from elasticsearch import Elasticsearch, helpers
import requests
import json
import yaml
from datetime import datetime, timezone
import time

# In a perfect world some things would be done differently here.  But limited API calls per month forces certain decisions to be made that otherwise would not be the best approach.

def get_teams():
   
    #TODO: modify this to use es_search() method
    client = Elasticsearch("https://localhost:9200/", verify_certs=False, ssl_show_warn=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")
    
    teams = client.search(index="teams", size=100)
    return teams._body['hits']['hits']

def get_location_info(home_team, teams):
    
    location = {}
    location["location"] = {}

    for team in (team for team in teams if team['_source'].get('team').get('id') == home_team):
        location["location"]["lat"] = team['_source'].get('team').get('location').get('lat')
        location["location"]["lon"] = team['_source'].get('team').get('location').get('lon')
        location["stadium_type"] = team['_source'].get('team').get('stadium')
        location["field_type"] = team['_source'].get('team').get('field')
    
    return location

def get_weather_alerts(lat, lon, headers):

    # TODO this only handles 1 alert.  what if there are multiples?

    walert = {}

    # TODO: pass in game.kickoff time to this function.  in the mean time...
    kickoff = 1729443600 #(oct 20, 1pm)

    alerts_url = f'https://api.weather.gov/alerts/active'

    # temporary hard code just to get some results
    lon=-81.37
    lat=30.24

    payload = {
        'status': 'actual',
        'message_type': 'alert',
        'point': f'{round(lat, 4)},{round(lon, 4)}'
    }

    resp = requests.get(alerts_url, payload, headers=headers).json()

    for alert in resp.get('features'):
        if kickoff <  int(datetime.fromisoformat(alert.get('properties').get('expires')).timestamp()):
            walert["alerts"] = {}
            walert["alerts"]["severity"] = alert.get('properties').get('severity')
            walert["alerts"]["event"] = alert.get('properties').get('event')
            walert["alerts"]["description"] = alert.get('properties').get('headline')
            walert["alerts"]["expires"] = alert.get('properties').get('expires')

    return walert

def get_weather(lat, lon, kickoff):

    weather = {}
    weather["weather"] = {}

    # for dev, if need to control kickoff time
    #kickoff = 1729567871

    headers = {
        'User-Agent': '(jbnation.com, jbyroads@gmail.com)'
    }
    
    points_url = f'https://api.weather.gov/points/{round(lat, 4)},{round(lon, 4)}'
    points = requests.get(points_url, headers=headers)
    
    grid_url = points.json().get('properties').get('forecast')
    grid = requests.get(grid_url, headers=headers)

    periods = grid.json().get('properties').get('periods')

    # api returns forecasts for more than just game window.  "if" here makes sure we get the correct weather window (or period)
    for period in (period for period in periods if int(datetime.fromisoformat(period.get('startTime')).timestamp()) <= kickoff and kickoff <= int(datetime.fromisoformat(period.get('endTime')).timestamp())):    
        weather["weather"]["temp"] = period.get("temperature")
        weather["weather"]["wind_speed"] = period.get("windSpeed")
        weather["weather"]["precipitation"] = period.get("probabilityOfPrecipitation").get("value")
        weather["weather"]["short_forecast"] = period.get("shortForecast")
        weather["weather"]["detailed_forecast"] = period.get("detailedForecast")

    walerts = get_weather_alerts(lat, lon, headers)
    weather["weather"].update(walerts)

    return weather

def es_search(index=None, query=None):

    client = Elasticsearch("https://localhost:9200/", verify_certs=False, ssl_show_warn=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")
    
    resp = client.search(index=index, body=query)

    return resp._body['hits']['hits']

def es_ingest(results):
    
    results.update({'@timestamp': int(datetime.now().timestamp())*1000})
    print(results)
    print("-------------")

    # TODO: put creds in k8s secrets
    #un = "j10s"
    #api_key = "T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ=="

    client = Elasticsearch("https://localhost:9200/", verify_certs=False, ssl_show_warn=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")

    resp = client.index(index="5050club", document=results)

    client.indices.refresh(index="5050club")

def es_bulk_ingest(allgames):

    # TODO: put creds in k8s secrets
    #un = "j10s"
    #api_key = "T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ=="

    index = "allgames"
    client = Elasticsearch("https://localhost:9200/", verify_certs=False, ssl_show_warn=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")

    #https://elasticsearch-py.readthedocs.io/en/v8.15.1/quickstart.html#indexing-documents
    #https://elasticsearch-py.readthedocs.io/en/latest/helpers.html
    #These helpers are the recommended way to perform bulk ingestion.

    # from elasticsearch import helpers

    def ingest_docs(allgames):
        for game in allgames:
            game.update({'@timestamp': int(datetime.now().timestamp())*1000})
            yield {
                "_op_type": "create",
                "_index": index,
                "_source": game
            }

    helpers.bulk(client, ingest_docs(allgames))

    print(f"Number of games ingested: {len(allgames)}")

    client.indices.refresh(index=index)

def parse_odds(data):
    
    start_time = time.time()
    print(f'start time: {start_time}')

    teams = get_teams()

    # TODO parser() needs to put together all games and pass that to es_ingest() vs putting together one game at a time and envoking es_ingest() over and over
    # thinking move entry inside the for loop.  then add an 'allgames = []' outside the for loop.  then add each entry to allgames.  can then pass allgames to check_scores() and es_ingest()
    allgames = []

    #for game in (game for game in data if game["id"] == "0dac14546d6008893a8b3b6c417472a6"):  # this list comprehension will go away.  here only for limiting results to 1 during dev
    for game in data:

        # TODO looks like odds keep updating even during the game.  we need to add something where if now() > commence_time, dont create new doc w/ those odds results
        # probably need to make a new field "completed" and make it boolean and drop status field w/ values of upcoming/live/completed.
        if int(datetime.now().timestamp()*1000) > int(game["commence_time"])*1000:
            print(f"skipping this game since its after kickoff. game.id: {game["id"]}")
            continue

        entry = {}

        entry.update({'game': {
            'id': game["id"], 
            'home_team': game["home_team"], 
            'away_team': game["away_team"], 
            'kickoff': int(game["commence_time"])*1000,
            'completed': False
            }})
        
        # if int(datetime.now().timestamp()) < game["commence_time"]:
        #     entry["game"]["status"] = 'upcoming'
        # elif int(datetime.now().timestamp()) >= game["commence_time"]:
        #     entry["game"]["status"] = 'live'

        location = get_location_info(game["home_team"], teams)
        entry["game"].update(location)

        #weather = get_weather(entry.get("game").get("location").get("lat"), entry.get("game").get("location").get("lon"), entry.get("game").get("kickoff"))
        #print(weather)
        #entry["game"].update(weather)

        for bookmaker in game.get("bookmakers"):
            entry["game"]["source"] = bookmaker["title"]
            entry["game"]["last_updated"] = int(bookmaker["last_update"])*1000
            for market_spreads in (market for market in bookmaker.get("markets") if market["key"]=="spreads"):
                entry["game"]["spread"] = {}

                # TODO: api doesnt indicate "fav" or "dog".  just has "point" and if its negative then you just know its fav.  should i do that?  would help for scenario where spread is 0 and there is no fav/dog.
                for outcome_fav in (outcome for outcome in market_spreads.get("outcomes") if outcome["point"]<0):
                    entry["game"]["spread"]["favorite_team"] = outcome_fav["name"]
                    entry["game"]["spread"]["favorite_points"] = outcome_fav["point"]
                    entry["game"]["spread"]["favorite_odds"] = outcome_fav["price"]
                for outcome_dog in (outcome for outcome in market_spreads.get("outcomes") if outcome["point"]>0):
                    entry["game"]["spread"]["underdog_team"] = outcome_dog["name"]
                    entry["game"]["spread"]["underdog_points"] = outcome_dog["point"]
                    entry["game"]["spread"]["underdog_odds"] = outcome_dog["price"]
                for outcome_pickem in (outcome for outcome in market_spreads.get("outcomes") if outcome["point"]==0):
                    if outcome_pickem["name"] == entry["game"]["home_team"]:
                        entry["game"]["spread"]["favorite_team"] = outcome_pickem["name"]
                        entry["game"]["spread"]["favorite_points"] = outcome_pickem["point"]
                        entry["game"]["spread"]["favorite_odds"] = outcome_pickem["price"]
                    if outcome_pickem["name"] == entry["game"]["away_team"]:
                        entry["game"]["spread"]["underdog_team"] = outcome_pickem["name"]
                        entry["game"]["spread"]["underdog_points"] = outcome_pickem["point"]
                        entry["game"]["spread"]["underdog_odds"] = outcome_pickem["price"]
            for market_totals in (market for market in bookmaker.get("markets") if market["key"]=="totals"):
                entry["game"]["total"] = {}

                for outcome_over in (outcome for outcome in market_totals.get("outcomes") if outcome["name"] == "Over"):
                    entry["game"]["total"]["over_under"] = outcome_over["point"]
                    entry["game"]["total"]["over_odds"] = outcome_over["price"]
                for outcome_under in (outcome for outcome in market_totals.get("outcomes") if outcome["name"] == "Under"):
                    entry["game"]["total"]["under_odds"] = outcome_under["price"]

        allgames.append(entry)

    # Your code here

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Elapsed time of parse_odds: {elapsed_time} seconds")

    return allgames

def get_odds():

    # TODO: logging
    
    # For a detailed API spec, see the Swagger API docs - https://app.swaggerhub.com/apis-docs/the-odds-api/odds-api/4#/sports/get_v4_sports
    # sample code: https://the-odds-api.com/liveapi/guides/v4/samples.html

    sport = 'americanfootball_nfl'

    payload = {
        'api_key': 'd79625dfeff1101a698ab3bca7324ed5',
        'regions': 'us',
        'markets': 'spreads,totals',
        #'bookmakers': 'williamhill_us',
        'bookmakers': 'draftkings',
        'dateFormat': 'unix',
        'oddsFormat': 'decimal'
    }

    odds_response = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds', payload)

    if odds_response.status_code != 200:
        print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')

    else:
        odds_json = odds_response.json()
        print('Number of events:', len(odds_json))

        # Check the usage quota
        print('Remaining requests', odds_response.headers['x-requests-remaining'])
        print('Used requests', odds_response.headers['x-requests-used'])

    return odds_json

def get_odds_file():

    # pull local file for development to save on api quota
    f = open('/Users/j10s/apps/5050club/spread-parser/data/odds_api_response.json')
    odds_json = json.load(f)

    print('Skipping odds api call.  Pulling from local file.')
    print('Number of events:', len(odds_json))
    
    # Closing file - only need if using local file for spreads
    f.close()

    return odds_json

if __name__ == '__main__':

    # check for ES connection first.  if cant connect, no sense in wasting api calls

    usefile = False

    if usefile:
        odds_resp = get_odds_file()
    else:
        odds_resp = get_odds()

    allgames = parse_odds(odds_resp)

    es_bulk_ingest(allgames)
from elasticsearch import Elasticsearch, helpers
import requests
import json
import yaml
from datetime import datetime, timezone

# TODO convert to using a class
    # get odds, process odds, ingest to es

def get_odds():
    results = http_poller()
    return results

def get_teams():
   
    client = Elasticsearch("https://localhost:9200/", verify_certs=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")
    
    teams = client.search(index="teams", size=100)
    return teams._body['hits']['hits']

def http_poller():

    # TODO: logging
    # TODO
    # For a detailed API spec, see the Swagger API docs - https://app.swaggerhub.com/apis-docs/the-odds-api/odds-api/4#/sports/get_v4_sports
    # sample code: https://the-odds-api.com/liveapi/guides/v4/samples.html
    # might need /v4/sports/{sport}/scores for seeing when game is complete and for final scores

    # this will be the eventual code once ready to constantly pull from api.  in mean time we'll just use a local file for development

    sport = 'americanfootball_nfl'

    payload = {
        'api_key': 'd79625dfeff1101a698ab3bca7324ed5',
        'regions': 'us',
        'markets': 'spreads,totals',
        'bookmakers': 'williamhill_us',
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


    # pull local file for development to save on api quota
    # f = open('./data/odds_api_response.json')
    # odds_json = json.load(f)

    print('Number of events:', len(odds_json))
    
    results = parser(odds_json)

    # Closing file - only need if using local file for spreads
    #f.close()

    return results

def parser(data):
    
    teams = get_teams()
    
    entry = {}
    
    #for game in (game for game in data if game["id"] == "0dac14546d6008893a8b3b6c417472a6"):  # this list comprehension will go away.  here only for limiting results to 1 during dev
    for game in data:
        entry.update({'game': {
            'id': game["id"], 
            'home_team': game["home_team"], 
            'away_team': game["away_team"], 
            'kickoff': game["commence_time"]
                               }})
        
        # TODO temporary solution.  need to think about this more.  need to keep api hits down.
        # nothing in "spreads" endpoint says if game is actually over or not.  so need to hit "scores" endpoint for "completed: true|false".
        # "scores" endpoint allows for providing game id so you can only get that one game.  but then youre making an api hit per game.  so maybe instead we just get all scores at some point in this job.
        # we also do need to get the actual scores for games too at some point and not just to find out if game is completed or not
        # but no point in hitting the scores api on say a Tu when no games are going on.  So need something to only hit scores api when appropriate, and when it does, just get all scores.
        # also, do we want score information in this index in these documents?  or do we want a separate index to keep scores?  initial thought is this index.
        if int(datetime.now().timestamp()) < game["commence_time"]:
            entry["game"]["status"] = 'upcoming'
        elif int(datetime.now().timestamp()) > game["commence_time"]+10800: #add 3 hours to kickoff team.  if current time is past that, then game is roughly over.
            entry["game"]["status"] = 'completed'
        else:
            entry["game"]["status"] = 'live'

        location = get_location_info(game["home_team"], teams)
        entry["game"].update(location)

        weather = get_weather(entry.get("game").get("location").get("lat"), entry.get("game").get("location").get("lon"), entry.get("game").get("kickoff"))
        entry["game"].update(weather)

        for bookmaker in game.get("bookmakers"):
            entry["game"]["source"] = bookmaker["title"]
            entry["game"]["last_updated"] = bookmaker["last_update"]
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
        
        es_ingest(entry)

def get_location_info(home_team, teams):
    
    location = {}
    location["location"] = {}

    for team in (team for team in teams if team['_source'].get('team').get('id') == home_team):
        location["location"]["lat"] = team['_source'].get('team').get('location').get('lat')
        location["location"]["lon"] = team['_source'].get('team').get('location').get('lon')
        location["stadium_type"] = team['_source'].get('team').get('stadium')
        location["field_type"] = team['_source'].get('team').get('field')
    
    return location

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
            walert["alerts"]["severity"] = alert.get('properties').get('severity')
            walert["alerts"]["event"] = alert.get('properties').get('event')
            walert["alerts"]["description"] = alert.get('properties').get('headline')
            walert["alerts"]["expires"] = alert.get('properties').get('expires')

    return walert


def es_ingest(results):
    print(results)
    print("-------------")

    # TODO: put creds in k8s secrets
    #un = "j10s"
    #api_key = "T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ=="

    client = Elasticsearch("https://localhost:9200/", verify_certs=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")

    resp = client.index(index="5050club", document=results)
    #print(resp["result"])

    client.indices.refresh(index="5050club")


    #https://elasticsearch-py.readthedocs.io/en/v8.15.1/quickstart.html#indexing-documents
    #These helpers are the recommended way to perform bulk ingestion.

    # from elasticsearch import helpers

    # def generate_docs():
    #     for i in range(10):
    #         yield {
    #             "_index": "my_index",
    #             "foo": f"foo {i}",
    #             "bar": "bar",
    #         }

    # helpers.bulk(client, generate_docs())

if __name__ == '__main__':
    get_odds()

    #es_ingest(results)
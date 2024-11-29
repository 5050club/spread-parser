from elasticsearch import Elasticsearch, helpers
import requests
import json
import yaml
from datetime import datetime, timezone

# In a perfect world some things would be done differently here.  But limited API calls per month forces certain decisions to be made that otherwise would not be the best approach.

def get_teams():
   
    #TODO: modify this to use es_search() method
    client = Elasticsearch("https://localhost:9200/", verify_certs=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")
    
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

def es_search(index, query=None):

    client = Elasticsearch("https://localhost:9200/", verify_certs=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")
    
    resp = client.search(index=index, body=query)

    return resp._body['hits']['hits']

def parse_results(allgames):

    print("check_scores: true")

    #this is where we do the call to get all scores. dont do it per game as thats too many api calls.  if we need to get even one, minds well get all.
    
    #allscores = get_scores()
    allscores = get_scores_file()
    
    #loop through each game in allgames where status == completed.
    for game in (game for game in allgames if game.get('game').get('status') == "completed"):
        # find matching game in allscores
        for score in (score for score in allscores if score.get('id') == game.get('game').get('id')):
            # if completed == false, update status in allgames to live.  this covers up fuzzy logic above to set game to completed if 3 hours past kickoff which is only done to save api hits.
            if score.get('completed') == False:
                game['game']['status'] == "live"
            # if completed == true, update game in allgames to include results
            if score.get('completed') == True:
                team1 = score.scores[0].get('name')
                team1_score = score.scores[0].get('score')

                team2 = score.scores[1].get('name')
                team2_score = score.scores[1].get('score')

                game['game']['results'] = {}
                game['game']['results']['total_points'] = team1_score + team2_score

                if team1_score > team2_score:
                    game['game']['results']['winner'] = team1
                    game['game']['results']['winning_score'] = team1_score
                    game['game']['results']['loser'] = team2
                    game['game']['results']['losing_score'] = team2_score
                elif team2_score > team1_score:
                    game['game']['results']['winner'] = team2
                    game['game']['results']['winning_score'] = team2_score
                    game['game']['results']['loser'] = team1
                    game['game']['results']['losing_score'] = team1_score
                else:
                    # this is to handle a tie.  but is this right?
                    game['game']['results']['winner'] is None
                    game['game']['results']['winning_score'] is None
                    game['game']['results']['loser'] is None
                    game['game']['results']['losing_score'] is None
                                
                # game.results.ats_winner  ->  if (game.spread.favorite_team == game.result.winner) and (game.spread.favorite - (game.result.winning_score - game.result.losing_score)) > 0, then favorite.  otherwise underdog
                
                # if fav is winner and game score diff > spread then fav. example: ravens fav. spread 3. they win 21-17. 4 > 3 so ats_winner = ravens 
                if (game['game']['spread']['favorite_team'] == game['game']['results']['winner']) and (game['game']['results']['winning_score'] - game['game']['results']['losing_score']) > game['game']['spread']['favorite']:
                    game['game']['results']['ats_winner'] = game['game']['spread']['favorite_team']
                # if fav is winner and game score diff < spread then dog.
                elif (game['game']['spread']['favorite_team'] == game['game']['results']['winner']) and (game['game']['results']['winning_score'] - game['game']['results']['losing_score']) < game['game']['spread']['favorite']:
                    game['game']['results']['ats_winner'] = game['game']['spread']['underdog_team']
                # if dog is winner then dog
                elif game['game']['spread']['underdog_team'] == game['game']['results']['winner']:
                    game['game']['results']['ats_winner'] = game['game']['spread']['underdog_team']
                # if game score diff == spread then push
                elif (game['game']['results']['winning_score'] - game['game']['results']['losing_score']) == game['game']['spread']['favorite']:
                    game['game']['results']['ats_winner'] = "push"


                # game.results.total  ->  if (game.result.total_points - game.total.over_under) = 0 push, < 0 under, > 0 over
                if game['game']['total']['over_under'] - game['game']['results']['total_points'] > 0:
                    game['game']['results']['total'] = "under"
                elif game['game']['total']['over_under'] - game['game']['results']['total_points'] < 0:
                    game['game']['results']['total'] = "over"
                elif game['game']['total']['over_under'] - game['game']['results']['total_points'] == 0:
                    game['game']['results']['total'] = "push"
    
    return allgames

def check_scores(allgames) -> bool:

    # TODO rethink this whole thing.  once a game is done, its removed from the odds response, so looping through allgames is pointless because the game wont be in there.  keep in mind here this is just to determine the boolean true/false of if we should get results.

    # option 1: dont worry about number of api hits.  basically every time we get spreads, we also get results.  that would make this "check_scores" OBE
    # option 2: check ES.  if "latest" has 'live' for any game, and its 3hrs past kickoff, check results

    # TODO loop through allgames and see if any are 'completed', which at this point in the process is only based off of "is it 3hrs past kickoff".  
    # if any are 'completed' check last record in ES for that game.  if all games are also completed there then skip getting results.
    # if any are not completed there then get all scores.
    # if not completed in scores, that game needs to be set to 'live'

    get_scores = False

    for game in allgames:
        latest_resp = []

        if game["game"]["status"] == 'completed':
            # TODO: create a "latest" index on allgames so we just need to query that and not do a top hit
            gameid = str(game.get('game').get('id'))
            
            # TODO: will need to update query to match mappings.  ie game.id.keyword will just be game.id in this query
            query = {
                "size": 1,
                "query": {
                    "bool": {
                    "filter": [
                        {
                        "term": {
                            "game.id.keyword": gameid
                        }
                        }
                    ]
                    }
                },
                "sort": [
                    {
                    "@timestamp": {
                        "order": "desc"
                    }
                    }
                ]
            }
            
            latest_resp = es_search(index='allgames', query=query)
            
            if latest_resp and latest_resp[0].get('_source').get('game').get('status') != "completed":
                get_scores = True
                # only need one instance of a game that is completed from the api resp and is not completed in ES.  Once that happens we can basically exit and return true.
                break

    return get_scores

def get_scores():

    sport = 'americanfootball_nfl'

    payload = {
        'api_key': 'd79625dfeff1101a698ab3bca7324ed5',
        'dateFormat': 'unix',
        'daysFrom': 2
    }

    scores_response = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/scores', payload)

    if scores_response.status_code != 200:
        print(f'Failed to get odds: status_code {scores_response.status_code}, response body {scores_response.text}')

    else:
        scores_json = scores_response.json()
        print('Number of events:', len(scores_json))

        # Check the usage quota
        print('Remaining requests', scores_response.headers['x-requests-remaining'])
        print('Used requests', scores_response.headers['x-requests-used'])

    print('Number of events:', len(scores_json))

    return scores_json

def get_scores_file():

    # pull local file for development to save on api quota
    f = open('/Users/j10s/apps/5050club/spread-parser/data/scores_api_response.json')
    scores_json = json.load(f)

    print('Skipping scores api call.  Pulling from local file.')
    print('Number of events:', len(scores_json))
    
    # Closing file - only need if using local file for spreads
    f.close()

    return scores_json

def es_ingest(results):
    
    results.update({'@timestamp': int(datetime.now().timestamp())*1000})
    print(results)
    print("-------------")

    # TODO: put creds in k8s secrets
    #un = "j10s"
    #api_key = "T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ=="

    client = Elasticsearch("https://localhost:9200/", verify_certs=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")

    resp = client.index(index="5050club", document=results)

    client.indices.refresh(index="5050club")

def es_bulk_ingest(allgames):

    # TODO: put creds in k8s secrets
    #un = "j10s"
    #api_key = "T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ=="

    index = "allgames"
    client = Elasticsearch("https://localhost:9200/", verify_certs=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")

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

    client.indices.refresh(index=index)

def parse_odds(data):
    
    teams = get_teams()
    
    # TODO parser() needs to put together all games and pass that to es_ingest() vs putting together one game at a time and envoking es_ingest() over and over
    # thinking move entry inside the for loop.  then add an 'allgames = []' outside the for loop.  then add each entry to allgames.  can then pass allgames to check_scores() and es_ingest()
    allgames = []

    #for game in (game for game in data if game["id"] == "0dac14546d6008893a8b3b6c417472a6"):  # this list comprehension will go away.  here only for limiting results to 1 during dev
    for game in data:
        entry = {}

        entry.update({'game': {
            'id': game["id"], 
            'home_team': game["home_team"], 
            'away_team': game["away_team"], 
            'kickoff': game["commence_time"]
                               }})
        
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

        allgames.append(entry)

    return allgames

def get_odds():

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


    # pull local file for development to save on api quota
    # f = open('./data/odds_api_response.json')
    # odds_json = json.load(f)

    print('Number of events:', len(odds_json))
    
    # Closing file - only need if using local file for spreads
    #f.close()

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

    # TODO before ingest, do something here to check scores, but only when necessary to limit api hits
    # solution: once we get allgames, see if any are 'completed' which is based just off of "is it 3hrs past kickoff".  if any are 'completed' check last record in ES for that game.  if all games are also completed there then skip getting results.  if any are not completed there then get results.

    if check_scores(allgames):
        finalgames = parse_results(allgames)
    else:
        finalgames = allgames
    

    es_bulk_ingest(allgames)
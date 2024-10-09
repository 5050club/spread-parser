import elasticsearch
import requests
import json
import yaml
from datetime import datetime, timezone

def get_odds():
    results = http_poller()
    return results

def http_poller():

    # TODO
    # For a detailed API spec, see the Swagger API docs - https://app.swaggerhub.com/apis-docs/the-odds-api/odds-api/4#/sports/get_v4_sports
    # sample code: https://the-odds-api.com/liveapi/guides/v4/samples.html
    # might need /v4/sports/{sport}/scores for seeing when game is complete and for final scores

    # this will be the eventual code once ready to constantly pull from api.  in mean time we'll just use a local file for development

    # sport = 'americanfootball_nfl'

    # payload = {
    #     'api_key': 'd79625dfeff1101a698ab3bca7324ed5',
    #     'regions': 'us',
    #     'markets': 'spreads,totals',
    #     'bookmakers': 'williamhill_us',
    #     'dateFormat': 'unix',
    #     'oddsFormat': 'decimal'
    # }

    # odds_response = requests.get(f'https://api.the-odds-api.com/v4/sports/{sport}/odds', payload)

    # if odds_response.status_code != 200:
    #     # TODO: implement logging
    #     print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')

    # else:
    #     odds_json = odds_response.json()
    #     print('Number of events:', len(odds_json))
    #     print(odds_json)

    #     # Check the usage quota
    #     #print('Remaining requests', odds_response.headers['x-requests-remaining'])
    #     #print('Used requests', odds_response.headers['x-requests-used'])


    # pull local file for development to save on api quota
    f = open('./data/odds_api_response.json')
    data = json.load(f)

    # TODO: logging
    print('Number of events:', len(data))
    
    # TODO: should potentially pass values for "markets" variable in payload into function for use in looping through to avoid hardcoding
    parser(data)

    # Closing file
    f.close()


def parser(data):
    
    # TODO: eventually what needs to be built out to send doc to elasticsearch
    games = []

    for game in (game for game in data if game["id"] == "0dac14546d6008893a8b3b6c417472a6"):  # this list comprehension will go away.  here only for limiting results to 1 during dev
        print(f'game.id: {game["id"]}, game.home_team: {game["home_team"]}, game.away_team: {game["away_team"]}, game.kickoff: {game["commence_time"]}')
        # TODO: get this working
        #print(get_location_info(game["home_team"]))
        get_location_info(game["home_team"])
        for bookmaker in game.get("bookmakers"):
            print(f'game.source: {bookmaker["title"]}, game.last_updated: {bookmaker["last_update"]}')
            for market_spreads in (market for market in bookmaker.get("markets") if market["key"]=="spreads"):
                print(market_spreads["key"])  #dont need this long term, this is only placeholder to show we're in the right place in the source doc
                # TODO: what if spread is 0 (no fav/dog) or if its off the board and is NA or something (i think per api schema this is an intergers so NA not possible)
                for outcome_fav in (outcome for outcome in market_spreads.get("outcomes") if outcome["point"]<0):
                    print(f'game.spread.favorite_team: {outcome_fav["name"]}, game.spread.favorite_points: {outcome_fav["point"]}, game.spread.favorite_odds: {outcome_fav["price"]}')
                for outcome_dog in (outcome for outcome in market_spreads.get("outcomes") if outcome["point"]>0):
                    print(f'game.spread.underdog_team: {outcome_dog["name"]}, game.spread.underdog_points: {outcome_dog["point"]}, game.spread.underdog_odds: {outcome_dog["price"]}')
            for market_totals in (market for market in bookmaker.get("markets") if market["key"]=="totals"):
                print(market_totals["key"])  #dont need this long term, this is only placeholder to show we're in the right place in the source doc
                for outcome_over in (outcome for outcome in market_totals.get("outcomes") if outcome["name"] == "Over"):
                    print(f'game.total.over_under: {outcome_over["point"]}, game.total.over_odds: {outcome_over["price"]}')
                for outcome_under in (outcome for outcome in market_totals.get("outcomes") if outcome["name"] == "Under"):
                    print(f'game.total.under_odds: {outcome_under["price"]}')

def get_location_info(home_team):
    
    # TODO: ingest teams.yaml to es and then here we need to pull from there.  would be nice to have a way to update team info w/o needing to update yaml file inside container

    teams_y = open('/Users/j10s/apps/5050club/backend/teams.yaml', "r")
    teams_d=yaml.load(teams_y, Loader=yaml.SafeLoader)

    print(f'game.location.lat: {teams_d.get(home_team).get("lat")}, game.location.lon: {teams_d.get(home_team).get("lon")}, game.stadium_type: {teams_d.get(home_team).get("stadium")}, game.field_type: {teams_d.get(home_team).get("field")}')
    
    get_weather(teams_d.get(home_team).get("lat"), teams_d.get(home_team).get("lon"))

def get_weather(lat, lon):

    # TODO: pass in game.kickoff time to this function.  in the mean time...
    kickoff = 1728605700
    # startTime = 2024-10-10T06:00:00-07:00 --> 1728565200
    # endTime =   2024-10-10T18:00:00-07:00 --> 1728608400
    # "number": 4

    headers = {
                'User-Agent': '(jbnation.com, jbyroads@gmail.com)'
    }
    
    points_url = f'https://api.weather.gov/points/{round(lat, 4)},{round(lon, 4)}'
    points = requests.get(points_url, headers=headers)
    
    grid_url = points.json().get('properties').get('forecast')
    grid = requests.get(grid_url, headers=headers)

    periods = grid.json().get('properties').get('periods')

    for period in (period for period in periods if int(datetime.fromisoformat(period.get('startTime')).timestamp()) <= kickoff and kickoff <= int(datetime.fromisoformat(period.get('endTime')).timestamp())):
        print(f'game.weather.temp: {period.get("temperature")}, game.weather.wind_speed: {period.get("windSpeed")}, game.weather.precipitation: {period.get("probabilityOfPrecipitation").get("value")}, game.weather.short_forecast: {period.get("shortForecast")}, game.weather.detailed_forecast: {period.get("detailedForecast")}')

    get_alerts(lat, lon)


def get_alerts(lat, lon):
    # TODO get alerts

    print("alerts")


def es_ingest():
    print("ingest")

if __name__ == '__main__':
    results = get_odds()
    # TODO
    #docs = get_weather(results)
    #es_ingest(docs)
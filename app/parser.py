import elasticsearch
import requests
import json

def get_spreads():
    results = http_poller()

def http_poller():

    # sample code: https://the-odds-api.com/liveapi/guides/v4/samples.html

    # API key: 4e29d3bc02dc3dc900404ced1b879df0
    # base_url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds'
    # payload = {
    #             'api_key': '4e29d3bc02dc3dc900404ced1b879df0',
    #             'regions': 'us',
    #             'markets': 'spreads,totals',
    #             'dateFormat': 'unix',
    #             'oddsFormat': 'decimal'
    #         }

    # r = requests.get(base_url, params=payload)

    # odds_json = r.json()
    # print('Number of events:', len(odds_json))
    # print(odds_json)



    f = open('./data/spreads_api_response.json')
    data = json.load(f)

    print('Number of events:', len(data))
    
    for game in data:
        print(game["id"])
    

    # Closing file
    f.close()


def parser():
    print("parser")

def get_weather():

    base_url = 'http://api.openweathermap.org/data/2.5/weather?'
    payload = {
                'lat': '40.7', # NY City, NY, USA
                'lon': '74.0',
                'units': 'imperial',
                'APPID': 'your-api-key'
            }
    r = requests.get(base_url, params=payload)  # gets json output

def ingest():
    print("ingest")

if __name__ == '__main__':
    get_spreads()
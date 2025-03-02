###
#
# This is just a script to update a local file w/ spreads thats then used for development and testing.
#
###

import requests
import json

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

    # write results to file
    f = open('/Users/j10s/apps/5050club/spread-parser/data/scores_api_response.json', 'w')
    f.write(json.dumps(scores_json))

    # Check the usage quota
    print('Remaining requests', scores_response.headers['x-requests-remaining'])
    print('Used requests', scores_response.headers['x-requests-used'])

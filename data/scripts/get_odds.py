###
#
# This is just a script to update a local file w/ spreads thats then used for development and testing.
#
###

import requests

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
    print(odds_json)

    # Check the usage quota
    print('Remaining requests', odds_response.headers['x-requests-remaining'])
    print('Used requests', odds_response.headers['x-requests-used'])

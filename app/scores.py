from elasticsearch import Elasticsearch, helpers
import requests
import json
import yaml
from datetime import datetime, timezone

# In a perfect world some things would be done differently here.  But limited API calls per month forces certain decisions to be made that otherwise would not be the best approach.

def es_bulk_ingest(index=None, docs=None):

    # TODO: put creds in k8s secrets
    #un = "j10s"
    #api_key = "T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ=="

    client = Elasticsearch("https://localhost:9200/", verify_certs=False, ssl_show_warn=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")

    #https://elasticsearch-py.readthedocs.io/en/v8.15.1/quickstart.html#indexing-documents
    #https://elasticsearch-py.readthedocs.io/en/latest/helpers.html
    #These helpers are the recommended way to perform bulk ingestion.

    # from elasticsearch import helpers

    def ingest_docs(docs):
        for doc in docs:
            doc.update({'@timestamp': int(datetime.now().timestamp())*1000})
            yield {
                "_op_type": "create",
                "_index": index,
                "_source": doc
            }

    helpers.bulk(client, ingest_docs(docs))

    print(f"Number of games ingested: {len(docs)}")

    client.indices.refresh(index=index)

def es_search(index=None, query=None):

    client = Elasticsearch("https://localhost:9200/", verify_certs=False, ssl_show_warn=False, api_key="T2dEZnJKSUJtT2RjdnlGQllreF86MXJfVE5ucVlTN09kT1pzb3ZGd1YyUQ==")
    
    resp = client.search(index=index, body=query)

    return resp._body['hits']['hits']

def parse_scores(allscores):

    print("check_scores: true")

    # 11/29: we've determine we need to get scores and have passed response in api resp.
    # next step is to ???...loop through allscores, find matching game id in ES in "latest".  check its status.  if completed then it already has result if not, grab that doc, merge w/ scores, ingest new document and set status to completed
    allgames = []
    
    for score in (score for score in allscores if score.get('completed') == True and score['scores']):

        id = score.get('id')

        query = {
            "size": 1,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "term": {
                                "game.id": id
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

        resp = es_search(index="allgames_latest", query=query)

        if resp and resp[0].get('_source').get('game').get('completed') != True:
            game = resp[0].get('_source')
            game['game']['completed'] = True
            game['game']['last_updated'] = int(score.get('last_update'))*1000

            team1 = score['scores'][0].get('name')
            team1_score = int(score['scores'][0].get('score'))

            team2 = score['scores'][1].get('name')
            team2_score = int(score['scores'][1].get('score'))

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
            if (game['game']['spread']['favorite_team'] == game['game']['results']['winner']) and (game['game']['results']['winning_score'] - game['game']['results']['losing_score']) > int(abs(game['game']['spread']['favorite_points'])):
                game['game']['results']['ats_winner'] = game['game']['spread']['favorite_team']
            # if fav is winner and game score diff < spread then dog.
            elif (game['game']['spread']['favorite_team'] == game['game']['results']['winner']) and (game['game']['results']['winning_score'] - game['game']['results']['losing_score']) < int(abs(game['game']['spread']['favorite_points'])):
                game['game']['results']['ats_winner'] = game['game']['spread']['underdog_team']
            # if dog is winner then dog
            elif game['game']['spread']['underdog_team'] == game['game']['results']['winner']:
                game['game']['results']['ats_winner'] = game['game']['spread']['underdog_team']
            # if game score diff == spread then push
            elif (game['game']['results']['winning_score'] - game['game']['results']['losing_score']) == int(abs(game['game']['spread']['favorite_points'])):
                game['game']['results']['ats_winner'] = "push"


            # game.results.total  ->  if (game.result.total_points - game.total.over_under) = 0 push, < 0 under, > 0 over
            if int(game['game']['total']['over_under']) - game['game']['results']['total_points'] > 0:
                game['game']['results']['total'] = "under"
            elif int(game['game']['total']['over_under']) - game['game']['results']['total_points'] < 0:
                game['game']['results']['total'] = "over"
            elif int(game['game']['total']['over_under']) - game['game']['results']['total_points'] == 0:
                game['game']['results']['total'] = "push"

            allgames.append(game)
    
    return allgames

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

def check_scores() -> bool:

    # check ES.  if "latest" has 'live' for any game, and its 3hrs past kickoff, check results
    
    get_scores = False

    # TODO: might need to updat query once we have a "latest" index.  might also need to double check matching mappings.

    query = {
        "query": {
            "bool": {
                "filter": [
                    {
                        "term": {
                            "game.completed": False
                        }
                    },
                    {
                        "range": {
                            "game.kickoff": {
                                "lte": "now-3h"
                            }
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

    latest_resp = es_search(index='allgames_latest', query=query)
   
    if latest_resp:
        get_scores = True

    return get_scores

if __name__ == '__main__':

    # check for ES connection first.  if cant connect, no sense in wasting api calls

    usefile = False

    if check_scores():
        if usefile:
            allscores = get_scores_file()
        else:
            allscores = get_scores()

        games = parse_scores(allscores)
    
        if games:
            es_bulk_ingest(index="allgames", docs=games)
        else:
            print("No games to update.")
    else:
        print("No need to check scores API.")
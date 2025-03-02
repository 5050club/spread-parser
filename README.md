# spread-parser

# next steps

- rework parser.py and the flow from get_odds to http_poller to parser etc.  probably also part of the piece around introduce classes
- convert to using a classes: get odds, process odds, scores, ingest to es
- what parameters do i want to pass in here? examples - only get odds, only get scores, only get info for one game, only get weather?

# fields
## changes to make to es schema
### add
game.stadium_type, keyword  ->  get from teams.yaml.  examples - indoor, outdoor, retractable
game.field_type, keyword  ->  get from teams.yaml.  examples - grass, turf
game.weather.precipitation, float or short?  (this will represent a percent).  examples are "50", "30", "30"
game.weather.alerts.severity, keyword
game.weather.alerts.event, keyword;text
game.weather.alerts.description, text
game.weather.alerts.expires, date
game.location.lat, geo_point
game.location.lon, geo_point

## update
game.team.home  ->  game.home_team
game.team.away  ->  game.away_team
all game.team.spread.* becomes game.spread.*
game.spread.source  ->  game.source
game.total.source  ->  game.source
game.spread.odds.favorite, float -> game.spread.favorite_odds
game.spread.odds.underdog, float -> game.spread.underdog_odds
game.total.odds.over, float  ->  game.total.over_odds
game.total.odds.under, float  ->  game.total.under_odds
game.weather.main, keyword  -> game.weather.short_forecast, text;keyword
game.weather.description, text  ->  game.weather.detailed_forecast, text
game.weather.wind_speed, float  ->  keyword;text
game.weather.alerts.event, keyword;text
game.location, geo_point  ->  game.location, object

### remove
game.team, object
game.spread.odds, object
game.spread.home, float  ->  bookmakers[].markets[key=spreads].outcomes[].point (if .name is home)
game.spread.away, float  ->  bookmakers[].markets[key=spreads].outcomes[].point (if .name is away)
game.total.odds, object
game.weather.feels_like, float  -> 

## field mappings
game, object
*game.id, keyword  ->  id
*game.home_team, text;keyword  ->  home_team
*game.away_team, text;keyword  ->  away_team
*game.kickoff, date  ->  commence_time
*game.last_updated, date  ->  bookmakers[].last_update
*game.source, keyword  ->  bookmakers[].title
game.status, keyword  ->  ? this like for upcoming, live, completed or something?  is this in the data somehwere or I need to derive this value?
--
*game.location, object  ->  /Users/j10s/apps/5050club/backend/teams.yaml has geo points and other info for given team.  will i ingest that and then pull that info in here for enrichment?
*game.location.lat, geo_point
*game.location.lon, geo_point
*game.stadium_type, keyword  ->  get from teams.yaml.  examples - indoor, outdoor, retractable
*game.field_type, keyword  ->  get from teams.yaml.  examples - grass, turf
--
*game.weather, object  ->  
*game.weather.temp: 62
*game.weather.wind_speed: 3 to 10 mph, 
*game.weather.precipitation: None, 
*game.weather.short_forecast: Mostly Sunny, 
*game.weather.detailed_forecast: Mostly sunny, with a high near 62. North wind 3 to 10 mph.
*game.weather.alerts, object
*game.weather.alerts.severity, keyword  ->  features[].properties.severity
*game.weather.alerts.event, keyword;text  -> features[].properties.event
*game.weather.alerts.description, text  ->  features[].properties.headline
*game.weather.alerts.expires, date  ->  features[].properties.expires
--  
*game.spread, object
*game.spread.favorite_team, text;keyword  ->  bookmakers[].markets[key=spreads].outcomes[].name (if .point is negative)
*game.spread.underdog_team, text;keyword  ->  bookmakers[].markets[key=spreads].outcomes[].name (if .point is positive)
*game.spread.favorite_points, float  ->  bookmakers[].markets[key=spreads].outcomes[].point (if point neg)
*game.spread.underdog_points, float  ->  bookmakers[].markets[key=spreads].outcomes[].point (if point pos)
*game.spread.favorite_odds, float -> bookmakers[].markets[key=spreads].outcomes[].price (if points neg)
*game.spread.underdog_odds, float -> bookmakers[].markets[key=spreads].outcomes[].price (if points pos)
--
*game.total, object
*game.total.over_under, float  ->  bookmakers[].markets[key=totals].outcomes[].price (need to pick one from over and under but should be same number always)
*game.total.over_odds, float  ->  bookmakers[].markets[key=totals].outcomes[name=Over].price
*game.total.under_odds, float  ->  bookmakers[].markets[key=totals].outcomes[name=Under].price

# do i need to use /v4/sports/{sport}/scores to get this info.  do i take the event id and do a search on this endpoint to see if game is completed
--
game.results, object
game.results.winner, text;keyword  ->  scores[].name (if score > other score)  what if there is a tie??
game.results.loser, text;keyword  ->  scores[].name (if score < other score)
game.results.winning_score, short  ->  scores[].score (if score > other score)
game.results.losing_score, short  ->  scores[].score (if score <> other score)
game.results.ats_winner, text;keyword  ->  if (game.spread.favorite_team == game.result.winner) and (game.spread.favorite - (game.result.winning_score - game.result.losing_score)) > 0, then favorite.  otherwise underdog
game.results.total, keyword  ->  if (game.result.total_points - game.total.over_under) = 0 push, < 0 under, > 0 over
game.results.total_points  ->  sum(game.result.winning_score, game.result.losing_score)


# questions
- at what point does a game no longer show up in the odds api.  
  - how do i make sure i know to get score info for that game
  - can i somehow use that to apply some logic where a game that doesnt have a score but isnt in the odds resp, then go query the scores endpoint.  but also need to limit api calls
  - how do i limit the number of calls to api.  will i need to check latest in es for game being complete and then i dont have to query api for it anymore.

# feature requests

- ability to perform adhoc runs that dont just grab everything, but grab something specific
  - check the api's to see what options can be provided w/ query.  that will drive what adhoc options are available here
- some way to run parser (argo workflow/events for example)
  - w/ a worker queue?
- free version of api only allows 500 requests/mo or something.  that would be 500/31 = 16.13/day = 24/16.13 =  1.48 (round up) = 1 request every 2 hours.  (once every 2hrs = 12x/day = 372x/month).  maybe run more frequently on Sunday mornings.
  - will need to refactor this math as additional calls will need to be made on Sundays to get scores as thats a separate endpoint
# Stream B notes (for the README limitations and methods sections)

Regenerate: `.venv/bin/python src/gtfs.py` then `cd src && ../.venv/bin/python context.py`.

## Read the CSV with string ids
`pd.read_csv("outputs/stops_context.csv", dtype={"stop_id": str, "tract_geoid": str})`.
The default read turns `stop_id` into int and breaks joins on string ids.

## Stops
- RTS GTFS, Spring 2026 feed (Regional Transit System, Gainesville), 971 stops.
- The feed's end date is 2026-05-03, so it predates the Sept 2026 event. It is the newest
  feed RTS publishes as far as we found.

## daily_trips and routes
- Representative day: Wednesday 2026-02-11. Active services that day: Weekday and Mon-Thur
  (Reduced_Service is switched off by calendar_dates.txt).
- daily_trips = count of stop_times rows (bus visits) at the stop on that day. It is a
  ridership proxy, not ridership.
- 14 stops have 0 trips that day (weekend-only or otherwise unserved). They keep their row
  with daily_trips = 0 and empty routes (reads as null in pandas).
- routes = route short names serving the stop that same day, comma separated.

## shelter_status
- OSM via Overpass, 933 bus stop and platform nodes. Each GTFS stop takes the nearest OSM
  node within 25 m. shelter=yes is sheltered, shelter=no is none, everything else is unknown.
- Fallback: for stops still unknown, the OSM `ref` tag equals the GTFS stop_id. Where the
  spatial match and the ref both gave an answer they agreed 485 of 485 times. A ref match is
  accepted only if that node is within 100 m of the stop. This recovered 26 stops.
- Result: none 495, unknown 370, sheltered 106. 718 of 971 stops matched an OSM node by distance.
- Unknown covers both "no OSM node within 25 m" and "OSM node with no shelter tag". Nothing
  was guessed. OSM shelter=no is only as good as the mappers, so treat none as "OSM says no".

## Census
- ACS 2024 5-year (2020-2024), tract level. The official Census API now requires a key, so
  the numbers come from Census Reporter, a keyless mirror of the same ACS tables.
- Tract shapes: Census TIGER/Line 2024. All 971 stops fall in an Alachua County tract.
- pct_no_vehicle = B08201_002 / B08201_001 * 100 (households with no vehicle).
- pct_65_plus = sum of B01001 male 020-025 and female 044-049, over B01001_001, times 100.
- No columns are empty. Tract values are a coarse proxy for who stands at a given stop.

## Route ranking (outputs/route_ranking.csv)
Regenerate after score.py: `.venv/bin/python src/route_ranking.py`.
- One sentence: a route ranks higher when its stops are, on average, hotter, busier, less
  likely to have a shelter, and in tracts with more car-free households.
- route_rank orders the 26 routes by avg_score, the mean stop score over the route's ranked
  stops (915 ranked stops; unranked stops are left out). Ties go to more top-50 stops.
- stops_in_top50 counts the route's stops in the citywide top 50 stops.
- pct_unsheltered is OSM "none" only. pct_unknown is shown beside it, so read unsheltered as
  a floor, not a total.
- Limits to state: a stop's bus visits count every route at that stop, so routes through
  busy hubs (Reitz Union, The Hub) get a boost. The top routes are mostly UF corridor routes,
  the same campus-tract effect as in the stop ranking.

## Community corrections (outputs/shelter_overrides.csv)
- Empty by design until someone verifies a stop. Columns: stop_id, status, source, date.
  Overrides beat OSM in context.py; each row must have a source. See ADMIN_PHOTOS.md.
- Popups link to a prefilled GitHub issue per stop ("Shelter info wrong? Tell us") and, for
  stops not known to be sheltered, to the request channels for a shelter (myGNV, RTS phone).
- Limit to state: the report link needs a GitHub account and someone has to triage issues.
  It is a feedback path, not a service, and it makes no promise about what the city does.

## Impact numbers (outputs/impact_summary.md, outputs/stop_afternoon_trips.csv)
Regenerate after score.py: `cd src && ../.venv/bin/python impact.py`. Every sentence in
`impact_summary.md` is computed from the data, so paste from it rather than retyping.
- afternoon_trips = bus visits at the stop between 11:00 and 16:59 on the same representative
  Wednesday as daily_trips. It counts scheduled visits, not measured afternoon temperatures.
- Headlines: 44 percent of weekday bus visits fall in 11 am to 5 pm; 49 percent of visits are
  at stops OSM lists as unsheltered and another 28 percent at unknown, only 23 percent at
  sheltered; the top 20 stops get 8 percent of visits from 2 percent of stops.

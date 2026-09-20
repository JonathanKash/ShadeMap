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
  stops (850 ranked stops; unranked stops are left out). Ties go to more top-50 stops.
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

## Ranking stability under census uncertainty (outputs/ranking_stability.md and .csv)
Regenerate after score.py: `cd src && ../.venv/bin/python stability.py` (fixed seed, reproducible).
- ACS numbers are estimates with margins of error. Two campus tracts are tiny: 164 and 237
  households, with margins of about 17 and 29 points on the no-vehicle share. 19 of the top 20
  stops sit in those two tracts.
- Redrawing each tract's share within its margin 1000 times: on average 16.3 of the 20
  published top stops stay in the top 20; ranks 1 to 10 stay in at least 90 percent of draws;
  ranks 15 to 20 are near-ties (41 to 76 percent).
- Only census uncertainty is varied (heat, bus visits and shelter are held fixed), so say
  "the top 10 are robust to census error, the rest of the top 20 is close", not that the
  whole ranking has an error bar. The published ranking is unchanged and nothing was tuned.
- Several top-20 stops are the same place: Southwest Recreation Center appears 3 times
  (different stop ids, ranks 3, 5, 8). Say so in the README rather than hiding it.

## Near and far from campus (outputs/priority_near_far_campus.csv and .md, outputs/stop_campus.csv, docs/campus.json)
Regenerate after score.py: `cd src && ../.venv/bin/python campus.py`. Boundary is the OpenStreetMap
University of Florida relations (main and East Campus), cached in data/, area 7.6 km2.
- Near campus = within 1 mile of the MAIN campus edge (campus included), far = beyond. Distance is from the
  boundary, not a center point: UF is about 3 km across, a mile around its center would not cover it.
  The separate 20-acre OSM "East Campus" outline is excluded: it is 2.7 miles from the main campus and
  its own one-mile ring pulled 54 NE Gainesville stops (NE 15th St, Waldo Rd) into "near campus".
- 369 stops near, 602 far. Far stops carry 36 percent of weekday bus visits and 41 percent of the
  visits at stops with no known shelter. The map draws the campus outline and the mile line
  (docs/campus_zone.geojson) while a zone chip is active. The two top 10 lists carry 6 percent of visits together.
- Each zone is ranked with the same score, nothing re-weighted. The far top 10 is citywide ranks 51
to 76, 1.5 to 3 miles from campus: Oaks Mall and apartment stops on routes 75, 52, 15 (NW Gainesville).
  The near top 10 is identical to the old citywide top 10.
- The app no longer has a "top 20" chip or top-20 emphasis; the biggest dots are the top 10 of each zone.
  A's separate "needs shade most" list (black dots) is unchanged and is still 20 stops.
- Limits: the boundary is drawn by OpenStreetMap contributors, near campus includes student apartments
  and much of downtown, shelter status is partial.

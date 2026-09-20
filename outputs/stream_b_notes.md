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

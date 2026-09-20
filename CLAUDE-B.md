# CLAUDE-B.md

Stream B: stops, service frequency, shelters, and who is affected. Read `CLAUDE.md` and
`CONTRACTS.md` first.

You own `src/gtfs.py` and `src/context.py`. Two deliverables:
`outputs/stops.geojson` by **10:20** and `outputs/stops_context.csv` by **12:00**.

## The 10:20 deliverable is urgent and trivial

A is blocked on stop coordinates. Download the RTS GTFS feed, parse `stops.txt`, write a
GeoJSON in EPSG:4326 with `stop_id` as a string. That is it. Do not clean it, do not
enrich it, do not wait until it is nice. Push it and tell the group.

If the RTS feed is hard to find, check Transitland, Mobility Database, or the GTFS link on
the city or RTS website. If you cannot find it in 15 minutes, say so loudly, because the
whole project shape changes.

## Then, in priority order

### 1. Daily trips (highest value, do it first)

Join `stop_times.txt` to `trips.txt` to `calendar.txt`. Pick one representative weekday
service id, count stop_times rows per `stop_id`. This is your ridership proxy.

Two traps: `calendar_dates.txt` exceptions, and multiple service ids active on the same
weekday. Do not model this perfectly. Pick a typical Wednesday, count, move on. Write down
what you picked so C can put it in the README limitations section.

Also build `routes`: comma separated route short names serving each stop. Judges like
seeing a familiar route number.

### 2. Shelter status

Overpass API, Gainesville bbox:

```
[out:json];
(
  node["highway"="bus_stop"](29.58,-82.48,29.73,-82.25);
  node["public_transport"="platform"](29.58,-82.48,29.73,-82.25);
);
out body;
```

Match OSM nodes to GTFS stops by nearest neighbor within about 25m. Read the `shelter`
tag: `yes` maps to `sheltered`, `no` maps to `none`, missing tag or no match within 25m
maps to `unknown`.

**Be honest about this.** OSM shelter coverage in Gainesville is likely sparse. If most
stops come back `unknown`, that is the real answer and C will write it into the
limitations. Do not guess a value to make the column look full. A judge who notices
fabricated data is the worst outcome of the day.

### 3. Census equity layer

This is the thing that turns a heat map into an impact argument, and it is what wins the
"problem and impact" criterion. Do not skip it.

- Tract geometries: Census TIGER/Line for Alachua County (FIPS 12001), or `pygris`
- ACS 5-year via the Census API: **B08201** for households with no vehicle, **B01001**
  for age 65+
- The API works without a key for light use, but grab a free key if you hit limits
- Spatial join stops to tracts, carry `tract_geoid`, `pct_no_vehicle`, `pct_65_plus`

Compute percentages yourself from the raw counts. Do not hardcode a denominator.

### 4. Write `outputs/stops_context.csv` exactly per the contract

Column names and the `shelter_status` vocabulary (`sheltered` / `none` / `unknown`) must
match exactly. C's scoring code branches on those three strings.

## Rules

- `stop_id` is a string everywhere, including after any merge. Pandas will silently coerce
  it to int and break C's join.
- Cache the GTFS zip and the Overpass response to `data/`. Overpass rate limits.
- Row count in `stops_context.csv` must equal row count in `stops.geojson`. Verify this
  before you push, with an assert.
- Do not touch `src/lst.py` or `src/score.py`.

## If you are behind at 11:30

Cut order: census layer last, shelters second to last, daily trips never. Ship the CSV
with `shelter_status` all `unknown` and null census columns rather than shipping nothing.
C's code should handle nulls, but tell C which columns are empty so the map legend does
not promise data that is not there.

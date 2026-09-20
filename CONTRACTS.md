# CONTRACTS.md

Read this with CLAUDE.md before doing anything. Every Claude in this repo reads this file.

Three people are working in parallel. This file is the only thing keeping you from
blocking each other. Do not change a schema here without telling the other two out loud.

## Streams

| Stream | Human | Owns | Never touches |
|---|---|---|---|
| A | | `src/lst.py`, satellite data, zonal stats | `src/gtfs.py`, `src/context.py`, `src/score.py`, `docs/` |
| B | | `src/gtfs.py`, `src/context.py` | `src/lst.py`, `src/score.py`, `docs/` |
| C | | `src/score.py`, `docs/`, `README.md`, `analysis.ipynb` | `src/lst.py`, `src/gtfs.py`, `src/context.py` |

Nobody edits `CLAUDE.md` or `CONTRACTS.md` after 10:15 except to fix a factual error, and
if you do, say it in the group chat.

## Git

Push to `main`, pull before every push. File ownership above means you should never hit a
real conflict. Branches would cost more time than they save today.

`data/` is gitignored (raw downloads, big). `outputs/` is committed (small CSVs, this is
how you hand work to each other).

## The three handoff files

These are the interface. Column names are exact. Everyone writes `stop_id` as a **string**,
not an int, because GTFS ids are not always numeric.

### 1. `outputs/stops.geojson`
Owner: **B**. Due **10:20**. This unblocks A.

Just a parse of GTFS `stops.txt`. Ship it fast and ugly, refine later.

```
stop_id      str    join key, everything keys off this
stop_name    str
stop_lat     float
stop_lon     float
geometry     Point, EPSG:4326
```

### 2. `outputs/stop_lst.csv`
Owner: **A**. Due **12:00**. Consumed by C.

One row per stop in `stops.geojson`.

```
stop_id       str
mean_lst_c    float   mean land surface temp, Celsius, in a 100m buffer
max_lst_c     float
pixel_count   int     how many raster pixels fell in the buffer, 0 means no data
scene_dates   str     semicolon separated, for the README methods section
```

Stops with no raster coverage: keep the row, `pixel_count = 0`, temps as null. Do not
drop rows. C handles the nulls.

### 3. `outputs/stops_context.csv`
Owner: **B**. Due **12:00**. Consumed by C.

One row per stop in `stops.geojson`.

```
stop_id          str
stop_name        str
stop_lat         float
stop_lon         float
daily_trips      int     count of stop_times rows for a typical weekday service day
routes           str     comma separated route short names
shelter_status   str     exactly one of: sheltered | none | unknown
tract_geoid      str     11 digit census tract GEOID
pct_no_vehicle   float   0 to 100, ACS B08201, share of households with no vehicle
pct_65_plus      float   0 to 100, ACS B01001
```

### 4. `outputs/scored_stops.csv` and `outputs/top_20_stops.csv`
Owner: **C**. Produced by joining 2 and 3 on `stop_id`.

Adds `lst_percentile`, `shelter_multiplier`, `transit_dependence`, `score`, `rank`.

## Stub data (this is what makes parallel work possible)

At 10:15, **C** writes `outputs/_stub_stop_lst.csv` and `outputs/_stub_stops_context.csv`
with the exact schemas above and 40 rows of plausible fake values around Gainesville
coordinates. C then builds the entire scoring and map pipeline against the stubs and never
waits on anyone.

At 12:00 C swaps the filenames. If the schemas match, the swap takes 30 seconds. That is
the whole point of this document.

A and B: if your real output does not load cleanly in place of the stub, that is your bug
to fix, not C's.

## Checkpoints

Everyone stops and syncs at these times. Keep them to five minutes.

- **10:20** B has shipped `stops.geojson`. A confirms it loads.
- **12:00** A and B ship real handoff files. C swaps out the stubs.
- **13:30** Full pipeline runs end to end on real data. Whatever is broken at 13:30 gets
  cut, not fixed.
- **15:00** Code freeze. Everyone moves to submission and demo prep.
- **16:30** Devpost submission closes. Be done well before this.

## When you are blocked

Do not wait. Fall back to the stub, flag it in the group chat, and keep moving. A person
sitting idle for 20 minutes is 10 percent of this hackathon.

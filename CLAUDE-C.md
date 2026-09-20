# CLAUDE-C.md

Stream C: scoring, map, story, submission. Read `CLAUDE.md` and `CONTRACTS.md` first.

You own `src/score.py`, `docs/`, `README.md`, `analysis.ipynb`, and the Devpost
submission. You never wait for A or B because you build against stubs.

You are also the person who decides at 13:30 what gets cut. That is a real job. Take it.

## 10:00 to 10:15: write the stubs

Before anything else, write `outputs/_stub_stop_lst.csv` and
`outputs/_stub_stops_context.csv` with the exact schemas in `CONTRACTS.md`, 40 rows,
plausible values, real-ish Gainesville coordinates (roughly 29.60 to 29.70 lat, -82.40 to
-82.30 lon). Make the values varied enough that your map and legend actually get
exercised: temperatures spanning 28 to 45 C, a mix of `sheltered` / `none` / `unknown`,
daily_trips from 4 to 120.

Tell A and B the stubs exist so they can validate their output against them.

From here on, everything you build runs on the stubs until 12:00. You should have a
working map by noon with fake data in it.

## Scoring (`src/score.py`)

```
score = lst_percentile * log1p(daily_trips) * shelter_multiplier * transit_dependence
```

- `lst_percentile`: percentile rank of `mean_lst_c` across all stops, 0 to 1
- `shelter_multiplier`: `none` = 1.5, `unknown` = 1.25, `sheltered` = 1.0
- `transit_dependence`: `pct_no_vehicle` min-max normalized into 0.5 to 1.5
- Null handling: stops with `pixel_count = 0` get excluded from the ranking entirely, but
  keep them in `scored_stops.csv` with a null score and a `excluded_reason` column. Null
  census means `transit_dependence = 1.0`.

Do not tune weights to produce a nicer looking top 20. If someone asks whether you tuned
it, the answer has to be no.

Write `outputs/scored_stops.csv` (everything) and `outputs/top_20_stops.csv` (rank 1
through 20, human readable column order).

## Map (`docs/index.html`)

Folium, static export, GitHub Pages from the `docs/` folder.

- Center Gainesville, zoom 12, CartoDB Positron basemap so the color ramp reads clearly
- All stops as circle markers, radius scaled by score, sequential color ramp
- Legend in plain words, not just a number gradient. "Higher priority for shade" beats
  "0.82"
- Top 20 get a distinct marker style and a popup with stop name, routes, daily trips,
  mean LST in both C and F, shelter status, and rank
- A title bar rendered into the map itself with one sentence of context, because the map
  will get shared as a bare link without the README
- Test it on a phone. A judge may open it on their own device.

## README

Lead with the problem in two sentences, then a screenshot of the map, then the method,
then how to run it. Then a limitations section that says plainly: partial OSM shelter
coverage, trip counts used as a ridership proxy, short satellite time window, tract-level
census as a coarse proxy for stop-level population. Naming these builds credibility
rather than costing it.

No em dashes anywhere, in the README, the map copy, or the Devpost writeup.

## 15:30: the actual demo

Pull Google Street View images for the top 3 ranked stops and save them to `assets/`.
A photo of a real bare stop pole with no bench, next to your ranking, is worth more to a
judge than the entire pipeline. If you only have time for one thing after code freeze,
this is it.

## 16:00: Devpost submission

Six fields. Write them before 16:00, not at 16:25.

1. Project name
2. Track: NASA / GeoEmerge
3. Which problem brief, or your own problem description
4. Description, at least one paragraph: what you built, who it helps, how it works
5. Repo link plus the GitHub Pages map link
6. All three team members listed. Check this twice, missing teammates is a common and
   painful mistake.

## Your judgment calls

At 13:30 you look at what A and B have and decide what ships. Use the cut order in
`CLAUDE.md`. Cutting a feature at 13:30 is normal. Debugging a feature at 15:45 is how
teams end up with nothing to submit.

## Do not

- Do not touch `src/lst.py`, `src/gtfs.py`, or `src/context.py`. If A or B's output is
  wrong, tell them, do not fix it yourself. Two people editing one file at 14:00 is how
  the repo breaks.
- Do not make the notebook the deliverable. The map and the CSV are the deliverable. The
  notebook just has to run top to bottom from a fresh kernel by 15:00.

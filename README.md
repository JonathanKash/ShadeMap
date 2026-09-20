# ShadeMap Gainesville

Riders of Gainesville's RTS buses wait for the bus on unshaded asphalt through Florida summers, and the people who wait the longest are the ones without a car. Nobody has a ranked, data-backed list of which stops are hottest, so ShadeMap builds one from NASA Landsat satellite temperatures, bus schedules, shelter data, and census data.

**Live map:** https://jonathankash.github.io/ShadeMap/ (tap any stop for details). Also: the [shade planner](https://jonathankash.github.io/ShadeMap/planner.html) and the [classic map](https://jonathankash.github.io/ShadeMap/classic.html).

![ShadeMap map of Gainesville bus stops colored by priority for shade](assets/map.png)

## What the map shows

Every RTS bus stop is a dot. Color shows priority for shade, from pale for the lowest 40 percent of stops to dark red for the top 5 percent. Bigger dots have more weekday buses. The 20 stops on the "needs shade most" list described below are solid black. Stops with no satellite data or no weekday service are gray and are not ranked.

Use the search box to find a stop or route, and the chips to filter to all stops, the priority top 20, the "needs shade most" list, or stops with no shelter. Tapping a stop opens a panel with its rank, heat, shelter status, a warning when no sheltered stop is within a 5 minute walk on its route, and rider photos when there are any. The classic map shows the same ranking with numbered pins for the top 20 ([screenshot](assets/classic_map.png)).

The **shade planner** answers a what-if: if the city could add shelters at only some stops, which ones reach the most weekday bus visits? You pick how many stops and see the bus visits covered, on a map, with a CSV download. It is a what-if, not a plan or a cost estimate.

The full ranking is in [`outputs/scored_stops.csv`](outputs/scored_stops.csv) and the top 20 are in [`outputs/top_20_stops.csv`](outputs/top_20_stops.csv).

| Rank | Stop | Bus visits per weekday | Nearby summer morning heat | Shelter (OpenStreetMap) |
|---|---|---|---|---|
| 1 | University Village South Apartments | 163 | 107.9 F | none |
| 2 | Weimer Hall | 248 | 110.7 F | none |
| 3 | Southwest Recreation Center | 61 | 109.3 F | none |
| 4 | Gator Corner Dining Facility @ Gale Lemerand | 248 | 109.6 F | none |
| 5 | Southwest Recreation Center | 61 | 108.2 F | none |

**How sure are we of the order?** Read the top 20 as a set of priority stops, not a precise ordering. Stop-level temperature differences are small, close to what one summer of 30 m Landsat can resolve. To test this we split the summer into two independent halves (odd and even days), rebuilt the composite from each, and re-ran the full score. Between 13 and 15 of the 20 stops stayed in the top 20 each time, so the set is mostly stable, and positions within the list, including who is number 1, can swap under measurement noise.

The top 20 is concentrated around the University of Florida campus. That is what the formula produces: campus stops combine hot surroundings with some of the busiest service in the system, and many have no shelter mapped. It is not the result of hand tuning.

## How a stop is scored

A stop ranks higher when it is hotter than most stops, gets more bus visits, has no known shelter, and sits in a census tract where more households have no vehicle:

```
score = heat_percentile * log(1 + daily_trips) * shelter_multiplier * transit_dependence
```

| Term | Meaning |
|---|---|
| `heat_percentile` | Percentile rank (0 to 1) of the average land surface temperature within 100 m of the stop, among all ranked stops. |
| `daily_trips` | Bus visits to the stop on a typical weekday. Used as a stand-in for how many people wait there. |
| `shelter_multiplier` | 1.5 if OpenStreetMap says no shelter, 1.25 if unknown, 1.0 if sheltered. |
| `transit_dependence` | The tract's share of households with no vehicle, scaled from 0.5 (fewest car-free households among ranked stops) to 1.5 (most). Stops with no census value get 1.0. |

There is no model, and the weights were not adjusted to change the ranking.

## Other lists in the data

The map shows the stop ranking above. Three more views are in `outputs/` as CSV files. The first is also on the map as the "needs shade most" chip and the black dots; the route ranking and shelter-distance files are CSV only, and the shelter-distance warning shows in each stop's panel.

**Where the wait itself is worst** ([`outputs/shade_need.csv`](outputs/shade_need.csv)). The main score multiplies by bus visits, so it answers "where would a shelter help the most riders," and busy campus stops lead. This second list asks a different question, "where is standing at the stop hardest," and does not reward busy stops:

```
shade_need = heat_percentile * (1 - green_cover) * shelter_factor * social_vulnerability
```

Any stop with weekday service, satellite data and a shelter status of none or unknown qualifies (814 stops; confirmed sheltered stops are left out). `green_cover` is the share of vegetation within 100 m from Sentinel-2, used as a rough stand-in for bare surroundings. `social_vulnerability` blends the census share of households with no vehicle and of residents 65 and older. Only 4 of its top 20 are also in the main top 20, and the median top-20 stop has 27 bus visits a day versus 158 for the main list.

| Rank | Stop | Bus visits per weekday | Nearby summer morning heat | Green cover within 100 m | Shelter (OpenStreetMap) |
|---|---|---|---|---|---|
| 1 | Westbound NE 39th Ave at Main St | 23 | 110.6 F | 7% | none |
| 2 | Big Lot on NW 13th Street | 37 | 109.0 F | 5% | none |
| 3 | SUBWAY at Newberry Rd | 51 | 111.8 F | 16% | none |
| 4 | GRACE Marketplace | 13 | 107.2 F | 23% | none |
| 5 | NW 16th Ave NW 13th St | 20 | 112.8 F | 21% | none |

**Routes** ([`outputs/route_ranking.csv`](outputs/route_ranking.csv)). A route ranks higher when its stops are, on average, hotter, busier, less likely to have a shelter, and in tracts with more car-free households. Across 26 routes, the top three are Route 33 (Butler Plaza to The Hub), Route 38 and Route 21. Routes through busy hubs get a boost because a stop's bus visits count every route serving it, and the top routes are mostly University of Florida corridor routes.

**Distance to a shelter** ([`outputs/nearest_shelter.csv`](outputs/nearest_shelter.csv)). For every stop and route pair, the nearest stop on the same route that OpenStreetMap lists as sheltered, by straight-line distance and a walking time at 80 m per minute. On 816 of 1,434 stop and route pairs (57 percent) there is no sheltered stop within a 5 minute walk. OpenStreetMap shelter coverage is partial, so read that as "none that OpenStreetMap knows of," an upper bound.

## What a resident can do

In the app view, every stop panel links to a prefilled GitHub issue for reporting wrong shelter information, which needs a GitHub account and a person to check it. Stops with no sheltered stop within a five minute walk on their route (per OpenStreetMap) also show how to ask for one: the City of Gainesville's myGNV request portal and the RTS customer service phone line. The classic map carries both links in every popup. Nothing here promises what the city or RTS will do. Verified corrections go into `outputs/shelter_overrides.csv` with a source.

**For planners: the Shade planner** ([`docs/planner.html`](docs/planner.html), linked from the app view). Pick how many stops could get a shelter, from 5 to 100, and choose either the main ranking or the shade-need list. It shows the weekday bus visits those stops carry, the share of all RTS visits and of visits at stops without a known shelter, the routes they touch, a map, and a CSV download. It is a what-if tool. It does not estimate cost or say what the city will do.

## Method

1. **Heat (NASA Landsat).** Land surface temperature comes from Landsat 8 and 9 Collection 2 Level-2 (`lwir11` band, 30 m resolution), fetched from the [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2) STAC API with no manual downloads. We used 37 scenes from June 2 to September 15, 2026 over Alachua County. Each pixel is cloud-masked individually using the `qa_pixel` band, then the median across all scenes is taken. The USGS scale factor (0.00341802) and offset (149.0) convert to Kelvin, then to Celsius. Each stop gets a 100 m buffer (built in EPSG:6440, Florida North, meters), and we take the mean of the pixels inside it. The county-wide median of the composite is 33.2 C.
2. **Stops and service.** Stop locations and weekday bus visits come from the RTS GTFS feed (Spring 2026, 971 stops), using Wednesday, February 11, 2026 as the representative weekday.
3. **Shelters.** OpenStreetMap via the Overpass API. Each stop takes the nearest OSM bus stop or platform within 25 m. A stop still unknown after that is matched on the OSM `ref` tag, which equals the RTS stop id, if that node is within 100 m (where both methods gave an answer they agreed in 485 of 485 cases). `shelter=yes` is sheltered, `shelter=no` is none, and everything else is unknown.
4. **Transit dependence.** ACS 2024 5-year estimates at census tract level: households with no vehicle (table B08201) and residents 65 and older (table B01001, shown in the data but not used in the score). Numbers come from Census Reporter, a keyless mirror of the same ACS tables. Tract shapes are Census TIGER/Line 2024.
5. **Vegetation context.** Sentinel-2 L2A at 10 m, 17 summer scenes, cloud-masked, median NDVI composite. For each stop we report the share of pixels within 100 m with NDVI above 0.4 (`pct_green`) in `outputs/stop_canopy.csv`. It is shown in the map popups and is not part of the main score. It is used in the separate "where the wait itself is worst" list described above. Greener stops run cooler in our data (r = -0.55 against land surface temperature).
6. **Afternoon check (NASA ECOSTRESS, not scored).** ECOSTRESS ECO_L2T_LSTE v2 from NASA Earthdata / LP DAAC, summer 2026 afternoon overpasses (12:00 to 5:00 PM). Used only to size the gap between morning Landsat values and afternoon heat, described under Limitations.
7. **Scoring and map.** `src/score.py` joins the tables and computes the score. `src/make_map.py` builds the classic static map in `docs/classic.html`, and `src/make_app_data.py` bakes the data file the app view (`docs/app.html`, the default page) loads.

**Result counts:** 971 stops, 915 ranked, 42 excluded for no satellite data, 14 excluded for no weekday service.

### Methods and curriculum

This project follows the NASA GeoEmerge (EMERGE) Data Analysis workflow: acquire public environmental data, clean it (per-pixel cloud masking), analyze it (zonal statistics and ranking), and communicate it to a non-expert audience through a map.

**TODO before submitting:** name the specific EMERGE curriculum textbook and lesson this follows, with a link. The lesson name is not in the repo yet.

## Rider photos

Every stop popup has an **Add a photo of this stop** button. A rider picks or takes a photo, says what date and time they took it, and can add a short note about shade, benches or shelter. The time of day matters here because our satellite data is from the morning and riders wait in the afternoon. Nothing appears on the map until an admin reviews it. Location data inside each photo is removed in the browser before upload. Approved photos show in the stop's popup with the time they were taken.

The button is hidden until the project's Supabase storage is connected, so the map is unchanged without it. Setup and the review steps are in [SUPABASE_SETUP.md](SUPABASE_SETUP.md).

## How to run it

Python 3.11 or newer.

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # on Mac or Linux: .venv/bin/pip

python src/gtfs.py            # stops and weekday trips
cd src && python context.py && cd ..   # shelters and census
python src/lst.py             # Landsat composite and per-stop temperatures
python src/score.py           # scored_stops.csv and top_20_stops.csv
python src/make_map.py        # docs/classic.html

# optional extra lists (outputs/shade_need.csv, route_ranking.csv, nearest_shelter.csv)
python src/lst.py canopy      # Sentinel-2 green cover per stop
python src/shade_need.py
python src/route_ranking.py
python src/nearest_shelter.py

# data file for the app view (docs/app.html), run last so it picks up everything above
python src/make_app_data.py
```

Every download is cached in `data/`, so a rerun is fast. The handoff files each step produces are committed in `outputs/`, so you can also run `score.py` and `make_map.py` directly without the earlier steps.

## Limitations

- **Shelter data is partial.** OpenStreetMap coverage of bus shelters is uneven. Of the 971 stops, 370 are unknown and 495 are none. "None" means OpenStreetMap says no shelter, not that we confirmed it on the ground, and unknown is treated as somewhere in between.
- **Bus visits are a ridership proxy.** RTS does not publish per-stop ridership, so we use the number of scheduled bus visits per weekday. The schedule is from the Spring 2026 feed, which ends May 3, 2026. That is the newest feed we found, but it predates this analysis.
- **Morning satellite temperatures, over one summer.** Landsat passes over Gainesville around 10:30 am, so the temperatures underestimate the mid-afternoon peak a rider feels. The ranking is relative across stops, so the ordering still means something, but the Celsius and Fahrenheit values are not afternoon temperatures. The data is a seasonal median, not a single heat wave.
  - **How big the gap is.** We checked with NASA ECOSTRESS (70 m). On the clearest afternoon, August 14, 2026 at 2:52 PM, the median surface temperature in the Gainesville tile was 44.3 C (about 112 F) and a quarter of the area was above 50 C (122 F). Our morning Landsat composite median is 33.2 C, so afternoon surfaces run roughly 10 C hotter than the values on the map.
  - **Why the ranking does not use it.** Only 3 of 20 summer afternoon ECOSTRESS overpasses were usable after cloud screening, because Florida summer afternoons are mostly cloudy. Ranking individual stops from those scenes agreed poorly with the Landsat layer (rank agreement about 0.2), so we did not build a per-stop afternoon ranking. The afternoon figures above describe the city as a whole.
- **30 m pixels blur the stop with its surroundings.** The 100 m buffer is a neighborhood average, not the temperature of the pad the rider stands on.
- **42 of 971 stops (4.3 percent) have no temperature data.** This is not cloud cover. The Landsat surface temperature product has a known gap in its emissivity input over part of west-central Gainesville. We chose not to estimate these values: every temperature in the ranking is a measured satellite value. We show these stops as gray and do not rank them, rather than scoring them as cool.
- **Census data is tract level, and some tracts are tiny.** A tract is a coarse proxy for who actually waits at a given stop. The tract around the Reitz Union has only 164 households, so its 30.5 percent no-vehicle figure has a margin of error of about 17 points, and 19 of the top 20 stops sit in two such campus tracts. We redrew each tract's value within its margin 1,000 times: the top 10 stops stay in the top 20 at least 90 percent of the time, while ranks 15 to 20 are close calls ([`outputs/ranking_stability.md`](outputs/ranking_stability.md)). Only census uncertainty was varied.
- **Some top stops are the same place.** Southwest Recreation Center appears three times (ranks 3, 5 and 8) under different stop ids.
- **Shade itself is not measured.** The analysis does not include tree canopy, building shadows, or sun angle. The only protection input is whether OpenStreetMap lists a shelter at the stop. The ranking shows where heat exposure and need look highest and where no shelter is known, not how shaded each stop is. The popups show nearby green cover from satellite vegetation data as context, but that is a vegetation measure, not shade. It does not affect the main ranking, and the separate "where the wait itself is worst" list uses it only as a rough stand-in for bare surroundings. Tree canopy and shadow analysis would be a natural next step.
- **Descriptive only.** The list shows where the data says heat exposure is highest. It is not a recommendation for what any agency should build.

## Repository layout

```
src/lst.py       Landsat fetch, scale, composite, per-stop temperatures
src/gtfs.py      stop parsing and weekday trip counts
src/context.py   OpenStreetMap shelters and census tracts
src/score.py     join, score, rank
src/make_map.py  builds the classic map (docs/classic.html)
src/make_app_data.py   bakes docs/app_data.json for the app view
src/shade_need.py, route_ranking.py, nearest_shelter.py   the extra lists
outputs/         handoff CSVs, the final ranked CSVs, and the extra lists
docs/            served by GitHub Pages: index.html (redirects to app.html, the default map),
                 app.html, planner.html, classic.html, and the photo upload code
supabase/        one-time storage setup for rider photos (see SUPABASE_SETUP.md)
assets/          screenshots and photos
analysis.ipynb   the analysis, runs top to bottom
```

## Data sources

- Landsat 8 and 9 Collection 2 Level-2 (NASA / USGS), via Microsoft Planetary Computer
- ECOSTRESS ECO_L2T_LSTE v2 (NASA), via NASA Earthdata / LP DAAC, afternoon check only
- Sentinel-2 L2A (ESA), via Microsoft Planetary Computer, green cover in popups only
- RTS (Regional Transit System, Gainesville) GTFS feed
- OpenStreetMap contributors, via the Overpass API
- U.S. Census Bureau ACS 5-year estimates (via Census Reporter) and TIGER/Line shapes
- Basemap tiles from Esri

# Devpost draft (paste each field; fill the marked blanks)

Every number below comes from the repo (`outputs/impact_summary.md`, `README.md`,
`outputs/ranking_stability.md`). If a number changes, regenerate those files and update it here.

## Blanks only the team can fill

- [x] **EMERGE curriculum:** filled in below (Textbook 1, led by Chapter 4 Temperature, Rainfall & Vegetation, plus three supporting lessons). Each lesson was checked against its page on geo-di-lab.github.io/emerge-lessons, not just its title, and the vegetation and temperature numbers were recomputed from the CSVs (see section 7 of `analysis.ipynb`). Someone on the team should skim the four lesson pages once and confirm they are happy with the wording, because Dr. Yang leads EMERGE and is a judge.
- [x] **Teammates:** Lucas Fonte, Francisco Rodriguez, Jonathan Kashi. **Typing names is not enough.** Each person needs a Devpost account and must be added to the project's team on Devpost (invite them, and they accept). Check the team list on the project page twice before submitting.
- [x] **Deadline:** the track PDF says **submit by 5 PM**. The repo planning docs say 4:30 PM, which is out of date. Aim to submit by 4:30 PM anyway.
- [ ] **Track name:** the track PDF is titled "NASA and Environmental Data Track". Pick whichever Devpost option matches that (the planning docs called it "NASA / GeoEmerge").
- [ ] **Demo photos:** add one or two real photos of top stops if the team has them (see `ADMIN_PHOTOS.md`). Skip the sentence in the description if there are none.
- [ ] **RTS feed link:** the GTFS download URL in `src/gtfs.py` returned a non-zip response when we last tried it from a script (3:15 PM). If it moved, update `GTFS_URL` so "how to run it" still works, and do not link that URL on Devpost.

## 1. Project name

ShadeMap Gainesville

## 2. Track

NASA and Environmental Data (the EMERGE track, CityCamp Gainesville Hack Day)

## 3. Problem brief

Our own: Gainesville riders wait on unshaded asphalt through Florida summers, and the people who wait longest are the ones without a car. Nobody has a public, data-backed list of which RTS bus stops are worst, so shade and shelters cannot be prioritized with evidence.

## 4. Description

**The problem.** RTS runs 971 stops across Gainesville. On a typical weekday its buses make 39,703 visits to those stops, 44 percent of them between 11 am and 5 pm, the hottest part of the day. About half of those visits (49 percent) are at stops that OpenStreetMap lists as having no shelter, and another 28 percent are at stops where shelter status is unknown. Only 23 percent are at stops listed as sheltered.

**What we built.** ShadeMap ranks every RTS stop by how much a shelter or shade structure would matter there, and puts the answer in an interactive map anyone can open on a phone. Each stop gets a score from four things: how hot its surroundings are (NASA Landsat 8 and 9 land surface temperature, a per-pixel median of 37 cloud-masked summer 2026 scenes), how many buses stop there (RTS GTFS schedule), whether it has a shelter (OpenStreetMap), and how many nearby households have no car (US Census ACS). The formula is one sentence: a stop ranks higher when it is hotter than most stops, gets more bus visits, has no known shelter, and sits in a tract with more car-free households. We did not tune the weights to make the list look better.

**Who it helps.** The map is built for residents, riders and city staff. Every stop panel links to a prefilled report if our shelter information is wrong, and stops with no sheltered stop within a five minute walk on their route show how to ask for one through the City of Gainesville request portal (myGNV) and the RTS customer service line. A Shade planner lets staff pick how many stops could get a shelter and see the weekday bus visits that reaches, on a map and as a downloadable list. It is a what-if tool. It does not estimate cost or say what the city will do. Riders can also send a photo of a stop, which is reviewed by a person before it appears on the map. The two top 10 lists together carry 6 percent of weekday bus visits.

**Two lists, on purpose.** The main ranking multiplies by bus visits, so busy campus stops lead. A second list, "needs shade most," ignores bus volume so quiet stops in hot, car-free or senior neighborhoods still count. Only 4 stops appear on both top 20 lists, and the map shows the second list as black dots. Because campus stops dominate a citywide ranking, the map shows two top 10 lists instead: stops within a mile of the UF campus and stops beyond that mile. Stops far from campus carry 36 percent of weekday bus visits, and their top 10 (Oaks Mall and apartment stops on routes 75, 52 and 15 in northwest Gainesville) ranks 51st to 76th citywide, so a single top 20 would never have shown them.

**How we checked it.** We recomputed every stop's score with separately written code and got identical results (no rank changed). Census numbers are estimates, and the campus tract with the most top-20 stops has only 164 households, so we redrew each tract's value within its margin of error 1,000 times. The top 10 stops stay in the top 20 at least 90 percent of the time, and ranks 15 to 20 are close calls. We also checked NASA ECOSTRESS afternoon data: on the clearest afternoon (August 14, 2026, 2:52 PM) the median surface was 44.3 C, against 33.2 C for our morning Landsat composite, so the ranking understates afternoon heat. We use it only to say so.

**Limitations, plainly.** OpenStreetMap shelter coverage is partial (106 stops sheltered, 495 none, 370 unknown), so "none" means OpenStreetMap says none, not that we confirmed it. Bus visits are a stand-in for how many people wait, not a rider count. The schedule is RTS's Spring 2026 feed, using one representative Wednesday. 42 stops have no temperature data because of a known gap in the Landsat surface temperature product, and they are shown as "no data," not scored as cool. Census data is tract level. Shade itself is not measured. The list describes where the data says heat exposure is highest and does not recommend what any agency should build.

**Built with.** Python, pandas, geopandas, NASA/USGS Landsat 8 and 9, NASA ECOSTRESS, ESA Sentinel-2, Microsoft Planetary Computer, OpenStreetMap and the Overpass API, RTS GTFS, US Census ACS and TIGER/Line, Leaflet, Supabase (rider photo uploads), GitHub Pages.

**EMERGE curriculum used: Textbook 1, Data Analysis** ("EMERGE Lessons", https://geo-di-lab.github.io/emerge-lessons/). Our main lesson is **Chapter 4, Temperature, Rainfall & Vegetation**, and we apply its vegetation half at the scale of a single bus stop.

- **What the lesson teaches.** It maps land surface temperature and vegetation for Florida from satellite data and charts them together, measuring vegetation with NDVI = (NIR - Red) / (NIR + Red) from Sentinel-2.
- **What we did.** We computed NDVI from Sentinel-2 as a median composite of 17 cloud-masked summer scenes and summarized it in a 100 m circle around each of the 971 stops, then set it next to the NASA Landsat temperature in the same circle. Across the 929 stops with both, greener stops are cooler (correlation -0.55). The least green fifth of stops averages 8.2 F hotter than the greenest fifth (104.2 F vs 96.0 F on summer mornings). That is our own finding, a correlation and not a claim about what planting would do.
- **Vegetation in our rankings.** It feeds the "needs shade most" list as (1 - green cover). That list's top 20 stops average 21 percent green cover, against 57 percent across all 814 eligible stops.
- **Where we differ.** The lesson uses 1 km MODIS temperature and Google Earth Engine. We use finer Landsat (30 m) and ECOSTRESS (70 m) with Python and Microsoft Planetary Computer. We leave out rainfall and multi-year trend charts because we analyze one summer. The lesson gives no NDVI cutoffs and does not state a link between vegetation and temperature, so our "green" cutoff (NDVI above 0.4) and the relationship above are our own.

Three other lessons shaped the work: **Chapter 3, Vegetation & Water Indices** (the NDVI method), **Chapter 4, Introduction to Risk Mapping** (combining environmental layers into one simple map, which we adapt from mosquito habitat to heat exposure at bus stops), and **Chapter 5, Communicate the Science** (plain language and stated uncertainty).

We did not use the geoemerge Python package, Textbook 2 (Geospatial AI), Google Earth Engine, or GLOBE Observer data.

**Data and credits.**
- NASA/USGS Landsat 8 and 9 Collection 2 Level-2, via Microsoft Planetary Computer: https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2
- NASA ECOSTRESS ECO_L2T_LSTE v2, via NASA Earthdata / LP DAAC: https://www.earthdata.nasa.gov (afternoon check only)
- ESA Sentinel-2 L2A, via Microsoft Planetary Computer: https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a
- RTS (Regional Transit System) GTFS schedule, Spring 2026: https://go-rts.com
- OpenStreetMap contributors (shelters and the University of Florida boundary), via the Overpass API: https://www.openstreetmap.org/copyright
- U.S. Census Bureau ACS 5-year estimates (via Census Reporter, https://censusreporter.org) and TIGER/Line tract shapes
- Basemap tiles by Esri; maps drawn with Leaflet (https://leafletjs.com); Public Sans typeface (license in `docs/fonts/`)
- Code: Python with pandas, geopandas, rasterio and rioxarray, odc-stac, pystac-client, planetary-computer, folium, matplotlib and Jupyter; rider photos stored with Supabase; hosted on GitHub Pages.

**Reuse and upkeep.** Everything is in the repo and reruns from committed files (`pip install -r requirements.txt`, then the scripts listed in the README). Another city can swap in its own transit schedule and study area. Shelter corrections and rider photos go through a documented review process (`ADMIN_PHOTOS.md`, `SUPABASE_SETUP.md`, `SECURITY.md`), so a small team or a volunteer can keep the data current. What we would do next: a live bus layer (built, but off until RTS provides an API key), tree canopy and shadow analysis, and ridership counts if RTS shares them.

## 5. Links

- Repo: https://github.com/JonathanKash/ShadeMap
- Live map: https://jonathankash.github.io/ShadeMap/
- Shade planner: https://jonathankash.github.io/ShadeMap/planner.html
- Classic map (numbered top 20): https://jonathankash.github.io/ShadeMap/classic.html
- EMERGE Textbook 1: https://geo-di-lab.github.io/emerge-lessons/

## 6. Team

Lucas Fonte, Francisco Rodriguez, Jonathan Kashi.

Add all three through Devpost's team invite, not just in the text. Each teammate needs a Devpost account and has to accept the invite. Check the team list on the project page twice before submitting.

# Devpost draft (paste each field; fill the marked blanks)

Every number below comes from the repo (`outputs/impact_summary.md`, `README.md`,
`outputs/ranking_stability.md`). If a number changes, regenerate those files and update it here.

## Blanks only the team can fill

- [ ] **EMERGE curriculum:** name the textbook and lesson we followed, with a link. Kashi's notes say the workflow matches Textbook 1 (Data Analysis). The lesson name is not in the repo yet.
- [ ] **Teammates:** list all three on the Devpost (Jonathan Kashi, the Stream C teammate, and the Stream B teammate). Check twice.
- [ ] **Deadline:** the repo docs say 4:30 PM, Kashi's notes from the track PDF say 5 PM. Confirm which and submit well before it.
- [ ] **Demo photos:** add one or two real photos of top stops if the team has them (see `ADMIN_PHOTOS.md`). Skip the sentence in the description if there are none.

## 1. Project name

ShadeMap Gainesville

## 2. Track

NASA / GeoEmerge

## 3. Problem brief

Our own: Gainesville riders wait on unshaded asphalt through Florida summers, and the people who wait longest are the ones without a car. Nobody has a public, data-backed list of which RTS bus stops are worst, so shade and shelters cannot be prioritized with evidence.

## 4. Description

**The problem.** RTS runs 971 stops across Gainesville. On a typical weekday its buses make 39,703 visits to those stops, 44 percent of them between 11 am and 5 pm, the hottest part of the day. About half of those visits (49 percent) are at stops that OpenStreetMap lists as having no shelter, and another 28 percent are at stops where shelter status is unknown. Only 23 percent are at stops listed as sheltered.

**What we built.** ShadeMap ranks every RTS stop by how much a shelter or shade structure would matter there, and puts the answer in an interactive map anyone can open on a phone. Each stop gets a score from four things: how hot its surroundings are (NASA Landsat 8 and 9 land surface temperature, a per-pixel median of 37 cloud-masked summer 2026 scenes), how many buses stop there (RTS GTFS schedule), whether it has a shelter (OpenStreetMap), and how many nearby households have no car (US Census ACS). The formula is one sentence: a stop ranks higher when it is hotter than most stops, gets more bus visits, has no known shelter, and sits in a tract with more car-free households. We did not tune the weights to make the list look better.

**Who it helps.** The map is built for residents, riders and city staff. Every stop panel links to a prefilled report if our shelter information is wrong, and stops with no sheltered stop within a five minute walk on their route show how to ask for one through the City of Gainesville request portal (myGNV) and the RTS customer service line. A Shade planner lets staff pick how many stops could get a shelter and see the weekday bus visits that reaches, on a map and as a downloadable list. It is a what-if tool. It does not estimate cost or say what the city will do. The 20 highest-priority stops carry 8 percent of weekday bus visits from 2 percent of stops.

**Two lists, on purpose.** The main ranking multiplies by bus visits, so busy campus stops lead. A second list, "needs shade most," ignores bus volume so quiet stops in hot, car-free or senior neighborhoods still count. Only 4 stops appear on both top 20 lists, and the map shows the second list as black dots.

**How we checked it.** We recomputed the bus visit counts and every score from the raw files with separate code and got identical results. Census numbers are estimates, and the campus tract with the most top-20 stops has only 164 households, so we redrew each tract's value within its margin of error 1,000 times. The top 10 stops stay in the top 20 at least 90 percent of the time, and ranks 15 to 20 are close calls. We also checked NASA ECOSTRESS afternoon data: on the clearest afternoon (August 14, 2026, 2:52 PM) the median surface was 44.3 C, against 33.2 C for our morning Landsat composite, so the ranking understates afternoon heat. We use it only to say so.

**Limitations, plainly.** OpenStreetMap shelter coverage is partial (106 stops sheltered, 495 none, 370 unknown), so "none" means OpenStreetMap says none, not that we confirmed it. Bus visits are a stand-in for how many people wait, not a rider count. The schedule is RTS's Spring 2026 feed, using one representative Wednesday. 42 stops have no temperature data because of a known gap in the Landsat surface temperature product, and they are shown as "no data," not scored as cool. Census data is tract level. Shade itself is not measured. The list describes where the data says heat exposure is highest and does not recommend what any agency should build.

**Built with.** Python, pandas, geopandas, NASA/USGS Landsat 8 and 9, NASA ECOSTRESS, ESA Sentinel-2, Microsoft Planetary Computer, OpenStreetMap and the Overpass API, RTS GTFS, US Census ACS and TIGER/Line, Leaflet, GitHub Pages.

**EMERGE.** This follows the NASA GeoEmerge Data Analysis workflow: acquire public environmental data, clean it (per-pixel cloud masking), analyze it (zonal statistics and ranking), and communicate it to a non-expert audience through a map. [FILL: textbook and lesson name, with link.]

## 5. Links

- Repo: https://github.com/JonathanKash/ShadeMap
- Live map: https://jonathankash.github.io/ShadeMap/
- Shade planner: https://jonathankash.github.io/ShadeMap/planner.html

## 6. Team

[FILL: all three teammates.]

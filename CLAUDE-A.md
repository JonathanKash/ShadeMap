# CLAUDE-A.md

Stream A: satellite heat data. Read `CLAUDE.md` and `CONTRACTS.md` first.

You own `src/lst.py` and nothing else. Your single deliverable is
`outputs/stop_lst.csv` by 12:00.

You are the critical path. If your data is late, the project has no NASA story and the
track prize is gone. Everything else in this repo can be faked. This cannot.

## Your job in one sentence

Get Landsat surface temperature over Alachua County, buffer each bus stop by 100m, and
write the mean temperature per stop.

## Do this first, before anything else

Get a single Landsat scene loading and plotted. Not a pipeline, not a function, just a
notebook cell that produces a picture of Gainesville in Celsius. Until that image renders,
nothing else you write matters.

```
pip install pystac-client planetary-computer odc-stac rioxarray geopandas
```

Microsoft Planetary Computer, collection `landsat-c2-l2`, no auth needed beyond
`planetary_computer.sign_inplace`. Filter to `platform in ["landsat-8", "landsat-9"]`,
bbox around Alachua County, summer 2026, `eo:cloud_cover < 20`.

The band you want is `lwir11` (surface temperature). Collection 2 Level-2 ST is scaled:

```
celsius = raw * 0.00341802 + 149.0 - 273.15
```

**Verify that scale and offset against the band metadata in the item assets rather than
trusting those numbers.** If your output is not roughly 25 to 50 C for a Florida summer
afternoon, the scaling is wrong. Sanity check before you build on top of it.

Also apply the `qa_pixel` cloud mask. Clouds read as cold and will silently drag your
means down.

## Then

1. Median composite across 3 to 6 cloud-free scenes. If this is slow or fiddly, use one
   good scene and move on. Note which you did in `scene_dates`.
2. Load `outputs/stops.geojson` from B. If it is not there yet, parse GTFS `stops.txt`
   yourself, it is three lines with pandas, do not wait for anyone.
3. Reproject stops to **EPSG:6440** (Florida North, meters), buffer 100m, run zonal stats
   against the LST raster. `rasterstats.zonal_stats` or `rioxarray` clip per geometry.
4. Write `outputs/stop_lst.csv` exactly per the contract.

## Rules

- Cache every download to `data/`. Re-running a STAC fetch three times will cost you an
  hour you do not have.
- Print the shape, CRS, and min/max after every step. Wrong CRS and unscaled bands are the
  two bugs that eat hackathon afternoons, and both are silent.
- Stops with no coverage keep their row with `pixel_count = 0`. Never drop rows, C's join
  depends on the row count matching.
- Do not touch `src/score.py`. The scoring formula is C's. If you think the formula is
  wrong, say so in chat, do not edit it.

## If you are behind at 11:30

Cut in this order: median composite (use one scene), then the 100m buffer (sample the
single pixel under each stop point instead). A single-pixel single-scene version still
produces a valid CSV and a valid map. Ship something that loads.

## Do not

- Do not start with ECOSTRESS. It needs an Earthdata login and AppEEARS job queuing that
  can take longer than the hackathon. Only consider it after `stop_lst.csv` exists and it
  is before 13:00.
- Do not build an abstraction layer for multiple data sources. There is one data source.

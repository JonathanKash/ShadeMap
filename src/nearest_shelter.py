"""Nearest sheltered stop on the same route, per stop.

For every (stop, route) pair: the closest stop on that route that OSM marks
sheltered, the straight-line distance, and the walk time at 80 m/min. Pairs
with no sheltered stop within a 5 minute walk are flagged; those are the
places where a rider on that route has no nearby sheltered place to wait.

Writes outputs/nearest_shelter.csv (long format, one row per stop-route).
New file, owned by Stream A. Consumes B's outputs only, touches nothing else.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

WALK_M_PER_MIN = 80.0  # standard planning walking speed
WALK_LIMIT_MIN = 5.0

root = Path(__file__).resolve().parent.parent
ctx = pd.read_csv(root / "outputs" / "stops_context.csv",
                  dtype={"stop_id": str, "tract_geoid": str})
stops = gpd.read_file(root / "outputs" / "stops.geojson")[["stop_id", "geometry"]]
stops["stop_id"] = stops["stop_id"].astype(str)

g = ctx.merge(stops, on="stop_id")
g = gpd.GeoDataFrame(g, geometry="geometry", crs="EPSG:4326").to_crs("EPSG:6440")
print(f"stops: {g.shape}, sheltered: {(g.shelter_status == 'sheltered').sum()}")

# long form: one row per stop-route
g["route_list"] = g["routes"].fillna("").str.split(",")
long = g.explode("route_list")
long["route"] = long["route_list"].str.strip()
long = long[long["route"] != ""]
print(f"stop-route pairs: {len(long)}, routes: {long['route'].nunique()}")

rows = []
for route, grp in long.groupby("route"):
    sheltered = grp[grp.shelter_status == "sheltered"]
    for _, s in grp.iterrows():
        if len(sheltered) == 0:
            nearest = None
        else:
            d = sheltered.geometry.distance(s.geometry)
            # a sheltered stop is its own nearest shelter at distance 0
            i = d.idxmin()
            nearest = (sheltered.loc[i], float(d.loc[i]))
        if nearest is None:
            rows.append((s.stop_id, s.stop_name, route, None, None, None, None, True))
        else:
            ns, dist = nearest
            walk = dist / WALK_M_PER_MIN
            rows.append((s.stop_id, s.stop_name, route, ns.stop_id, ns.stop_name,
                         round(dist), round(walk, 1), walk > WALK_LIMIT_MIN))

out = pd.DataFrame(rows, columns=[
    "stop_id", "stop_name", "route", "nearest_sheltered_stop_id",
    "nearest_sheltered_stop_name", "distance_m", "walk_min",
    "no_shelter_within_5min",
])
n_flag = int(out.no_shelter_within_5min.sum())
n_no_shelter_route = int(out.nearest_sheltered_stop_id.isna().sum())
print(f"flagged pairs (no sheltered stop within {WALK_LIMIT_MIN:.0f} min walk): "
      f"{n_flag} of {len(out)} ({n_flag / len(out):.0%})")
print(f"  of which on routes with no OSM-sheltered stop at all: {n_no_shelter_route}")
by_route = out.groupby("route").no_shelter_within_5min.mean().sort_values(ascending=False)
print("worst routes (share of stops flagged):")
print((by_route.head(8) * 100).round(0).astype(int).to_string())

out_path = root / "outputs" / "nearest_shelter.csv"
out.to_csv(out_path, index=False)
print(f"wrote {out_path}")

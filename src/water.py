"""Nearest OSM drinking fountain per stop. Stream A file.

Heat safety context: a rider waiting at a hot stop with no water nearby is
worse off than the temperature alone says. Coverage caveat mirrors shelters:
OSM maps fountains best on campus and in parks, so "no fountain within a
5 minute walk" means "none that OSM knows of", an upper bound.

Writes outputs/stop_water.csv and docs/fountains.json (for the map layer).
Run: .venv/Scripts/python src/water.py
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "drinking_water_osm.json"
WALK_M_PER_MIN = 80.0
WALK_LIMIT_MIN = 5.0

OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = ('[out:json][timeout:60];('
         'node["amenity"="drinking_water"](29.55,-82.55,29.78,-82.20);'
         'way["amenity"="drinking_water"](29.55,-82.55,29.78,-82.20);'
         ');out center;')


def fetch():
    CACHE.parent.mkdir(exist_ok=True)
    if not CACHE.exists():
        r = requests.post(OVERPASS, data={"data": QUERY}, timeout=120, headers={
            "User-Agent": "ShadeMap-Gainesville/1.0 (github.com/JonathanKash/ShadeMap)"})
        r.raise_for_status()
        CACHE.write_bytes(r.content)
    return json.loads(CACHE.read_text(encoding="utf-8"))


def main():
    els = fetch().get("elements", [])
    pts = []
    for e in els:
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if lat is not None and lon is not None:
            pts.append((float(lat), float(lon)))
    print(f"fountains from OSM: {len(pts)}")

    fountains = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([p[1] for p in pts], [p[0] for p in pts]),
        crs="EPSG:4326").to_crs("EPSG:6440")

    stops = gpd.read_file(ROOT / "outputs" / "stops.geojson").to_crs("EPSG:6440")
    stops["stop_id"] = stops["stop_id"].astype(str)

    rows = []
    for _, s in stops.iterrows():
        d = fountains.geometry.distance(s.geometry)
        dist = float(d.min())
        walk = dist / WALK_M_PER_MIN
        rows.append((s.stop_id, s.stop_name, round(dist), round(walk, 1),
                     walk > WALK_LIMIT_MIN))
    df = pd.DataFrame(rows, columns=[
        "stop_id", "stop_name", "nearest_fountain_m", "walk_min",
        "no_water_within_5min"])
    n_flag = int(df.no_water_within_5min.sum())
    print(f"stops with no OSM fountain within {WALK_LIMIT_MIN:.0f} min walk: "
          f"{n_flag} of {len(df)} ({n_flag / len(df):.0%})")
    print(f"walk_min median {df.walk_min.median():.1f}, "
          f"p10 {df.walk_min.quantile(0.1):.1f}, p90 {df.walk_min.quantile(0.9):.1f}")

    out = ROOT / "outputs" / "stop_water.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out}")

    (ROOT / "docs" / "fountains.json").write_text(
        json.dumps({"source": "OpenStreetMap amenity=drinking_water, partial coverage",
                    "fountains": [[round(p[0], 6), round(p[1], 6)] for p in pts]},
                   separators=(",", ":")), encoding="utf-8")
    print("wrote docs/fountains.json")


if __name__ == "__main__":
    main()

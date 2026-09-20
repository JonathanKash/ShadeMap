"""Split the stop ranking into near-campus and far-from-campus zones, top 10 of each.

Run from repo root after score.py:  cd src && ../.venv/bin/python campus.py
Writes outputs/stop_campus.csv, outputs/priority_near_far_campus.csv and .md, docs/campus.json.

Why: the main ranking is dominated by University of Florida campus stops (19 of the old top 20),
so the rest of Gainesville disappears from the top of the list. Two zones fix that:
  near campus          = within 1 mile of the UF campus, campus included
  far from campus      = everything beyond 1 mile
Distance is measured from the EDGE of the campus (the OpenStreetMap boundary of the University
of Florida, main campus plus East Campus), not from a center point: UF is about 3 km across,
so a mile around a center point would not even cover the campus.

Ranking inside each zone uses the SAME score as the main ranking (heat percentile is still
citywide); nothing is re-weighted. Near campus includes student apartments and much of
downtown and Midtown; the table shows census columns so a reader can see who lives nearby.
"""
import json
import time

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union

from gtfs import ROOT

DATA, OUT, DOCS = ROOT / "data", ROOT / "outputs", ROOT / "docs"
CACHE = DATA / "overpass_uf_campus.json"
NEAR_MILES = 1.0
NEAR_M = NEAR_MILES * 1609.344
TOP_N = 10
UA = {"User-Agent": "ShadeMap-hackathon/1.0 (CityCamp Gainesville)"}
QUERY = """[out:json][timeout:60];
(
  way["amenity"="university"]["name"~"University of Florida"](29.60,-82.42,29.72,-82.28);
  relation["amenity"="university"]["name"~"University of Florida"](29.60,-82.42,29.72,-82.28);
);
out geom;"""
MIRRORS = ["https://overpass.kumi.systems/api/interpreter", "https://lz4.overpass-api.de/api/interpreter",
           "https://overpass-api.de/api/interpreter"]  # the main server often times out


def fetch_boundary() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    DATA.mkdir(exist_ok=True)
    for attempt in range(2):
        for url in MIRRORS:
            try:
                r = requests.post(url, data={"data": QUERY}, headers=UA, timeout=90)
                if r.ok and r.json().get("elements"):
                    CACHE.write_text(json.dumps(r.json()))
                    return r.json()
            except (requests.RequestException, ValueError):
                pass
        time.sleep(5)
    raise RuntimeError("could not fetch the UF boundary from any Overpass mirror")


def campus_polygon() -> gpd.GeoSeries:
    polys = []
    for e in fetch_boundary()["elements"]:
        lines = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in e.get("members", [])
                 if m["type"] == "way" and m.get("role") in ("outer", "") and len(m.get("geometry", [])) > 1]
        polys += list(polygonize(unary_union(lines)))
    poly = gpd.GeoSeries([unary_union(polys)], crs="EPSG:4326").to_crs("EPSG:6440")
    area_km2 = poly.area.iloc[0] / 1e6
    assert 5 < area_km2 < 12, f"campus area {area_km2:.1f} km2 is implausible (UF main campus is about 8 km2)"
    print(f"campus polygon: {area_km2:.2f} km2")
    return poly


def main() -> None:
    poly = campus_polygon().iloc[0]
    d = pd.read_csv(OUT / "scored_stops.csv", dtype={"stop_id": str})
    pts = gpd.GeoSeries(gpd.points_from_xy(d.stop_lon, d.stop_lat), crs="EPSG:4326").to_crs("EPSG:6440")
    d["dist_to_campus_m"] = [round(poly.distance(p), 1) for p in pts]
    d["near"] = d["dist_to_campus_m"] <= NEAR_M
    d[["stop_id", "near", "dist_to_campus_m"]].rename(columns={"near": "near_campus"}).to_csv(OUT / "stop_campus.csv", index=False)

    ranked = d[d["rank"].notna()].copy()
    ranked["area"] = ranked["near"].map({True: "near campus", False: "far from campus"})
    ranked = ranked.sort_values("rank")
    ranked["area_rank"] = ranked.groupby("area").cumcount() + 1  # rank order is already by score
    cols = ["area", "area_rank", "rank", "stop_id", "stop_name", "routes", "daily_trips", "mean_lst_f",
            "shelter_status", "pct_no_vehicle", "pct_65_plus", "score"]
    top = pd.concat([ranked[(ranked.area == a) & (ranked.area_rank <= TOP_N)] for a in ("far from campus", "near campus")])
    top = top[cols].rename(columns={"rank": "citywide_rank"}).round({"pct_no_vehicle": 1, "pct_65_plus": 1, "score": 2})
    top.to_csv(OUT / "priority_near_far_campus.csv", index=False)

    # small file for the app and planner: stop_id -> [near campus 1/0, rank within its zone (0 if unranked)]
    grp = ranked.set_index("stop_id")["area_rank"].to_dict()
    (DOCS / "campus.json").write_text(json.dumps(
        {r.stop_id: [int(r.near), int(grp.get(r.stop_id, 0))] for r in d.itertuples()}, separators=(",", ":")))

    total = d["daily_trips"].sum()
    far = d[~d.near]
    uns = d[d.shelter_status != "sheltered"]
    both = top.copy()
    lines = [
        "# Top 10 near campus and top 10 far from campus (generated by src/campus.py)", "",
        f"Near campus means within {NEAR_MILES:g} mile of the University of Florida campus edge (OpenStreetMap boundary), "
        "campus included. Far from campus is everything beyond that. Each zone is ranked with the same score as the main ranking.", "",
        f"- {int(d.near.sum())} of {len(d)} stops are near campus and {len(far)} are far from it.",
        f"- Stops far from campus carry {100 * far.daily_trips.sum() / total:.0f} percent of weekday bus visits.",
        f"- Of the visits at stops with no known shelter, {100 * uns[~uns.near].daily_trips.sum() / uns.daily_trips.sum():.0f} percent are far from campus.",
        f"- The two top 10 lists together carry {both.daily_trips.sum():,.0f} bus visits a weekday, "
        f"{100 * both.daily_trips.sum() / total:.0f} percent of the system total.", "",
        "## Top 10 far from campus", "",
    ]
    for a, title in (("far from campus", None), ("near campus", "## Top 10 near campus")):
        if title:
            lines += ["", title, ""]
        lines += ["| # | Stop | Routes | Visits/day | Shelter | No-car households | City rank |", "|---|---|---|---|---|---|---|"]
        for r in top[top.area == a].itertuples():
            lines.append(f"| {r.area_rank} | {r.stop_name} | {r.routes} | {r.daily_trips} | {r.shelter_status} | "
                         f"{r.pct_no_vehicle:.0f}% | {int(r.citywide_rank)} |")
    lines += ["", "Limits: the campus boundary is from OpenStreetMap. Near campus includes student apartments, "
              "much of downtown and Midtown. Shelter status is OpenStreetMap-based and partial.", ""]
    (OUT / "priority_near_far_campus.md").write_text("\n".join(lines))
    print("\n".join(lines[4:8]))
    print(top[["area", "area_rank", "citywide_rank", "stop_name", "routes", "daily_trips", "shelter_status", "pct_no_vehicle"]].to_string(index=False))
    print("dist to campus for the far top 10 (m):", d[d.stop_id.isin(top[top.area == "far from campus"].stop_id)].dist_to_campus_m.round(0).tolist())


if __name__ == "__main__":
    main()

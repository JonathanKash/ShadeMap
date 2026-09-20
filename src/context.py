"""Stream B: OSM shelter matching and ACS census join for each RTS stop.

Run from repo root: .venv/bin/python src/context.py   (writes outputs/stops_context.csv)
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from gtfs import build_daily_trips, load_stops

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"

METRIC_CRS = "EPSG:6440"  # NAD83(2011) / Florida North, meters (checked with pyproj)
UA = {"User-Agent": "ShadeMap-hackathon/1.0 (CityCamp Gainesville)"}  # Overpass 406s without one

# --- OSM shelters ---------------------------------------------------------------------

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_CACHE = DATA / "overpass_bus_stops.json"
OVERPASS_QUERY = """[out:json][timeout:60];
(
  node["highway"="bus_stop"](29.58,-82.48,29.73,-82.25);
  node["public_transport"="platform"](29.58,-82.48,29.73,-82.25);
);
out body;"""
MATCH_M = 25  # CLAUDE-B.md: nearest OSM node within about 25 m


def fetch_osm() -> list[dict]:
    DATA.mkdir(exist_ok=True)
    if not OVERPASS_CACHE.exists():
        r = requests.post(OVERPASS_URL, data={"data": OVERPASS_QUERY}, headers=UA, timeout=120)
        r.raise_for_status()
        OVERPASS_CACHE.write_text(r.text)
    return json.loads(OVERPASS_CACHE.read_text())["elements"]


def shelter_status(stops: gpd.GeoDataFrame) -> pd.Series:
    """sheltered | none | unknown per stop_id.

    Nearest OSM node within MATCH_M meters. shelter=yes -> sheltered, shelter=no -> none.
    Anything else (no shelter tag, other tag value, no OSM node within 25 m) -> unknown.
    Nothing is guessed: unmatched or untagged stops stay unknown on purpose.
    """
    els = fetch_osm()
    osm = gpd.GeoDataFrame(
        {"osm_id": [e["id"] for e in els], "shelter": [e.get("tags", {}).get("shelter", "") for e in els]},
        geometry=gpd.points_from_xy([e["lon"] for e in els], [e["lat"] for e in els]),
        crs="EPSG:4326",
    ).to_crs(METRIC_CRS)
    s = stops[["stop_id", "geometry"]].to_crs(METRIC_CRS)
    j = gpd.sjoin_nearest(s, osm, how="left", max_distance=MATCH_M, distance_col="dist_m")
    # Ties (two OSM nodes equally near) would duplicate rows; keep the first per stop.
    j = j.drop_duplicates("stop_id")
    status = j["shelter"].map({"yes": "sheltered", "no": "none"}).fillna("unknown")
    status.index = j["stop_id"].values
    matched = j["osm_id"].notna().sum()
    print(f"OSM nodes {len(osm)}; stops matched within {MATCH_M} m: {matched}/{len(j)}")
    print(f"shelter_status counts: {status.value_counts().to_dict()}")
    return status


# --- Census tracts + ACS --------------------------------------------------------------
#
# DECISION: api.census.gov now redirects keyless requests to missing_key.html (checked
# 2026-09-20), and we chose to stay keyless. So ACS numbers come from Census Reporter, a
# third-party mirror that serves the official ACS 5-year tables without a key. Vintage is
# ACS 2024 5-year (2020-2024). Tract geometries are Census TIGER/Line 2024 (official).
# If a Census API key turns up, swap fetch_acs() for api.census.gov; the maths is the same.

ACS_URL = ("https://api.censusreporter.org/1.0/data/show/latest"
           "?table_ids=B08201,B01001&geo_ids=140|05000US12001")  # 140 = tracts in Alachua
ACS_CACHE = DATA / "acs_alachua_tracts.json"
TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_12_tract.zip"
TIGER_ZIP = DATA / "tl_2024_12_tract.zip"

# B01001: sex by age. Age 65+ = male 65-66 (020) through 85+ (025) and female (044-049).
B01001_65_PLUS = [f"B01001{n:03d}" for n in list(range(20, 26)) + list(range(44, 50))]


def fetch_acs() -> dict:
    DATA.mkdir(exist_ok=True)
    if not ACS_CACHE.exists():
        r = requests.get(ACS_URL, headers=UA, timeout=120)
        r.raise_for_status()
        ACS_CACHE.write_text(r.text)
    d = json.loads(ACS_CACHE.read_text())
    print(f"ACS release: {d['release']['name']} ({d['release']['years']})")
    return d


def load_tracts() -> gpd.GeoDataFrame:
    """Alachua County tracts with pct_no_vehicle and pct_65_plus (0 to 100)."""
    if not TIGER_ZIP.exists():
        r = requests.get(TIGER_URL, headers=UA, timeout=300)
        r.raise_for_status()
        assert r.content[:2] == b"PK", "TIGER download was not a zip"
        TIGER_ZIP.write_bytes(r.content)
    tr = gpd.read_file(f"zip://{TIGER_ZIP}")
    tr = tr[tr["COUNTYFP"] == "001"][["GEOID", "geometry"]].rename(columns={"GEOID": "tract_geoid"})

    rows = []
    for geo, tables in fetch_acs()["data"].items():
        hh = tables["B08201"]["estimate"]
        pop = tables["B01001"]["estimate"]
        # Percentages come from raw counts. A zero denominator gives null, not 0.
        no_veh = hh["B08201002"] / hh["B08201001"] * 100 if hh["B08201001"] else None
        p65 = sum(pop[c] for c in B01001_65_PLUS) / pop["B01001001"] * 100 if pop["B01001001"] else None
        rows.append({"tract_geoid": geo.split("US")[-1], "pct_no_vehicle": no_veh, "pct_65_plus": p65})
    acs = pd.DataFrame(rows)
    tr = tr.merge(acs, on="tract_geoid", how="left")
    print(f"tracts: {len(tr)} (TIGER) / {len(acs)} (ACS); "
          f"missing ACS: {tr.pct_no_vehicle.isna().sum()} no_vehicle, {tr.pct_65_plus.isna().sum()} 65+")
    print(f"pct_no_vehicle {tr.pct_no_vehicle.min():.1f}..{tr.pct_no_vehicle.max():.1f}, "
          f"pct_65_plus {tr.pct_65_plus.min():.1f}..{tr.pct_65_plus.max():.1f}")
    return tr


def census_join(stops: gpd.GeoDataFrame) -> pd.DataFrame:
    tr = load_tracts()
    j = gpd.sjoin(stops[["stop_id", "geometry"]].to_crs(tr.crs), tr, how="left", predicate="intersects")
    j = j.drop_duplicates("stop_id")  # a stop exactly on a tract edge would match twice
    print(f"stops with a tract: {j.tract_geoid.notna().sum()}/{len(j)}")
    return j[["stop_id", "tract_geoid", "pct_no_vehicle", "pct_65_plus"]]


# --- stops_context.csv ------------------------------------------------------------------

COLUMNS = ["stop_id", "stop_name", "stop_lat", "stop_lon", "daily_trips", "routes",
           "shelter_status", "tract_geoid", "pct_no_vehicle", "pct_65_plus"]


def build_context() -> pd.DataFrame:
    stops = load_stops()
    trips = build_daily_trips()
    ctx = pd.DataFrame(stops.drop(columns="geometry"))
    ctx = ctx.merge(trips, on="stop_id", how="left")
    # Stops with no trips on the representative day (weekend-only, etc.) keep their row.
    ctx["daily_trips"] = ctx["daily_trips"].fillna(0).astype(int)
    ctx["routes"] = ctx["routes"].fillna("")
    ctx["shelter_status"] = ctx["stop_id"].map(shelter_status(stops))
    ctx = ctx.merge(census_join(stops), on="stop_id", how="left")
    ctx = ctx[COLUMNS]

    geo_rows = len(gpd.read_file(OUT / "stops.geojson"))
    assert len(ctx) == geo_rows, f"row count {len(ctx)} != stops.geojson {geo_rows}"
    assert ctx.stop_id.is_unique and ctx.stop_id.map(type).eq(str).all()
    assert ctx.shelter_status.isin(["sheltered", "none", "unknown"]).all()
    return ctx


if __name__ == "__main__":
    ctx = build_context()
    OUT.mkdir(exist_ok=True)
    ctx.to_csv(OUT / "stops_context.csv", index=False)
    print(f"wrote outputs/stops_context.csv: {len(ctx)} rows")
    print(ctx.describe(include="all").T[["count", "unique", "top", "min", "max"]])

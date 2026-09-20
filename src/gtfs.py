"""Stream B: RTS GTFS download, stops export, daily trips and routes.

Run from repo root: .venv/bin/python src/gtfs.py
"""
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"

# Found via Transitland Atlas (feeds/riderts.app.dmfr.json, feed id f-djm2-regionaltransitsystem).
# Agency in agency.txt: "Regional Transit System" (Gainesville). The old riderts.app and
# go-rts.com/gtfs/google_transit.zip URLs return HTML, so do not use them.
GTFS_URL = "https://go-rts.com/wp-content/uploads/2026/01/RTSGTFS_Spring2026_V6.zip"
GTFS_ZIP = DATA / "rts_gtfs.zip"


def download_gtfs() -> Path:
    """Fetch the GTFS zip once and cache it in data/."""
    DATA.mkdir(exist_ok=True)
    if not GTFS_ZIP.exists():
        r = requests.get(GTFS_URL, timeout=120)
        r.raise_for_status()
        assert r.content[:2] == b"PK", "GTFS download was not a zip"
        GTFS_ZIP.write_bytes(r.content)
    return GTFS_ZIP


def read_table(name: str) -> pd.DataFrame:
    """Read one GTFS txt file. All columns as str so ids never get coerced to int."""
    with zipfile.ZipFile(download_gtfs()) as z:
        with z.open(name) as f:
            return pd.read_csv(f, dtype=str, encoding="utf-8-sig").fillna("")


def load_stops() -> gpd.GeoDataFrame:
    """Raw parse of stops.txt. No cleaning or enrichment (contract: ship it fast)."""
    s = read_table("stops.txt")
    s["stop_lat"] = s["stop_lat"].astype(float)
    s["stop_lon"] = s["stop_lon"].astype(float)
    s["stop_id"] = s["stop_id"].astype(str)
    cols = ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    return gpd.GeoDataFrame(
        s[cols],
        geometry=gpd.points_from_xy(s["stop_lon"], s["stop_lat"]),
        crs="EPSG:4326",
    )


def write_stops_geojson() -> gpd.GeoDataFrame:
    stops = load_stops()
    OUT.mkdir(exist_ok=True)
    stops.to_file(OUT / "stops.geojson", driver="GeoJSON")
    print(f"stops.geojson: {len(stops)} rows, unique ids {stops.stop_id.nunique()}")
    print(f"  lat {stops.stop_lat.min():.4f}..{stops.stop_lat.max():.4f}, "
          f"lon {stops.stop_lon.min():.4f}..{stops.stop_lon.max():.4f}")
    return stops


if __name__ == "__main__":
    write_stops_geojson()

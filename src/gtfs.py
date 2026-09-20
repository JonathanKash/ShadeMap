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


# --- daily trips and routes -------------------------------------------------------------
#
# REPRESENTATIVE DAY (write this in the README limitations, per CLAUDE-B.md):
# Wednesday 2026-02-11. Chosen because the feed is labeled Spring 2026, and 15 of the
# feed's regular Wednesdays look like this one: service ids "Weekday" + "Mon-Thur" are
# active, "Reduced_Service" is switched off by calendar_dates.txt (it only runs on
# breaks). The other common Wednesday is "Weekday" alone (fall pattern, 16 Wednesdays);
# the two differ by only 67 trips (Mon-Thur), so the choice barely moves the counts.
# Active services are computed from calendar.txt + calendar_dates.txt for that date
# rather than hardcoded, so the exception_type 1/2 trap is handled.
# daily_trips = count of stop_times rows (one per bus visit) for trips on that day.
# NOTE: the feed's end date is 2026-05-03, so it is stale relative to the Sept 2026 hack
# day. It is the newest feed RTS publishes as far as we found.
REP_DATE = "20260211"


def active_service_ids(date: str = REP_DATE) -> set[str]:
    cal = read_table("calendar.txt")
    cd = read_table("calendar_dates.txt")
    weekday = pd.Timestamp(date).day_name().lower()
    on = cal[(cal.start_date <= date) & (cal.end_date >= date) & (cal[weekday] == "1")]
    active = set(on.service_id.str.strip())
    for _, r in cd[cd.date == date].iterrows():
        sid = r.service_id.strip()
        if r.exception_type == "1":
            active.add(sid)
        elif r.exception_type == "2":
            active.discard(sid)
    return active


def _route_sort_key(name: str):
    return (0, int(name), "") if name.isdigit() else (1, 0, name)


def build_daily_trips() -> pd.DataFrame:
    """One row per stop that appears in stop_times: stop_id, daily_trips, routes.

    routes = comma separated route_short_name of the routes serving the stop on the
    representative day (same trips as daily_trips, so the two columns agree).
    """
    services = active_service_ids()
    assert services, f"no active services on {REP_DATE}"
    # trips.txt has stray tabs/spaces in many columns (seen in the Spring 2026 feed).
    trips = read_table("trips.txt").apply(lambda c: c.str.strip())
    trips = trips[trips.service_id.isin(services)][["trip_id", "route_id"]]
    routes = read_table("routes.txt").apply(lambda c: c.str.strip())
    trips = trips.merge(routes[["route_id", "route_short_name"]], on="route_id", how="left")
    st = read_table("stop_times.txt")[["trip_id", "stop_id"]]
    st = st.merge(trips, on="trip_id", how="inner")
    print(f"active services on {REP_DATE}: {sorted(services)}; "
          f"{len(trips)} trips, {len(st)} stop_times rows")
    out = st.groupby("stop_id").agg(
        daily_trips=("trip_id", "size"),
        routes=("route_short_name",
                lambda s: ",".join(sorted(set(s.fillna("")) - {""}, key=_route_sort_key))),
    ).reset_index()
    out["stop_id"] = out["stop_id"].astype(str)
    return out


if __name__ == "__main__":
    write_stops_geojson()
    dt = build_daily_trips()
    print(dt.describe(), dt.head())

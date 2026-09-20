"""Street View photos of the top-ranked stops, saved to assets/.

Usage (repo root):  .venv/bin/python src/streetview.py [N]     # default N = 8

Key: env var GOOGLE_MAPS_API_KEY, or a one-line file data/google_api_key.txt (data/ is
gitignored). The key is never written to assets/ or the index. Needs the "Street View
Static API" enabled on the Google Cloud project.

Why top 8, not top 3: some stops have no coverage or only an old panorama, and several
top stops are the same physical place (e.g. Southwest Recreation Center appears at more
than one rank). Fetch extra and let the team pick the best three by eye.

Method: the free metadata endpoint finds the nearest outdoor panorama within RADIUS_M of
the stop. We then point the camera from that panorama toward the stop, so the photo shows
the stop and not just the road. distance_m in the index says how far the panorama is
from the stop; a large value means the stop may be far from the frame.
Google requires attribution: credit the images to Google Street View wherever they are shown.
"""
import math
import os
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
META_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
IMG_URL = "https://maps.googleapis.com/maps/api/streetview"
RADIUS_M = 50


def api_key() -> str:
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    f = ROOT / "data" / "google_api_key.txt"
    if not key and f.exists():
        key = f.read_text().strip()
    if not key:
        sys.exit("No key. Set GOOGLE_MAPS_API_KEY or put it in data/google_api_key.txt")
    return key


def bearing(lat1, lon1, lat2, lon2) -> float:
    """Compass bearing in degrees from point 1 to point 2."""
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot((lat2 - lat1) * 111_000,
                      (lon2 - lon1) * 111_000 * math.cos(math.radians(lat1)))


def main(n: int = 8) -> None:
    key = api_key()
    top = pd.read_csv(ROOT / "outputs" / "top_20_stops.csv", dtype={"stop_id": str}).head(n)
    ctx = pd.read_csv(ROOT / "outputs" / "stops_context.csv", dtype={"stop_id": str})
    top = top.merge(ctx[["stop_id", "stop_lat", "stop_lon"]], on="stop_id")
    ASSETS.mkdir(exist_ok=True)

    rows = []
    for r in top.itertuples():
        meta = requests.get(META_URL, timeout=30, params={
            "location": f"{r.stop_lat},{r.stop_lon}", "radius": RADIUS_M,
            "source": "outdoor", "key": key}).json()
        row = {"rank": r.rank, "stop_id": r.stop_id, "stop_name": r.stop_name,
               "status": meta["status"], "file": "", "pano_date": "", "distance_m": "", "heading": ""}
        if meta["status"] == "OK":
            p = meta["location"]
            h = bearing(p["lat"], p["lng"], r.stop_lat, r.stop_lon)
            img = requests.get(IMG_URL, timeout=60, params={
                "size": "640x400", "pano": meta["pano_id"], "heading": round(h),
                "fov": 90, "pitch": 0, "key": key})
            if img.ok and img.headers.get("content-type", "").startswith("image"):
                name = f"rank{int(r.rank):02d}_stop{r.stop_id}.jpg"
                (ASSETS / name).write_bytes(img.content)
                row.update(file=name, pano_date=meta.get("date", ""), heading=round(h),
                           distance_m=round(dist_m(p["lat"], p["lng"], r.stop_lat, r.stop_lon), 1))
            else:
                row["status"] = f"IMAGE_HTTP_{img.status_code}"
        rows.append(row)
        print(f"rank {r.rank:>2} stop {r.stop_id:>5} {row['status']:<12} {row['file']} "
              f"{row['pano_date']} {row['distance_m']} m  {r.stop_name}")

    pd.DataFrame(rows).to_csv(ASSETS / "streetview_index.csv", index=False)
    print(f"saved {sum(bool(x['file']) for x in rows)}/{len(rows)} images + assets/streetview_index.csv")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)

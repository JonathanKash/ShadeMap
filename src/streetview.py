"""Street-level photos of the top-ranked stops from Mapillary, saved to assets/.

Usage (repo root):  .venv/bin/python src/streetview.py [N]     # default N = 8

Free: no card. Needs a Mapillary client token in env var MAPILLARY_TOKEN, or a one-line
file data/mapillary_token.txt (data/ is gitignored). The token is sent as a header and is
never written to assets/ or the index.

Why top 8, not top 3: some stops have no photo nearby, and several top stops are the same
physical place (Southwest Recreation Center appears at more than one rank). Fetch extra
and let the team pick the best three by eye.

Method: search Mapillary images in a small box around the stop, then prefer photos whose
camera heading points toward the stop, then the closest, then the newest. distance_m and
facing_diff_deg in the index say how good the match is; a large value means the stop may not
be in frame, so look at the image before using it.

LICENSE: Mapillary images are CC BY-SA 4.0. Wherever a photo is shown, credit it as
"Photo: <creator> via Mapillary (CC BY-SA 4.0)". The index has a creator column.
(Swapped in for a Google Street View version: Google needs a billing card, Mapillary does not.)
"""
import math
import os
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
API = "https://graph.mapillary.com/images"
BOX_DEG = 0.0006          # about 65 m each way
FACING_OK_DEG = 60        # camera heading within this of the bearing to the stop counts as facing it
FIELDS = "id,captured_at,compass_angle,geometry,thumb_1024_url,is_pano,creator"


def token() -> str:
    t = os.environ.get("MAPILLARY_TOKEN", "").strip()
    f = ROOT / "data" / "mapillary_token.txt"
    if not t and f.exists():
        t = f.read_text().strip()
    if not t:
        sys.exit("No token. Set MAPILLARY_TOKEN or put it in data/mapillary_token.txt")
    return t


def bearing(lat1, lon1, lat2, lon2) -> float:
    """Compass bearing in degrees from point 1 to point 2."""
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot((lat2 - lat1) * 111_000,
                      (lon2 - lon1) * 111_000 * math.cos(math.radians(lat1)))


def angle_diff(a: float, b: float) -> float:
    """Smallest angle between two compass headings, 0 to 180."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


def best_image(images: list[dict], lat: float, lon: float) -> dict | None:
    """Pick the image most likely to show the stop. Flat photos beat 360 panoramas."""
    scored = []
    for im in images:
        if not im.get("thumb_1024_url"):
            continue
        ilon, ilat = im["geometry"]["coordinates"]
        d = dist_m(ilat, ilon, lat, lon)
        diff = angle_diff(im.get("compass_angle", 0), bearing(ilat, ilon, lat, lon))
        facing = bool(im.get("is_pano")) or diff <= FACING_OK_DEG  # a pano can look any way
        scored.append(((not facing, bool(im.get("is_pano")), round(d / 10), -im["captured_at"]),
                       {**im, "distance_m": round(d, 1), "facing_diff_deg": round(diff)}))
    return min(scored, key=lambda s: s[0])[1] if scored else None


def main(n: int = 8) -> None:
    headers = {"Authorization": f"OAuth {token()}"}
    top = pd.read_csv(ROOT / "outputs" / "top_20_stops.csv", dtype={"stop_id": str}).head(n)
    ctx = pd.read_csv(ROOT / "outputs" / "stops_context.csv", dtype={"stop_id": str})
    top = top.merge(ctx[["stop_id", "stop_lat", "stop_lon"]], on="stop_id")
    ASSETS.mkdir(exist_ok=True)

    rows = []
    for r in top.itertuples():
        bbox = f"{r.stop_lon - BOX_DEG},{r.stop_lat - BOX_DEG},{r.stop_lon + BOX_DEG},{r.stop_lat + BOX_DEG}"
        resp = requests.get(API, headers=headers, timeout=60,
                            params={"bbox": bbox, "fields": FIELDS, "limit": 200})
        resp.raise_for_status()
        images = resp.json().get("data", [])
        pick = best_image(images, r.stop_lat, r.stop_lon)
        row = {"rank": r.rank, "stop_id": r.stop_id, "stop_name": r.stop_name,
               "candidates": len(images), "file": "", "captured": "", "creator": "",
               "distance_m": "", "facing_diff_deg": "", "is_pano": ""}
        if pick:
            img = requests.get(pick["thumb_1024_url"], timeout=60)
            if img.ok:
                name = f"rank{int(r.rank):02d}_stop{r.stop_id}.jpg"
                (ASSETS / name).write_bytes(img.content)
                row.update(file=name, captured=pd.to_datetime(pick["captured_at"], unit="ms").date(),
                           creator=pick.get("creator", {}).get("username", ""),
                           distance_m=pick["distance_m"], facing_diff_deg=pick["facing_diff_deg"],
                           is_pano=bool(pick.get("is_pano")))
        rows.append(row)
        print(f"rank {r.rank:>2} stop {r.stop_id:>5} candidates {row['candidates']:>3} "
              f"{row['file'] or 'NO PHOTO':<24} {row['captured']} {row['distance_m']} m  {r.stop_name}")

    pd.DataFrame(rows).to_csv(ASSETS / "streetview_index.csv", index=False)
    print(f"saved {sum(bool(x['file']) for x in rows)}/{len(rows)} images + assets/streetview_index.csv")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)

"""Validate and shrink admin-uploaded stop photos, and list which stops still need one.

Usage (repo root):
    .venv/bin/python src/photos.py            # check photos, write outputs/stop_photos.csv
    .venv/bin/python src/photos.py --resize   # also shrink big photos and strip metadata

Photos live in docs/photos/ (GitHub Pages only serves docs/). Name each file after its
stop id: 807.jpg, 966.png, 1254.webp. See ADMIN_PHOTOS.md for the upload steps.

--resize does two things to every photo, in place:
  * scales it to at most 1280 px on the long side (phone photos are 3 to 8 MB, the map
    should load on a phone over cell data)
  * re-saves it WITHOUT EXIF, which removes the GPS position and time the phone recorded
Orientation is applied first, so portrait photos do not end up sideways.

Writes outputs/stop_photos.csv (stop_id, file, stop_name, rank). The map reads this file to
know which popups get a photo, so it never links to a missing image. With no photos the
file is just the header, which is the correct empty state.
"""
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = ROOT / "docs" / "photos"
OUT = ROOT / "outputs" / "stop_photos.csv"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIDE = 1280
WARN_BYTES = 1_500_000
COLUMNS = ["stop_id", "file", "stop_name", "rank"]


def shrink(path: Path) -> None:
    """Apply orientation, cap the long side, and re-save without EXIF.

    Idempotent: a photo that is already small and has no EXIF is left untouched, so
    re-running (or the GitHub Action re-running) never re-encodes it or changes its bytes.
    """
    with Image.open(path) as im:
        if max(im.size) <= MAX_SIDE and not im.getexif() and path.stat().st_size <= WARN_BYTES:
            return
        im = ImageOps.exif_transpose(im)
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            im.convert("RGB").save(path, "JPEG", quality=82, optimize=True)
        else:
            im.save(path)  # PNG and WebP are saved without the source EXIF block


def main(resize: bool = False, photo_dir: Path = PHOTO_DIR, out: Path = OUT) -> pd.DataFrame:
    ctx = pd.read_csv(ROOT / "outputs" / "stops_context.csv", dtype={"stop_id": str})
    names = dict(zip(ctx.stop_id, ctx.stop_name))
    scored = pd.read_csv(ROOT / "outputs" / "scored_stops.csv", dtype={"stop_id": str})
    ranks = dict(zip(scored.stop_id, scored["rank"]))

    files = sorted(p for p in photo_dir.glob("*") if p.suffix.lower() in EXTS) if photo_dir.exists() else []
    if not photo_dir.exists():
        print(f"{photo_dir} does not exist yet, so there are no photos. Writing an empty manifest.")

    rows, problems = [], []
    for p in files:
        if p.stem not in names:
            problems.append(f"{p.name}: '{p.stem}' is not a stop_id in stops_context.csv, skipped")
            continue
        try:
            if resize:
                shrink(p)
            with Image.open(p) as im:
                im.verify()
        except Exception as e:  # a corrupt or non-image file with an image extension
            problems.append(f"{p.name}: cannot read as an image ({e}), skipped")
            continue
        if p.stat().st_size > WARN_BYTES:
            problems.append(f"{p.name}: {p.stat().st_size / 1e6:.1f} MB, run with --resize")
        r = ranks.get(p.stem)
        rows.append({"stop_id": p.stem, "file": p.name, "stop_name": names[p.stem],
                     "rank": int(r) if pd.notna(r) else ""})

    # One photo per stop: two files for the same stop id would be ambiguous.
    df = pd.DataFrame(rows, columns=COLUMNS)
    dupes = df[df.duplicated("stop_id", keep=False)]
    if len(dupes):
        problems.append(f"more than one photo for stop(s) {sorted(dupes.stop_id.unique())}; keeping the first")
        df = df.drop_duplicates("stop_id")
    df = df.sort_values("rank", key=pd.to_numeric, na_position="last")

    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)

    top20 = scored[scored["rank"].notna() & (scored["rank"] <= 20)].sort_values("rank")
    missing = top20[~top20.stop_id.isin(df.stop_id)]
    print(f"{len(df)} photo(s) accepted, written to {out}")
    for m in problems:
        print("  PROBLEM:", m)
    print(f"Top 20 stops still without a photo: {len(missing)} of 20")
    for m in missing.head(10).itertuples():
        print(f"  rank {int(m.rank):>2}  {m.stop_id}  {m.stop_name}")
    return df


if __name__ == "__main__":
    main(resize="--resize" in sys.argv)

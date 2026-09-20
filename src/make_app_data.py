"""Bake docs/app_data.json for the app-style map page (docs/app.html).

Joins the committed handoff CSVs into one compact JSON the page loads once.
Stream A file: new outputs only, nothing of B's or C's is modified.

Run: .venv/Scripts/python src/make_app_data.py
"""

import json
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parent.parent

scored = pd.read_csv(root / "outputs" / "scored_stops.csv",
                     dtype={"stop_id": str, "tract_geoid": str})
need = pd.read_csv(root / "outputs" / "shade_need.csv", dtype={"stop_id": str})
canopy = pd.read_csv(root / "outputs" / "stop_canopy.csv", dtype={"stop_id": str})
near = pd.read_csv(root / "outputs" / "nearest_shelter.csv", dtype={
    "stop_id": str, "nearest_sheltered_stop_id": str})

df = (scored
      .merge(need[["stop_id", "shade_need_rank"]], on="stop_id", how="left")
      .merge(canopy[["stop_id", "pct_green"]], on="stop_id", how="left"))

flagged = near[near.no_shelter_within_5min]
flags = {}
for _, r in flagged.iterrows():
    flags.setdefault(r.stop_id, []).append([
        r.route,
        None if pd.isna(r.walk_min) else round(float(r.walk_min), 1),
        None if pd.isna(r.nearest_sheltered_stop_name) else r.nearest_sheltered_stop_name,
    ])

n_ranked = int(df["rank"].notna().sum())
stops = []
for _, s in df.iterrows():
    stops.append({
        "id": s.stop_id,
        "name": s.stop_name,
        "lat": round(float(s.stop_lat), 6),
        "lon": round(float(s.stop_lon), 6),
        "routes": [] if pd.isna(s.routes) else [x.strip() for x in str(s.routes).split(",")],
        "trips": 0 if pd.isna(s.daily_trips) else int(s.daily_trips),
        "lst_f": None if pd.isna(s.mean_lst_f) else round(float(s.mean_lst_f), 1),
        "green": None if pd.isna(s.pct_green) else round(float(s.pct_green)),
        "no_veh": None if pd.isna(s.pct_no_vehicle) else round(float(s.pct_no_vehicle), 1),
        "shelter": s.shelter_status,
        "rank": None if pd.isna(s["rank"]) else int(s["rank"]),
        "need_rank": None if pd.isna(s.shade_need_rank) else int(s.shade_need_rank),
        "excluded": None if pd.isna(s.excluded_reason) else s.excluded_reason,
        "flags": flags.get(s.stop_id, []),
    })

out = {"n_ranked": n_ranked, "stops": stops}
path = root / "docs" / "app_data.json"
path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(f"wrote {path}: {len(stops)} stops, {n_ranked} ranked, "
      f"{sum(1 for s in stops if s['need_rank'] and s['need_rank'] <= 20)} shade-need top 20, "
      f"{path.stat().st_size // 1024} KB")

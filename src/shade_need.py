"""Shade-need identifier: the stops that most lack shade, not the busiest.

C's score answers "where does a shelter help the most riders" and trip volume
dominates it. This answers "where is the wait itself worst": among stops with
real service (>= 10 bus visits per weekday) and no shelter per OSM,

    shade_need = lst_percentile * (1 - pct_green / 100) * transit_dependence

Heat, absence of natural shade, and neighborhood transit dependence. Service
is an entry threshold, not a multiplier, so ridership volume cannot swamp
exposure. Writes outputs/shade_need.csv for all qualifying stops with
`shade_need_rank` and a `top20_shade_need` flag for the map.

Stream A file. Reads handoff outputs only, changes nothing of B's or C's.
"""

from pathlib import Path

import pandas as pd

MIN_TRIPS = 10  # roughly one bus an hour on a weekday

root = Path(__file__).resolve().parent.parent
ctx = pd.read_csv(root / "outputs" / "stops_context.csv",
                  dtype={"stop_id": str, "tract_geoid": str})
lst = pd.read_csv(root / "outputs" / "stop_lst.csv", dtype={"stop_id": str})
canopy = pd.read_csv(root / "outputs" / "stop_canopy.csv", dtype={"stop_id": str})

df = (ctx.merge(lst[["stop_id", "mean_lst_c", "pixel_count"]], on="stop_id")
         .merge(canopy[["stop_id", "pct_green"]], on="stop_id"))
print(f"joined: {df.shape}")

# same eligibility logic as the main ranking: measured temperature only
eligible = df[(df.pixel_count > 0) & (df.daily_trips >= MIN_TRIPS)
              & (df.shelter_status == "none")].copy()
print(f"eligible (measured LST, >= {MIN_TRIPS} trips, OSM says no shelter): "
      f"{len(eligible)}")

eligible["lst_percentile"] = eligible.mean_lst_c.rank(pct=True)
# same 0.5 to 1.5 scaling C uses for transit dependence
nv = eligible.pct_no_vehicle
eligible["transit_dependence"] = 0.5 + (nv - nv.min()) / (nv.max() - nv.min())
eligible["shade_need"] = (eligible.lst_percentile
                          * (1.0 - eligible.pct_green / 100.0)
                          * eligible.transit_dependence).round(4)

eligible = eligible.sort_values("shade_need", ascending=False)
eligible["shade_need_rank"] = range(1, len(eligible) + 1)
eligible["top20_shade_need"] = eligible.shade_need_rank <= 20

cols = ["stop_id", "stop_name", "stop_lat", "stop_lon", "routes", "daily_trips",
        "mean_lst_c", "pct_green", "pct_no_vehicle", "shelter_status",
        "lst_percentile", "transit_dependence", "shade_need",
        "shade_need_rank", "top20_shade_need"]
out = eligible[cols]
out.to_csv(root / "outputs" / "shade_need.csv", index=False)
print(f"wrote outputs/shade_need.csv ({len(out)} rows)")

top = out.head(20)
print("\nTop 20 stops that most need shade:")
print(top[["shade_need_rank", "stop_name", "routes", "daily_trips",
           "mean_lst_c", "pct_green", "pct_no_vehicle"]].to_string(index=False))

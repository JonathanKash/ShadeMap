"""Shade-need identifier: the stops that most lack shade, not the busiest.

C's score answers "where does a shelter help the most riders" and trip volume
dominates it. This answers "where is the wait itself worst," built for social
benefit:

    shade_need = lst_percentile * (1 - pct_green / 100)
                 * shelter_factor * social_vulnerability

- Eligibility is any weekday service, not a frequency bar. Sparse service
  means longer waits in the sun, not less need, and a frequency bar would
  exclude exactly the neighborhoods transit serves worst.
- Unknown shelter status is included (factor 1.25 vs 1.5 for confirmed none,
  C's own convention). OSM mapping is densest around campus and wealthier
  areas, so excluding unmapped stops would bias against under-mapped
  neighborhoods.
- social_vulnerability blends car-free households and residents 65 and
  older, the population heat harms most. Both from B's census columns.

Writes outputs/shade_need.csv with `shade_need_rank` and `top20_shade_need`.
Stream A file. Reads handoff outputs only, changes nothing of B's or C's.
"""

from pathlib import Path

import pandas as pd

MIN_TRIPS = 1  # any weekday service; frequency is not need
SHELTER_FACTOR = {"none": 1.5, "unknown": 1.25}

root = Path(__file__).resolve().parent.parent
ctx = pd.read_csv(root / "outputs" / "stops_context.csv",
                  dtype={"stop_id": str, "tract_geoid": str})
lst = pd.read_csv(root / "outputs" / "stop_lst.csv", dtype={"stop_id": str})
canopy = pd.read_csv(root / "outputs" / "stop_canopy.csv", dtype={"stop_id": str})

df = (ctx.merge(lst[["stop_id", "mean_lst_c", "pixel_count"]], on="stop_id")
         .merge(canopy[["stop_id", "pct_green"]], on="stop_id"))
print(f"joined: {df.shape}")

# measured temperature only, any service, not confirmed sheltered
eligible = df[(df.pixel_count > 0) & (df.daily_trips >= MIN_TRIPS)
              & (df.shelter_status.isin(SHELTER_FACTOR))].copy()
print(f"eligible (measured LST, any weekday service, not confirmed "
      f"sheltered): {len(eligible)}")

eligible["lst_percentile"] = eligible.mean_lst_c.rank(pct=True)
eligible["shelter_factor"] = eligible.shelter_status.map(SHELTER_FACTOR)


def scale_05_15(s):
    """C's 0.5 to 1.5 min-max convention."""
    return 0.5 + (s - s.min()) / (s.max() - s.min())


# car-free households and seniors, equally weighted, then scaled 0.5 to 1.5
vuln_raw = (scale_05_15(eligible.pct_no_vehicle)
            + scale_05_15(eligible.pct_65_plus)) / 2.0
eligible["social_vulnerability"] = scale_05_15(vuln_raw)
eligible["shade_need"] = (eligible.lst_percentile
                          * (1.0 - eligible.pct_green / 100.0)
                          * eligible.shelter_factor
                          * eligible.social_vulnerability).round(4)

eligible = eligible.sort_values("shade_need", ascending=False)
eligible["shade_need_rank"] = range(1, len(eligible) + 1)
eligible["top20_shade_need"] = eligible.shade_need_rank <= 20

cols = ["stop_id", "stop_name", "stop_lat", "stop_lon", "routes", "daily_trips",
        "mean_lst_c", "pct_green", "pct_no_vehicle", "pct_65_plus",
        "shelter_status", "lst_percentile", "shelter_factor",
        "social_vulnerability", "shade_need", "shade_need_rank",
        "top20_shade_need"]
out = eligible[cols]
out.to_csv(root / "outputs" / "shade_need.csv", index=False)
print(f"wrote outputs/shade_need.csv ({len(out)} rows)")

top = out.head(20)
print("\nTop 20 stops that most need shade:")
print(top[["shade_need_rank", "stop_name", "routes", "daily_trips",
           "mean_lst_c", "pct_green", "shelter_status", "pct_no_vehicle",
           "pct_65_plus"]].to_string(index=False))

"""Stream C: join LST and context, score every stop, write the ranked CSVs.

score = lst_percentile * log1p(daily_trips) * shelter_multiplier * transit_dependence

Run from the repo root: python src/score.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

SHELTER_MULTIPLIER = {"none": 1.5, "unknown": 1.25, "sheltered": 1.0}

TOP_20_COLUMNS = [
    "rank", "stop_id", "stop_name", "routes", "daily_trips", "mean_lst_c", "mean_lst_f",
    "shelter_status", "pct_no_vehicle", "pct_65_plus", "lst_percentile",
    "shelter_multiplier", "transit_dependence", "score",
]


def load(lst_path=None, context_path=None):
    lst_path = lst_path or OUT / "stop_lst.csv"
    context_path = context_path or OUT / "stops_context.csv"
    lst = pd.read_csv(lst_path, dtype={"stop_id": str})
    ctx = pd.read_csv(context_path, dtype={"stop_id": str, "tract_geoid": str})
    df = ctx.merge(lst, on="stop_id", how="left", validate="one_to_one")
    print(f"joined: {df.shape[0]} stops, {lst['stop_id'].nunique()} in lst, "
          f"{ctx['stop_id'].nunique()} in context")
    return df


def score(df):
    df = df.copy()

    df["excluded_reason"] = None
    no_lst = df["pixel_count"].fillna(0).eq(0) | df["mean_lst_c"].isna()
    no_service = df["daily_trips"].fillna(0).eq(0)
    df.loc[no_service, "excluded_reason"] = "no service on representative weekday"
    df.loc[no_lst, "excluded_reason"] = "no satellite data in 100 m buffer"
    ranked = df["excluded_reason"].isna()

    df["mean_lst_f"] = df["mean_lst_c"] * 9 / 5 + 32

    # percentile rank of mean LST among stops that can be ranked, 0 to 1
    df["lst_percentile"] = np.nan
    df.loc[ranked, "lst_percentile"] = df.loc[ranked, "mean_lst_c"].rank(pct=True)

    df["shelter_multiplier"] = df["shelter_status"].map(SHELTER_MULTIPLIER).fillna(1.25)

    # min-max of pct_no_vehicle into 0.5 to 1.5, null census means neutral 1.0
    pv = df["pct_no_vehicle"]
    lo, hi = pv.min(), pv.max()
    df["transit_dependence"] = 0.5 + (pv - lo) / (hi - lo)
    df["transit_dependence"] = df["transit_dependence"].fillna(1.0)

    df["score"] = np.nan
    df.loc[ranked, "score"] = (
        df.loc[ranked, "lst_percentile"]
        * np.log1p(df.loc[ranked, "daily_trips"])
        * df.loc[ranked, "shelter_multiplier"]
        * df.loc[ranked, "transit_dependence"]
    )

    df["rank"] = df["score"].rank(ascending=False, method="first").astype("Int64")
    return df.sort_values(["rank", "stop_id"], na_position="last").reset_index(drop=True)


def write(df):
    df.to_csv(OUT / "scored_stops.csv", index=False)
    top = df[df["rank"].notna() & (df["rank"] <= 20)][TOP_20_COLUMNS].copy()
    for col in ["mean_lst_c", "mean_lst_f", "pct_no_vehicle", "pct_65_plus"]:
        top[col] = top[col].round(1)
    for col in ["lst_percentile", "transit_dependence", "score"]:
        top[col] = top[col].round(3)
    top.to_csv(OUT / "top_20_stops.csv", index=False)
    return top


def main():
    df = score(load())
    top = write(df)
    ranked = df["rank"].notna().sum()
    print(f"ranked {ranked}, excluded {len(df) - ranked}")
    print(df["excluded_reason"].value_counts().to_string())
    print(f"score range {df['score'].min():.3f} to {df['score'].max():.3f}")
    print(f"transit_dependence range {df['transit_dependence'].min():.2f} "
          f"to {df['transit_dependence'].max():.2f}")
    print(top[["rank", "stop_name", "daily_trips", "mean_lst_c", "shelter_status", "score"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()

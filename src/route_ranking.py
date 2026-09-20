"""Rank RTS routes by the average shade-priority score of the stops they serve.

Run from repo root after score.py:  .venv/bin/python src/route_ranking.py
Reads outputs/scored_stops.csv, writes outputs/route_ranking.csv.

One-sentence definition (for the README): a route ranks higher when its stops are, on
average, hotter, busier, less likely to have a shelter, and in tracts with more car-free
households.

Choices:
* Average, not total. A total would just reward long routes.
* Only ranked stops count (stops with no satellite data or no weekday service are excluded,
  same as the stop ranking).
* A stop's daily_trips counts every route at that stop, so routes through busy hubs (Reitz
  Union, The Hub) get a boost. Visits cannot be split per route without changing the trip
  counts, so say this in the README.
* pct_unsheltered is "OSM says no shelter" over the route's ranked stops. pct_unknown is
  shown next to it because unknown stops are not counted as unsheltered.
"""
import pandas as pd

from gtfs import ROOT, read_table

TOP_N = 50  # "stops in the citywide top 50" column


def build() -> pd.DataFrame:
    stops = pd.read_csv(ROOT / "outputs" / "scored_stops.csv", dtype={"stop_id": str})
    ranked = stops[stops["rank"].notna()].copy()
    ranked["route"] = ranked["routes"].str.split(",")
    e = ranked.explode("route")
    e["route"] = e["route"].str.strip()
    e = e[e["route"].notna() & (e["route"] != "")]

    g = e.groupby("route").agg(
        ranked_stops=("stop_id", "nunique"),
        avg_score=("score", "mean"),
        stops_in_top50=("rank", lambda s: int((s <= TOP_N).sum())),
        pct_unsheltered=("shelter_status", lambda s: 100 * (s == "none").mean()),
        pct_unknown=("shelter_status", lambda s: 100 * (s == "unknown").mean()),
        avg_lst_c=("mean_lst_c", "mean"),
    ).reset_index()

    names = (read_table("routes.txt").apply(lambda c: c.str.strip())
             .drop_duplicates("route_short_name")
             .set_index("route_short_name")["route_long_name"])
    g["route_name"] = g["route"].map(names).fillna("")

    # Highest average score first; ties broken by how many top-50 stops the route serves.
    g = g.sort_values(["avg_score", "stops_in_top50"], ascending=False).reset_index(drop=True)
    g.insert(0, "route_rank", g.index + 1)
    g = g[["route_rank", "route", "route_name", "ranked_stops", "avg_score",
           "stops_in_top50", "pct_unsheltered", "pct_unknown", "avg_lst_c"]]
    return g.round({"avg_score": 2, "pct_unsheltered": 0, "pct_unknown": 0, "avg_lst_c": 1})


if __name__ == "__main__":
    out = build()
    assert out.route.is_unique and (out.route_name != "").all(), "route without a name or duplicate route"
    out.to_csv(ROOT / "outputs" / "route_ranking.csv", index=False)
    print(f"wrote outputs/route_ranking.csv: {len(out)} routes")
    print(out.head(10).to_string(index=False))

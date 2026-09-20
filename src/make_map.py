"""Stream C: build docs/index.html (static Folium map) from outputs/scored_stops.csv.

Run from the repo root after score.py: python src/make_map.py
"""
from html import escape
from pathlib import Path
from urllib.parse import quote

import folium
import pandas as pd
from folium import DivIcon

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

CENTER = (29.6516, -82.3248)  # Gainesville

# stops that have a photo in docs/photos/, from outputs/stop_photos.csv (header only until
# the first upload, which is fine). Reading the list means popups never link a missing file.
_manifest = ROOT / "outputs" / "stop_photos.csv"
PHOTO_FILE = {}
if _manifest.exists():
    _photos = pd.read_csv(_manifest, dtype={"stop_id": str, "file": str})
    PHOTO_FILE = {sid: f for sid, f in zip(_photos["stop_id"], _photos["file"])
                  if (DOCS / "photos" / f).exists()}
# sequential ramp, light to dark, one color per fifth of ranked stops
RAMP = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
RAMP_LABELS = [
    "Lowest 20 percent of stops",
    "Lower middle",
    "Middle",
    "Upper middle",
    "Highest 20 percent of stops",
]
NO_DATA = "#9aa0a6"

TITLE = (
    "Which Gainesville bus stops need shade most? Stops are ranked by summer heat, "
    "bus service, shelter, and how many nearby households have no car."
)

SHELTER_TEXT = {
    "sheltered": "Sheltered (per OpenStreetMap)",
    "none": "No shelter (per OpenStreetMap)",
    "unknown": "Shelter status unknown",
}

CSS = """
<style>
  #title-bar {
    position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
    z-index: 9999; box-sizing: border-box; width: min(720px, calc(100vw - 120px));
    background: rgba(255,255,255,0.96); border-radius: 8px; padding: 8px 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.3); font: 14px/1.35 system-ui, sans-serif;
    color: #1f2933; text-align: center;
  }
  #title-bar b { font-size: 16px; display: block; margin-bottom: 2px; }
  #legend {
    position: fixed; bottom: 22px; left: 10px; z-index: 9999; max-width: 250px;
    background: rgba(255,255,255,0.96); border-radius: 8px; padding: 8px 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.3); font: 13px/1.35 system-ui, sans-serif;
    color: #1f2933;
  }
  #legend .head { font-weight: 600; margin-bottom: 4px; }
  #legend .row { display: flex; align-items: center; margin: 2px 0; }
  #legend .sw {
    width: 14px; height: 14px; border-radius: 50%; margin-right: 8px;
    border: 1px solid rgba(0,0,0,0.35); flex: none;
  }
  #legend .note { margin-top: 6px; font-size: 12px; color: #52606d; }
  .rank-pin {
    box-sizing: border-box; width: 22px; height: 22px; border-radius: 50%;
    background: #111827; color: #fff;
    border: 2px solid #fff; box-shadow: 0 0 4px rgba(0,0,0,0.6);
    font: 700 11px/18px system-ui, sans-serif; text-align: center;
  }
  .popup { font: 13px/1.4 system-ui, sans-serif; min-width: 200px; }
  .popup .name { font-weight: 600; font-size: 14px; }
  .popup .rank { color: #bd0026; font-weight: 700; }
  @media (max-width: 600px) {
    #title-bar { font-size: 12px; padding: 6px 8px; left: 56px; transform: none;
                 width: calc(100vw - 66px); }
    #title-bar b { font-size: 14px; }
    #legend { font-size: 11px; max-width: 190px; bottom: 16px; padding: 6px 8px; }
  }
</style>
"""


REPO = "https://github.com/JonathanKash/ShadeMap"


def action_html(r):
    """What a resident can do from the popup (added by Stream B for community impact).

    1. Ask for a shelter: only at stops not known to be sheltered. Channels are the City of
       Gainesville request portal (myGNV, mygnv.org redirects to the city's portal) and the
       RTS phone number from the agency line of RTS's own GTFS feed. No promise is made
       about what the city will do.
    2. Report wrong shelter info: opens a prefilled GitHub issue for this stop. A maintainer
       who verifies it adds a sourced row to outputs/shelter_overrides.csv (see ADMIN_PHOTOS.md).
    """
    stop_id, name = str(r["stop_id"]), str(r["stop_name"])
    status = str(r["shelter_status"])
    body = (f"Stop: {name} (stop_id {stop_id})\nOur map says: {status}\n\n"
            "What is actually at this stop (shelter, no shelter, not sure):\n\n"
            "How do you know (date you visited, or attach a photo):\n")
    issue = (f"{REPO}/issues/new?title={quote(f'Shelter info: stop {stop_id} {name}', safe='')}"
             f"&body={quote(body, safe='')}")
    ask = ""
    if status != "sheltered":
        ask = ('<div style="margin-top:6px"><b>Want a shelter here?</b> Ask the city: '
               '<a href="https://mygnv.org" target="_blank" rel="noopener">myGNV</a> '
               'or call RTS at (352) 334-2600.</div>')
    fix = (f'<div style="margin-top:4px;font-size:12px"><a href="{escape(issue)}" '
           f'target="_blank" rel="noopener">Shelter info wrong? Tell us</a></div>')
    return ask + fix


def popup_html(r, ranked):
    name = escape(str(r["stop_name"]))
    routes = escape(str(r["routes"])) if pd.notna(r["routes"]) else "none that day"
    # vegetation is shown for context only, it is not part of the score
    green = ("Green cover within 100 m: no data" if pd.isna(r["pct_green"])
             else f'Green cover within 100 m: {r["pct_green"]:.0f} percent '
                  f'(satellite vegetation, not measured shade)')
    if ranked:
        head = (f'<div class="name">{name}</div>'
                f'<div class="rank">Rank {int(r["rank"])} of {N_RANKED}</div>')
        heat = f'{r["mean_lst_c"]:.1f} C / {r["mean_lst_f"]:.1f} F'
    else:
        head = (f'<div class="name">{name}</div>'
                f'<div>Not ranked: {escape(str(r["excluded_reason"]))}</div>')
        heat = ("no data" if pd.isna(r["mean_lst_c"])
                else f'{r["mean_lst_c"]:.1f} C / {r["mean_lst_f"]:.1f} F')
    img = PHOTO_FILE.get(str(r["stop_id"]))
    photo = (f'<img src="photos/{escape(img)}" alt="Photo of {name}" loading="lazy" '
             f'style="width:100%;margin-top:6px;border-radius:4px">'
             f'<div style="font-size:11px;color:#52606d">Photo: ShadeMap team</div>'
             if img else "")
    return (
        f'<div class="popup">{head}'
        f'<div>Routes: {routes}</div>'
        f'<div>Bus visits per weekday: {int(r["daily_trips"])}</div>'
        f'<div>Summer morning heat nearby: {heat}</div>'
        f'<div>{SHELTER_TEXT.get(r["shelter_status"], "Shelter status unknown")}</div>'
        f'<div>{green}</div>'
        f'{photo}'
        f'{action_html(r)}'
        f'</div>'
    )


def legend_html(n_ranked, n_missing):
    rows = "".join(
        f'<div class="row"><span class="sw" style="background:{c}"></span>{lab}</div>'
        for c, lab in reversed(list(zip(RAMP, RAMP_LABELS)))
    )
    return (
        '<div id="legend">'
        '<div class="head">Priority for shade</div>'
        f'{rows}'
        '<div class="row"><span class="rank-pin" style="width:18px;height:18px;'
        'font-size:10px;line-height:14px;margin-right:8px;flex:none">1</span>'
        'Top 20 stops, numbered</div>'
        f'<div class="row"><span class="sw" style="background:{NO_DATA}"></span>'
        f'Not ranked ({n_missing}: no satellite data or no service)</div>'
        '<div class="note">Bigger dots mean a higher score. Tap a stop for details. '
        f'{n_ranked} stops ranked.</div>'
        '</div>'
    )


def build(df):
    global N_RANKED
    ranked = df[df["rank"].notna()].copy()
    unranked = df[df["rank"].isna()]
    N_RANKED = len(ranked)

    # color class from score quintile, radius from score
    ranked["cls"] = pd.qcut(ranked["score"].rank(method="first"), 5, labels=False)
    smin, smax = ranked["score"].min(), ranked["score"].max()
    ranked["radius"] = 3.5 + 6.5 * (ranked["score"] - smin) / (smax - smin)

    # Esri light gray canvas: keyless, muted so the color ramp reads clearly
    m = folium.Map(location=CENTER, zoom_start=12, tiles=None,
                   control_scale=True, zoom_control=True, max_zoom=16)
    esri = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
    folium.TileLayer(esri.format("World_Light_Gray_Base"), name="Base", max_zoom=16,
                     attr="Tiles &copy; Esri", control=False).add_to(m)
    folium.TileLayer(esri.format("World_Light_Gray_Reference"), name="Labels", max_zoom=16,
                     attr="Tiles &copy; Esri", control=False, pane="shadowPane").add_to(m)

    for _, r in unranked.iterrows():
        folium.CircleMarker(
            (r["stop_lat"], r["stop_lon"]), radius=3, color=NO_DATA, weight=1,
            fill=True, fill_color=NO_DATA, fill_opacity=0.6,
            popup=folium.Popup(popup_html(r, False), max_width=280),
        ).add_to(m)

    # low scores first so the high ones draw on top
    for _, r in ranked.sort_values("score").iterrows():
        folium.CircleMarker(
            (r["stop_lat"], r["stop_lon"]), radius=float(r["radius"]),
            color="#333333", weight=0.6, fill=True,
            fill_color=RAMP[int(r["cls"])], fill_opacity=0.85,
            popup=folium.Popup(popup_html(r, True), max_width=280),
        ).add_to(m)

    for _, r in ranked[ranked["rank"] <= 20].iterrows():
        folium.Marker(
            (r["stop_lat"], r["stop_lon"]),
            icon=DivIcon(icon_size=(22, 22), icon_anchor=(11, 11),
                         html=f'<div class="rank-pin">{int(r["rank"])}</div>'),
            popup=folium.Popup(popup_html(r, True), max_width=280),
            z_index_offset=1000,
        ).add_to(m)

    root = m.get_root()
    root.header.add_child(folium.Element(CSS))
    root.header.add_child(folium.Element("<title>ShadeMap: Gainesville bus stop heat ranking</title>"))
    root.html.add_child(folium.Element(
        f'<div id="title-bar"><b>ShadeMap Gainesville</b>{TITLE}</div>'))
    root.html.add_child(folium.Element(legend_html(N_RANKED, len(unranked))))
    return m


def main():
    df = pd.read_csv(ROOT / "outputs" / "scored_stops.csv",
                     dtype={"stop_id": str, "tract_geoid": str})
    canopy = pd.read_csv(ROOT / "outputs" / "stop_canopy.csv", dtype={"stop_id": str},
                         usecols=["stop_id", "pct_green"])
    df = df.merge(canopy, on="stop_id", how="left", validate="one_to_one")
    print(f"canopy joined, {df['pct_green'].notna().sum()} of {len(df)} stops have pct_green")
    m = build(df)
    DOCS.mkdir(exist_ok=True)
    m.save(DOCS / "index.html")
    size_kb = (DOCS / "index.html").stat().st_size / 1024
    print(f"wrote docs/index.html ({size_kb:.0f} KB), {N_RANKED} ranked stops")


if __name__ == "__main__":
    main()

"""Stream A: Landsat Collection 2 L2 surface temperature over Alachua County.

Fetch scenes from Microsoft Planetary Computer, verify the ST scale factors
against asset metadata, apply the qa_pixel cloud mask, convert lwir11 to
Celsius. Everything downloaded is cached under data/.

Run the first-milestone sanity check (one scene -> PNG):

    python src/lst.py
"""

import time
from pathlib import Path

import numpy as np
import planetary_computer
import pystac_client
import rioxarray  # noqa: F401  (registers .rio accessor)
import xarray as xr

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "landsat-c2-l2"

# Alachua County, generous bbox (lon_min, lat_min, lon_max, lat_max)
ALACHUA_BBOX = (-82.66, 29.42, -82.04, 29.95)

# Summer 2026 window
DATE_RANGE = "2026-06-01/2026-09-20"

# Collection 2 L2 ST band scaling, per USGS docs. Verified against asset
# metadata at runtime in get_scale_offset(); these are only the expected values.
EXPECTED_SCALE = 0.00341802
EXPECTED_OFFSET = 149.0

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# qa_pixel bits that invalidate a pixel: fill, dilated cloud, cirrus,
# cloud, cloud shadow
QA_BAD_BITS = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4)


def search_items(bbox=ALACHUA_BBOX, date_range=DATE_RANGE, max_cloud=20):
    """Return signed STAC items, sorted by cloud cover ascending."""
    catalog = pystac_client.Client.open(
        STAC_URL, modifier=planetary_computer.sign_inplace
    )
    search = catalog.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=date_range,
        query={
            "eo:cloud_cover": {"lt": max_cloud},
            "platform": {"in": ["landsat-8", "landsat-9"]},
        },
    )
    items = list(search.items())
    # L2SR products carry surface reflectance only; the ST band we need
    # (lwir11) exists only on L2SP items
    items = [it for it in items if "lwir11" in it.assets]
    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100.0))
    return items


def get_scale_offset(item):
    """Read scale/offset for lwir11 from the item's asset metadata.

    Falls back to the documented constants only if the metadata is missing,
    and says so loudly.
    """
    bands = item.assets["lwir11"].extra_fields.get("raster:bands") or []
    if bands and "scale" in bands[0] and "offset" in bands[0]:
        scale, offset = bands[0]["scale"], bands[0]["offset"]
        print(f"  metadata scale={scale} offset={offset} "
              f"(expected {EXPECTED_SCALE}/{EXPECTED_OFFSET})")
        if not (np.isclose(scale, EXPECTED_SCALE) and np.isclose(offset, EXPECTED_OFFSET)):
            print("  WARNING: metadata disagrees with documented constants; "
                  "using metadata values")
        return scale, offset
    print("  WARNING: no raster:bands metadata on lwir11, falling back to "
          f"documented constants {EXPECTED_SCALE}/{EXPECTED_OFFSET}")
    return EXPECTED_SCALE, EXPECTED_OFFSET


def _cache_paths(item):
    return (
        DATA_DIR / f"{item.id}_lwir11.tif",
        DATA_DIR / f"{item.id}_qa_pixel.tif",
    )


def load_scene(item, bbox=ALACHUA_BBOX):
    """Load lwir11 + qa_pixel for one item, windowed to bbox, cached to data/.

    Returns (lwir11, qa_pixel) as 2-D DataArrays in the scene's native CRS.
    """
    DATA_DIR.mkdir(exist_ok=True)
    lwir_path, qa_path = _cache_paths(item)

    if lwir_path.exists() and qa_path.exists():
        print(f"  cache hit: {lwir_path.name}")
        lwir = rioxarray.open_rasterio(lwir_path).squeeze("band", drop=True)
        qa = rioxarray.open_rasterio(qa_path).squeeze("band", drop=True)
        return lwir, qa

    import odc.stac

    t0 = time.perf_counter()
    ds = odc.stac.load(
        [item],
        bands=["lwir11", "qa_pixel"],
        bbox=bbox,
        chunks=None,
    )
    elapsed = time.perf_counter() - t0
    lwir = ds["lwir11"].isel(time=0)
    qa = ds["qa_pixel"].isel(time=0)
    print(f"  fetched in {elapsed:.1f}s")

    lwir.rio.to_raster(lwir_path)
    qa.rio.to_raster(qa_path)
    print(f"  cached -> {lwir_path.name}, {qa_path.name}")
    return lwir, qa


def scene_to_celsius(item, bbox=ALACHUA_BBOX):
    """One scene -> cloud-masked LST in Celsius (float32, NaN where invalid)."""
    lwir, qa = load_scene(item, bbox)
    print(f"  raw lwir11 shape={lwir.shape} crs={lwir.rio.crs} "
          f"min={int(lwir.min())} max={int(lwir.max())}")

    scale, offset = get_scale_offset(item)

    # 0 in lwir11 is nodata/fill for Landsat C2
    valid = (lwir != 0) & ((qa.astype(np.uint16) & QA_BAD_BITS) == 0)
    celsius = (lwir.astype("float32") * scale + offset - 273.15).where(valid)
    celsius.rio.write_crs(lwir.rio.crs, inplace=True)

    frac_masked = 1.0 - float(valid.mean())
    print(f"  celsius shape={celsius.shape} crs={celsius.rio.crs} "
          f"min={float(celsius.min()):.1f} max={float(celsius.max()):.1f} "
          f"masked={frac_masked:.1%}")
    return celsius


def render_preview(celsius, title, out_path=DATA_DIR / "lst_preview.png"):
    """Save a quick-look PNG with a Celsius colorbar."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    vmin, vmax = np.nanpercentile(celsius.values, [2, 98])
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(celsius.values, cmap="inferno", vmin=vmin, vmax=vmax)
    fig.colorbar(im, ax=ax, label="Land surface temperature (deg C)", shrink=0.8)
    ax.set_title(title)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  preview -> {out_path}")
    return out_path


def build_composite(items, bbox=ALACHUA_BBOX, crs="EPSG:32617", resolution=30):
    """Per-pixel median LST (Celsius) across scenes, on one common grid.

    Scene-level cloud cover barely matters here because every pixel is
    masked individually with qa_pixel before the median.

    Returns (celsius_median, n_obs, scene_dates) where n_obs counts valid
    observations per pixel and scene_dates is a sorted list of YYYY-MM-DD.
    Cached to data/ keyed by the set of item ids.
    """
    import hashlib

    DATA_DIR.mkdir(exist_ok=True)
    key = hashlib.md5(",".join(sorted(it.id for it in items)).encode()).hexdigest()[:10]
    comp_path = DATA_DIR / f"lst_composite_{key}.tif"
    nobs_path = DATA_DIR / f"lst_composite_{key}_nobs.tif"
    dates_path = DATA_DIR / f"lst_composite_{key}_dates.txt"

    scene_dates = sorted({it.properties["datetime"][:10] for it in items})

    if comp_path.exists() and nobs_path.exists():
        print(f"  cache hit: {comp_path.name}")
        median = rioxarray.open_rasterio(comp_path).squeeze("band", drop=True)
        n_obs = rioxarray.open_rasterio(nobs_path).squeeze("band", drop=True)
        return median, n_obs, scene_dates

    # All scenes must agree on scaling before we composite them together
    scales = {get_scale_offset(it) for it in items}
    if len(scales) != 1:
        raise ValueError(f"Inconsistent scale/offset across scenes: {scales}")
    scale, offset = scales.pop()

    import odc.stac

    t0 = time.perf_counter()
    ds = odc.stac.load(
        items,
        bands=["lwir11", "qa_pixel"],
        bbox=bbox,
        crs=crs,
        resolution=resolution,
        groupby="solar_day",
        chunks=None,
    )
    print(f"  fetched {ds.sizes['time']} solar days in "
          f"{time.perf_counter() - t0:.1f}s, grid {ds.sizes['y']}x{ds.sizes['x']}")

    valid = (ds["lwir11"] != 0) & ((ds["qa_pixel"].astype(np.uint16) & QA_BAD_BITS) == 0)
    celsius = (ds["lwir11"].astype("float32") * scale + offset - 273.15).where(valid)

    median = celsius.median(dim="time", skipna=True).astype("float32")
    n_obs = valid.sum(dim="time").astype("int16")
    median.rio.write_crs(crs, inplace=True)
    n_obs.rio.write_crs(crs, inplace=True)

    covered = float((n_obs > 0).mean())
    print(f"  composite shape={median.shape} crs={median.rio.crs} "
          f"min={float(median.min()):.1f} max={float(median.max()):.1f} "
          f"coverage={covered:.1%} median_obs_per_px={float(n_obs.median()):.0f}")

    median.rio.to_raster(comp_path)
    n_obs.rio.to_raster(nobs_path)
    dates_path.write_text("\n".join(scene_dates), encoding="utf-8")
    print(f"  cached -> {comp_path.name}")
    return median, n_obs, scene_dates


def compute_stop_lst(median, scene_dates,
                     stops_path=None, out_path=None, buffer_m=100):
    """Zonal stats per stop -> outputs/stop_lst.csv per CONTRACTS.md.

    Buffers are built in EPSG:6440 (Florida North, meters) per CLAUDE.md,
    then reprojected to the raster CRS for the stats.
    """
    import geopandas as gpd
    import pandas as pd
    from rasterstats import zonal_stats

    root = Path(__file__).resolve().parent.parent
    stops_path = stops_path or root / "outputs" / "stops.geojson"
    out_path = out_path or root / "outputs" / "stop_lst.csv"

    stops = gpd.read_file(stops_path)
    print(f"  stops: {stops.shape} crs={stops.crs}")

    buffers = (
        stops.to_crs("EPSG:6440").geometry.buffer(buffer_m).to_crs(median.rio.crs)
    )

    arr = np.ma.masked_invalid(median.values)
    zs = zonal_stats(
        buffers, arr, affine=median.rio.transform(),
        stats=["mean", "max", "count"],
    )

    df = pd.DataFrame({
        "stop_id": stops["stop_id"].astype(str),
        "mean_lst_c": [z["mean"] for z in zs],
        "max_lst_c": [z["max"] for z in zs],
        "pixel_count": [int(z["count"]) for z in zs],
        "scene_dates": ";".join(scene_dates),
    })

    n_zero = int((df["pixel_count"] == 0).sum())
    print(f"  stop_lst: {df.shape}, pixel_count==0 for {n_zero} stops, "
          f"pixel_count median={df['pixel_count'].median():.0f}, "
          f"mean_lst_c range=[{df['mean_lst_c'].min():.1f}, "
          f"{df['mean_lst_c'].max():.1f}]")

    df.to_csv(out_path, index=False)
    print(f"  wrote {out_path}")
    return df


# Published TIRS band 10 thermal constants, used only if mtl.json is unreachable
PLANCK_K = {"landsat-8": (774.8853, 1321.0789), "landsat-9": (799.0284, 1329.2405)}


def get_planck_constants(item):
    """K1/K2 for band 10 from the item's mtl.json, else published constants."""
    import json
    import urllib.request

    try:
        with urllib.request.urlopen(item.assets["mtl.json"].href, timeout=30) as r:
            mtl = json.load(r)
        tc = mtl["LANDSAT_METADATA_FILE"]["LEVEL1_THERMAL_CONSTANTS"]
        return float(tc["K1_CONSTANT_BAND_10"]), float(tc["K2_CONSTANT_BAND_10"])
    except Exception as e:
        k = PLANCK_K[item.properties["platform"]]
        print(f"  mtl.json unavailable for {item.id} ({e}), "
              f"using published K1/K2 {k}")
        return k


def build_bt_composite(items, bbox=ALACHUA_BBOX, crs="EPSG:32617", resolution=30):
    """Median brightness temperature (Celsius) composite from the trad band.

    trad (thermal radiance) has no ASTER-GED emissivity dependency, so it
    covers the structural holes in the lwir11 ST product. BT underestimates
    true LST; calibrate against lwir11 before using it as a fill.
    """
    import hashlib

    DATA_DIR.mkdir(exist_ok=True)
    key = hashlib.md5(("bt:" + ",".join(sorted(it.id for it in items))).encode()).hexdigest()[:10]
    comp_path = DATA_DIR / f"bt_composite_{key}.tif"

    if comp_path.exists():
        print(f"  cache hit: {comp_path.name}")
        return rioxarray.open_rasterio(comp_path).squeeze("band", drop=True)

    # each solar day is a single platform (L8 and L9 are 8 days apart), so
    # Planck constants can be looked up per day
    day_k = {}
    for it in items:
        day = np.datetime64(it.properties["datetime"][:10])
        if day not in day_k:
            day_k[day] = get_planck_constants(it)

    import odc.stac

    t0 = time.perf_counter()
    ds = odc.stac.load(
        items, bands=["trad", "qa_pixel"], bbox=bbox, crs=crs,
        resolution=resolution, groupby="solar_day", chunks=None,
    )
    print(f"  fetched {ds.sizes['time']} solar days in {time.perf_counter() - t0:.1f}s")

    slices = []
    for t in ds.time.values:
        k1, k2 = day_k[t.astype("datetime64[D]")]
        trad = ds["trad"].sel(time=t)
        qa = ds["qa_pixel"].sel(time=t)
        valid = (trad > 0) & ((qa.astype(np.uint16) & QA_BAD_BITS) == 0)
        radiance = trad.astype("float32") * 0.001
        bt = (k2 / np.log(k1 / radiance + 1.0) - 273.15).where(valid)
        slices.append(bt)

    median = xr.concat(slices, dim="time").median(dim="time", skipna=True).astype("float32")
    median.rio.write_crs(crs, inplace=True)
    print(f"  BT composite shape={median.shape} crs={median.rio.crs} "
          f"min={float(median.min()):.1f} max={float(median.max()):.1f} "
          f"coverage={float(median.notnull().mean()):.1%}")
    median.rio.to_raster(comp_path)
    return median


def _zonal(median, stops, buffer_m=100, stats=("mean", "max", "count")):
    from rasterstats import zonal_stats

    buffers = stops.to_crs("EPSG:6440").geometry.buffer(buffer_m).to_crs(median.rio.crs)
    return zonal_stats(buffers, np.ma.masked_invalid(median.values),
                       affine=median.rio.transform(), stats=list(stats))


def gapfill(items, scene_dates):
    """Estimate LST for stops in the ST product's emissivity holes.

    Fits mean_lst_c ~ mean BT over stops that have both, then predicts for
    the pixel_count == 0 stops. Writes outputs/stop_lst_gapfill.csv (42 rows,
    contract columns plus method/fit-quality columns). Opt-in for C.
    """
    import geopandas as gpd
    import pandas as pd

    root = Path(__file__).resolve().parent.parent
    df = pd.read_csv(root / "outputs" / "stop_lst.csv", dtype={"stop_id": str})
    stops = gpd.read_file(root / "outputs" / "stops.geojson")

    bt = build_bt_composite(items)
    zs = _zonal(bt, stops)
    bt_df = pd.DataFrame({
        "stop_id": stops["stop_id"].astype(str),
        "mean_bt_c": [z["mean"] for z in zs],
        "max_bt_c": [z["max"] for z in zs],
        "bt_pixel_count": [int(z["count"]) for z in zs],
    })
    m = df.merge(bt_df, on="stop_id")

    fit = m[(m.pixel_count > 0) & (m.bt_pixel_count > 0)]
    slope, intercept = np.polyfit(fit.mean_bt_c, fit.mean_lst_c, 1)
    pred = slope * fit.mean_bt_c + intercept
    resid = fit.mean_lst_c - pred
    r2 = 1 - (resid ** 2).sum() / ((fit.mean_lst_c - fit.mean_lst_c.mean()) ** 2).sum()
    rmse = float(np.sqrt((resid ** 2).mean()))
    print(f"  calibration on {len(fit)} stops: lst = {slope:.3f}*bt + {intercept:.2f}, "
          f"r2={r2:.3f} rmse={rmse:.2f} C")

    gap = m[m.pixel_count == 0].copy()
    out = pd.DataFrame({
        "stop_id": gap.stop_id,
        "mean_lst_c": (slope * gap.mean_bt_c + intercept).round(2),
        "max_lst_c": (slope * gap.max_bt_c + intercept).round(2),
        "pixel_count": gap.bt_pixel_count,
        "scene_dates": ";".join(scene_dates),
        "method": "bt_regression",
        "fit_r2": round(float(r2), 3),
        "fit_rmse_c": round(rmse, 2),
    })
    n_est = int(out.mean_lst_c.notna().sum())
    print(f"  gapfill: {out.shape}, estimated LST for {n_est} of {len(out)} stops, "
          f"range=[{out.mean_lst_c.min():.1f}, {out.mean_lst_c.max():.1f}]")
    out_path = root / "outputs" / "stop_lst_gapfill.csv"
    out.to_csv(out_path, index=False)
    print(f"  wrote {out_path}")
    return out


def rank_stability(items):
    """Spearman rank correlation: single clearest scene vs the composite.

    One defensibility sentence for the README: does the ranking depend on
    compositing choices?
    """
    import geopandas as gpd
    import pandas as pd

    root = Path(__file__).resolve().parent.parent
    df = pd.read_csv(root / "outputs" / "stop_lst.csv", dtype={"stop_id": str})
    stops = gpd.read_file(root / "outputs" / "stops.geojson")

    best = items[0]
    print(f"  single scene: {best.id} "
          f"({best.properties['eo:cloud_cover']:.1f}% cloud)")
    celsius = scene_to_celsius(best)
    zs = _zonal(celsius, stops, stats=("mean", "count"))
    single = pd.DataFrame({
        "stop_id": stops["stop_id"].astype(str),
        "single_mean": [z["mean"] for z in zs],
        "single_count": [int(z["count"]) for z in zs],
    })
    m = df.merge(single, on="stop_id")
    both = m[(m.pixel_count > 0) & (m.single_count > 0)].dropna(
        subset=["mean_lst_c", "single_mean"])
    rho = both.mean_lst_c.rank().corr(both.single_mean.rank())
    print(f"  {len(both)} stops have data in both; Spearman rank correlation "
          f"= {rho:.3f}")
    return rho


def build_ndvi_composite(bbox, date_range=DATE_RANGE, max_cloud=40,
                         crs="EPSG:32617", resolution=10):
    """Median NDVI composite from Sentinel-2 L2A at 10 m, SCL cloud-masked.

    MPC serves unharmonized DNs: processing baseline >= 04.00 carries a
    +1000 offset that must be removed before the ratio, or NDVI skews low
    over dark surfaces. Verified against s2:processing_baseline per item.
    """
    import hashlib

    catalog = pystac_client.Client.open(
        STAC_URL, modifier=planetary_computer.sign_inplace
    )
    items = list(catalog.search(
        collections=["sentinel-2-l2a"], bbox=bbox, datetime=date_range,
        query={"eo:cloud_cover": {"lt": max_cloud}},
    ).items())
    print(f"  {len(items)} Sentinel-2 scenes with <{max_cloud}% cloud")
    baselines = {it.properties.get("s2:processing_baseline", "0") for it in items}
    if any(float(b) < 4.0 for b in baselines):
        raise ValueError(f"Mixed processing baselines {baselines}: "
                         "per-item offsets needed, refusing to guess")
    dn_offset = 1000.0

    DATA_DIR.mkdir(exist_ok=True)
    key = hashlib.md5(("ndvi:" + ",".join(sorted(it.id for it in items))).encode()).hexdigest()[:10]
    comp_path = DATA_DIR / f"ndvi_composite_{key}.tif"
    if comp_path.exists():
        print(f"  cache hit: {comp_path.name}")
        return rioxarray.open_rasterio(comp_path).squeeze("band", drop=True), items

    import odc.stac

    t0 = time.perf_counter()
    ds = odc.stac.load(
        items, bands=["B04", "B08", "SCL"], bbox=bbox, crs=crs,
        resolution=resolution, groupby="solar_day", chunks=None,
    )
    print(f"  fetched {ds.sizes['time']} solar days in "
          f"{time.perf_counter() - t0:.1f}s, grid {ds.sizes['y']}x{ds.sizes['x']}")

    # SCL classes: 0 nodata, 1 saturated, 3 cloud shadow, 8/9 cloud, 10 cirrus
    bad = ds["SCL"].isin([0, 1, 3, 8, 9, 10])
    red = (ds["B04"].astype("float32") - dn_offset).clip(0)
    nir = (ds["B08"].astype("float32") - dn_offset).clip(0)
    valid = (~bad) & (ds["B04"] > 0) & (ds["B08"] > 0) & ((nir + red) > 0)
    ndvi = ((nir - red) / (nir + red)).where(valid)

    median = ndvi.median(dim="time", skipna=True).astype("float32")
    median.rio.write_crs(crs, inplace=True)
    print(f"  NDVI composite shape={median.shape} "
          f"min={float(median.min()):.2f} max={float(median.max()):.2f} "
          f"coverage={float(median.notnull().mean()):.1%}")
    median.rio.to_raster(comp_path)
    return median, items


def canopy():
    """Per-stop greenness in the 100 m buffer -> outputs/stop_canopy.csv.

    mean_ndvi is the buffer average; pct_green is the share of valid 10 m
    pixels with NDVI > 0.4, a rough canopy-or-dense-vegetation fraction.
    Opt-in context for the map popups, not part of the frozen score formula.
    """
    import geopandas as gpd
    import pandas as pd

    root = Path(__file__).resolve().parent.parent
    stops = gpd.read_file(root / "outputs" / "stops.geojson")
    b = stops.total_bounds
    bbox = (b[0] - 0.01, b[1] - 0.01, b[2] + 0.01, b[3] + 0.01)

    median, items = build_ndvi_composite(bbox)
    scene_dates = sorted({it.properties["datetime"][:10] for it in items})

    from rasterstats import zonal_stats

    buffers = stops.to_crs("EPSG:6440").geometry.buffer(100).to_crs(median.rio.crs)
    arr = np.ma.masked_invalid(median.values)
    zs = zonal_stats(buffers, arr, affine=median.rio.transform(),
                     stats=["mean", "count"],
                     add_stats={"green": lambda x: float((x > 0.4).sum())})

    df = pd.DataFrame({
        "stop_id": stops["stop_id"].astype(str),
        "mean_ndvi": [round(z["mean"], 3) if z["count"] else None for z in zs],
        "pct_green": [round(100.0 * z["green"] / z["count"], 1) if z["count"] else None
                      for z in zs],
        "pixel_count": [int(z["count"]) for z in zs],
        "scene_dates": ";".join(scene_dates),
    })
    n_zero = int((df.pixel_count == 0).sum())
    print(f"  stop_canopy: {df.shape}, pixel_count==0 for {n_zero} stops, "
          f"mean_ndvi range=[{df.mean_ndvi.min():.2f}, {df.mean_ndvi.max():.2f}], "
          f"pct_green median={df.pct_green.median():.0f}")
    out_path = root / "outputs" / "stop_canopy.csv"
    df.to_csv(out_path, index=False)
    print(f"  wrote {out_path}")
    return df


def _earthdata_session():
    """Authenticated session: netrc via earthaccess, else bearer token file."""
    import earthaccess
    import requests

    try:
        auth = earthaccess.login(strategy="netrc")
        if auth.authenticated:
            return earthaccess.get_requests_https_session()
    except Exception:
        pass
    token_path = DATA_DIR / "earthdata_token.txt"
    if token_path.exists():
        s = requests.Session()
        s.headers["Authorization"] = f"Bearer {token_path.read_text().strip()}"
        return s
    raise SystemExit(
        "No Earthdata auth. Either run earthaccess.login(persist=True) in a "
        "terminal or put a token in data/earthdata_token.txt"
    )


def ecostress(afternoon_utc=(16, 21)):
    """Afternoon LST per stop from ECOSTRESS ECO_L2T_LSTE v2 tiles.

    Downloads LST and cloud GeoTIFFs for afternoon (default 12:00-17:00 EDT)
    summer overpasses, builds a cloud-masked median composite in Celsius,
    and writes outputs/stop_lst_afternoon.csv (opt-in for C, contract-like
    schema). Tiles share one grid per MGRS tile, so no reprojection between
    granules is needed.
    """
    import earthaccess
    import geopandas as gpd
    import pandas as pd

    root = Path(__file__).resolve().parent.parent
    eco_dir = DATA_DIR / "ecostress"
    eco_dir.mkdir(parents=True, exist_ok=True)

    results = earthaccess.search_data(
        short_name="ECO_L2T_LSTE",
        bounding_box=(-82.45, 29.60, -82.30, 29.72),
        temporal=("2026-06-01", "2026-09-20"),
    )
    seen = set()
    granules = []
    for g in results:
        t = g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
        # CMR can return multiple processing versions of one overpass
        if afternoon_utc[0] <= int(t[11:13]) <= afternoon_utc[1] and t not in seen:
            seen.add(t)
            granules.append((t, g))
    granules.sort(key=lambda x: x[0])
    print(f"  {len(results)} granules total, {len(granules)} in the "
          f"{afternoon_utc[0]}-{afternoon_utc[1]}h UTC afternoon window")

    session = _earthdata_session()
    files = {"LST": [], "cloud": []}
    t0 = time.perf_counter()
    for t, g in granules:
        links = [u for u in g.data_links() if u.endswith(".tif")]
        for kind in files:
            want = [u for u in links if u.endswith(f"_{kind}.tif")]
            if not want:
                continue
            url = want[0]
            dest = eco_dir / url.rsplit("/", 1)[1]
            if not dest.exists():
                r = session.get(url, timeout=120)
                r.raise_for_status()
                dest.write_bytes(r.content)
            files[kind].append((t, dest))
    print(f"  {len(files['LST'])} LST tiles on disk "
          f"({time.perf_counter() - t0:.0f}s incl. cache hits)")

    slices, used_dates = [], set()
    ref = None
    for (t, lst_path), (_, cloud_path) in zip(files["LST"], files["cloud"]):
        lst = rioxarray.open_rasterio(lst_path, masked=True).squeeze("band", drop=True)
        cloud = rioxarray.open_rasterio(cloud_path).squeeze("band", drop=True)
        if ref is None:
            ref = lst
            print(f"  tile grid {lst.shape} crs={lst.rio.crs}")
        elif lst.shape != ref.shape:
            print(f"  skipping {lst_path.name}: different tile/grid {lst.shape}")
            continue
        vals = lst.values.astype("float32")
        # v2 tiled LST is Kelvin; some builds ship scaled ints, so normalize
        finite = vals[np.isfinite(vals)]
        if finite.size and finite.max() > 400:
            vals = vals * 0.02
        vals = vals - 273.15
        vals[(cloud.values == 1) | ~np.isfinite(vals)] = np.nan
        frac = np.isfinite(vals).mean()
        if frac < 0.40:
            # the ECOSTRESS cloud mask is permissive: mostly-cloudy overpasses
            # keep contaminated edge pixels that read cold and add noise
            print(f"  skipping {lst_path.name.split('_')[5]}: only {frac:.0%} valid")
            continue
        slices.append(vals)
        used_dates.add(t[:10])
    if not slices:
        raise SystemExit("No usable afternoon tiles after cloud masking")

    stack = np.stack(slices)
    median = np.nanmedian(stack, axis=0).astype("float32")
    comp = ref.copy(data=median)
    n_obs = np.isfinite(stack).sum(axis=0)
    print(f"  afternoon composite from {len(slices)} overpasses on "
          f"{len(used_dates)} days: min={np.nanmin(median):.1f} "
          f"max={np.nanmax(median):.1f} "
          f"coverage={np.isfinite(median).mean():.1%} "
          f"median_obs={int(np.median(n_obs))}")

    stops = gpd.read_file(root / "outputs" / "stops.geojson")
    zs = _zonal(comp, stops)
    df = pd.DataFrame({
        "stop_id": stops["stop_id"].astype(str),
        "mean_lst_c": [round(z["mean"], 2) if z["count"] else None for z in zs],
        "max_lst_c": [round(z["max"], 2) if z["count"] else None for z in zs],
        "pixel_count": [int(z["count"]) for z in zs],
        "scene_dates": ";".join(sorted(used_dates)),
    })
    n_zero = int((df.pixel_count == 0).sum())
    print(f"  stop_lst_afternoon: {df.shape}, pixel_count==0 for {n_zero} "
          f"stops, mean range=[{df.mean_lst_c.min():.1f}, "
          f"{df.mean_lst_c.max():.1f}]")
    out_path = root / "outputs" / "stop_lst_afternoon.csv"
    df.to_csv(out_path, index=False)
    print(f"  wrote {out_path}")
    return df


if __name__ == "__main__":
    import sys

    MAX_CLOUD = 90  # per-pixel qa_pixel masking does the real cloud work
    mode = sys.argv[1] if len(sys.argv) > 1 else "main"

    if mode == "canopy":
        print("Sentinel-2 canopy proxy per stop...")
        canopy()
        raise SystemExit(0)
    if mode == "eco":
        print("ECOSTRESS afternoon LST per stop...")
        ecostress()
        raise SystemExit(0)

    print("Searching Planetary Computer...")
    items = search_items(max_cloud=MAX_CLOUD)
    print(f"Found {len(items)} scenes with <{MAX_CLOUD}% cloud in {DATE_RANGE}:")
    for it in items:
        print(f"  {it.id}  cloud={it.properties['eo:cloud_cover']:.1f}%  "
              f"{it.properties['datetime'][:10]}")
    if not items:
        raise SystemExit("No scenes found. Widen the date range or cloud threshold.")

    scene_dates = sorted({it.properties["datetime"][:10] for it in items})

    if mode == "gapfill":
        print("\nGap-filling ST holes from brightness temperature...")
        gapfill(items, scene_dates)
        raise SystemExit(0)
    if mode == "stability":
        print("\nRank stability check...")
        rank_stability(items)
        raise SystemExit(0)
    if mode == "splithalf":
        import geopandas as gpd
        import pandas as pd

        print("\nSplit-half stability: median of odd vs even solar days...")
        days = sorted({it.properties["datetime"][:10] for it in items})
        half_a = [it for it in items if days.index(it.properties["datetime"][:10]) % 2 == 0]
        half_b = [it for it in items if days.index(it.properties["datetime"][:10]) % 2 == 1]
        stops = gpd.read_file(Path(__file__).resolve().parent.parent / "outputs" / "stops.geojson")
        halves = []
        for name, half in [("A", half_a), ("B", half_b)]:
            print(f"  half {name}: {len(half)} scenes")
            comp, _, _ = build_composite(half)
            zs = _zonal(comp, stops, stats=("mean", "count"))
            halves.append(pd.Series(
                [z["mean"] if z["count"] > 0 else np.nan for z in zs]))
        both = pd.DataFrame({"a": halves[0], "b": halves[1]}).dropna()
        rho = both.a.rank().corr(both.b.rank())
        print(f"  {len(both)} stops covered in both halves; "
              f"Spearman rank correlation = {rho:.3f}")
        raise SystemExit(0)

    print("\nBuilding median composite...")
    t0 = time.perf_counter()
    median, n_obs, scene_dates = build_composite(items)
    print(f"Total composite: {time.perf_counter() - t0:.1f}s, "
          f"dates: {'; '.join(scene_dates)}")

    lo, hi = float(median.min()), float(median.max())
    if not (15.0 <= lo and hi <= 60.0):
        print(f"WARNING: LST range [{lo:.1f}, {hi:.1f}] C is outside the "
              "plausible 15-60 C envelope for Florida summer. Check scaling "
              "before building on this.")

    render_preview(
        median,
        f"Landsat LST median composite, Alachua County\n"
        f"{len(scene_dates)} days, {scene_dates[0]} to {scene_dates[-1]}",
        out_path=DATA_DIR / "lst_composite_preview.png",
    )

    print("\nZonal stats per stop...")
    compute_stop_lst(median, scene_dates)

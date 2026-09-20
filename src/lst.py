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


def render_preview(celsius, item, out_path=DATA_DIR / "lst_preview.png"):
    """Save a quick-look PNG with a Celsius colorbar."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    vmin, vmax = np.nanpercentile(celsius.values, [2, 98])
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(celsius.values, cmap="inferno", vmin=vmin, vmax=vmax)
    fig.colorbar(im, ax=ax, label="Land surface temperature (deg C)", shrink=0.8)
    date = item.properties["datetime"][:10]
    ax.set_title(f"Landsat LST, Alachua County, {date} "
                 f"({item.properties['platform']}, "
                 f"{item.properties['eo:cloud_cover']:.0f}% cloud)")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  preview -> {out_path}")
    return out_path


if __name__ == "__main__":
    print("Searching Planetary Computer...")
    items = search_items()
    print(f"Found {len(items)} scenes with <20% cloud in {DATE_RANGE}:")
    for it in items:
        print(f"  {it.id}  cloud={it.properties['eo:cloud_cover']:.1f}%  "
              f"{it.properties['datetime'][:10]}")
    if not items:
        raise SystemExit("No scenes found. Widen the date range or cloud threshold.")

    best = items[0]
    print(f"\nLoading best scene: {best.id}")
    t0 = time.perf_counter()
    celsius = scene_to_celsius(best)
    print(f"Total load+mask+scale: {time.perf_counter() - t0:.1f}s")

    lo, hi = float(celsius.min()), float(celsius.max())
    if not (15.0 <= lo and hi <= 60.0):
        print(f"WARNING: LST range [{lo:.1f}, {hi:.1f}] C is outside the "
              "plausible 15-60 C envelope for Florida summer. Check scaling "
              "before building on this.")

    render_preview(celsius, best)

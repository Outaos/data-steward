import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point, mapping
from pyproj import Transformer


def pop_within_buffer(
    tif_paths,   # <-- now accepts list[str]
    lat: float,
    lon: float,
    buffer_m: float = 30_000.0,
) -> float:
    total_pop = 0.0
    any_overlap = False

    for tif_path in tif_paths:
        with rasterio.open(tif_path) as src:
            raster_crs = src.crs
            if raster_crs is None:
                raise ValueError(f"Raster has no CRS defined: {tif_path}")

            transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
            geom = Point(x, y).buffer(buffer_m)

            # quick bbox skip
            minx, miny, maxx, maxy = geom.bounds
            left, bottom, right, top = src.bounds
            if (maxx < left) or (minx > right) or (maxy < bottom) or (miny > top):
                continue

            try:
                out_img, _ = mask(
                    src,
                    [mapping(geom)],
                    crop=True,
                    all_touched=True,
                    filled=True
                )
            except ValueError:
                # "Input shapes do not overlap raster."
                continue

            any_overlap = True
            data = out_img[0]

            nodata = src.nodata if src.nodata is not None else -200.0
            valid = (data != nodata) & np.isfinite(data) & (data >= 0)
            total_pop += float(data[valid].sum())

    if not any_overlap:
        raise ValueError("Buffer does not overlap any provided raster tiles.")

    return total_pop


if __name__ == "__main__":
    # ✅ put ALL 4 England tiles here
    tifs = [
        r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R3_C18.tif",
        r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R3_C19.tif",
        r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R4_C18.tif",
        r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R4_C19.tif",
    ]

    buffer_m = 30_000.0

    stadiums = {
        "Man United — Old Trafford": (53.4631, -2.2913),
        "Liverpool — Anfield": (53.4308, -2.9608),
        "Everton — Goodison Park": (53.4388, -2.9664),
        "Man City — Etihad Stadium": (53.4831, -2.2004),
        "Leeds United — Elland Road": (53.7778, -1.5721),
        "Newcastle United — St James’ Park": (54.9756, -1.6216),
        "Sunderland — Stadium of Light": (54.9144, -1.3884),
        "Aston Villa — Villa Park": (52.5092, -1.8849),
        "Wolves — Molineux Stadium": (52.5903, -2.1307),
        "Chelsea — Stamford Bridge": (51.4816, -0.1910),
        "Arsenal — Emirates Stadium": (51.5549, -0.1084),
        "Tottenham — Tottenham Hotspur Stadium": (51.6043, -0.0665),
        "West Ham — London Stadium": (51.5386, 0.0165),
        "Brighton — Amex Stadium": (50.8618, -0.0835),
        "Bournemouth — Vitality Stadium": (50.7352, -1.8383),
    }

    results = []
    for name, (lat, lon) in stadiums.items():
        try:
            total = pop_within_buffer(tifs, lat, lon, buffer_m=buffer_m)
            results.append((name, total))
        except Exception as e:
            results.append((name, None))
            print(f"[WARN] {name}: {e}")

    # sort: errors bottom, otherwise pop desc
    results.sort(key=lambda x: (x[1] is None, -(x[1] or 0)))

    print(f"\nEstimated population within {buffer_m/1000:.0f} km buffer (across {len(tifs)} tiles)")
    print("-" * 90)
    for name, total in results:
        if total is None:
            print(f"{name:45s}  ERROR")
        else:
            print(f"{name:45s}  {total:12,.0f}")
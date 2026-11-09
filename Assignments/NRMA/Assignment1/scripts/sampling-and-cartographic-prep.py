"""
Phase 4, step 1: R_factor_native.tif -> 30 m, EPSG:32736, clipped to Kasungu.

Input : data/processed/R_factor_native.tif   (EPSG:4326, ~5.5 km, buffered box)
        Kasungu_roi/*.gpkg or *.shp          (EPSG:32736)
Output: data/processed/R_factor_30m_kasungu.tif

The 30 m grid is for VISUALISATION ONLY (bilinear interpolation of a 5.5 km
product adds no information). State the true resolution (~5.5 km) on the map.

Needs: numpy, rasterio, geopandas.  Run from Spyder (F5), file in scripts/.
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

DST_CRS = "EPSG:32736"
RES = 30
NODATA = -9999.0

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:
    ROOT = Path(r"C:\Users\wongi\OneDrive\Desktop\Year 4\Lecture Notes\NRMA\Assignment\Assignment_1")

SRC = ROOT / "data/processed/R_factor_native.tif"
OUT = ROOT / "data/processed/R_factor_30m_kasungu.tif"
roi_file = next(iter(list((ROOT / "Kasungu_roi").glob("*.gpkg")) + list((ROOT / "Kasungu_roi").glob("*.shp"))))

# 1. ROI in the target CRS, destination grid snapped to 30 m ------------------
roi = gpd.read_file(roi_file).to_crs(DST_CRS)
minx, miny, maxx, maxy = roi.total_bounds
minx, miny = np.floor(minx / RES) * RES, np.floor(miny / RES) * RES
maxx, maxy = np.ceil(maxx / RES) * RES, np.ceil(maxy / RES) * RES
width, height = int((maxx - minx) / RES), int((maxy - miny) / RES)
dst_transform = from_origin(minx, maxy, RES, RES)
print(f"ROI: {roi_file.name} | output grid {width} x {height} px at {RES} m")

# 2. Reproject + resample (bilinear) ------------------------------------------
dst = np.full((height, width), NODATA, dtype="float32")
with rasterio.open(SRC) as src:
    reproject(
        source=rasterio.band(src, 1),
        destination=dst,
        src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata,
        dst_transform=dst_transform, dst_crs=DST_CRS, dst_nodata=NODATA,
        resampling=Resampling.bilinear,
    )

# 3. Exact clip to the district boundary --------------------------------------
outside = geometry_mask(list(roi.geometry), out_shape=dst.shape, transform=dst_transform, invert=False)
dst[outside] = NODATA

# 4. Save + report ------------------------------------------------------------
with rasterio.open(OUT, "w", driver="GTiff", height=height, width=width, count=1,
                   dtype="float32", crs=DST_CRS, transform=dst_transform,
                   nodata=NODATA, compress="lzw") as f:
    f.write(dst, 1)

valid = dst[dst != NODATA]
print(f"Saved {OUT}")
print(f"R (MJ mm ha-1 h-1 yr-1): min {valid.min():.0f}  mean {valid.mean():.0f}  max {valid.max():.0f}  (n={valid.size} px)")
if (dst[~outside] == NODATA).any():
    print("WARNING: nodata holes inside the district; check the source extent covers the ROI.")
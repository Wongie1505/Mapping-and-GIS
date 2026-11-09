"""
Phase 3: Annual rainfall (P) and RUSLE R-factor for Kasungu, 2025.

Input : 12 monthly CHIRPS totals (mm) in data/raw/  (chirps_2025_01.tif ... _12.tif)
Output: data/processed/annual_P.tif, data/processed/R_factor_native.tif
        outputs/monthly_rainfall.png

Equation: Renard & Freimund (1994), P-based, R in MJ mm ha-1 h-1 yr-1
    R = 0.0483 * P**1.61                          for P <= 850 mm
    R = 587.8 - 1.219*P + 0.004105*P**2           for P  > 850 mm
Derived from long-term mean P at 132 US stations; applied here to a single
year (2025) as an approximation. Run on the native ~5.5 km CHIRPS grid.

Needs: numpy, rasterio, matplotlib. Optional: geopandas (district-only stats).
Run from Spyder (F5) with the file saved in Assignment_1/scripts/.
"""
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------- equation
def r_factor(p):
    """Renard & Freimund (1994) P-based R factor. p: annual rainfall in mm."""
    p = np.asarray(p, dtype="float64")
    low = 0.0483 * p ** 1.61
    high = 587.8 - 1.219 * p + 0.004105 * p ** 2
    return np.where(p <= 850, low, high)


def run_tests():
    # Values recomputed by hand/Python (NOT the NotebookLM doc's 1459.72)
    assert abs(float(r_factor(600)) - 1434.73) < 0.05
    assert abs(float(r_factor(1200)) - 5036.20) < 0.05
    assert abs(float(r_factor(850)) - 2513.69) < 0.05
    assert abs(float(r_factor(851)) - float(r_factor(850))) < 10  # branches ~join
    print("Equation tests passed.")


# ---------------------------------------------------------------- main
def main():
    import matplotlib.pyplot as plt
    import rasterio
    from rasterio.features import geometry_mask

    # Project root = parent of scripts/. Edit ROOT if you run it from elsewhere.
    try:
        ROOT = Path(__file__).resolve().parents[1]
    except NameError:
        ROOT = Path(r"C:\Users\wongi\OneDrive\Desktop\Year 4\Lecture Notes\NRMA\Assignment\Assignment_1")

    RAW, PROC, OUT, ROI_DIR = ROOT / "data/raw", ROOT / "data/processed", ROOT / "outputs", ROOT / "Kasungu_roi"
    PROC.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    run_tests()

    # 1. Load the 12 monthly rasters and check they align ---------------------
    files = sorted(RAW.glob("chirps_2025_*.tif"))
    assert len(files) == 12, f"Expected 12 monthly files in {RAW}, found {len(files)}"
    print("Files:", [f.name for f in files])

    stack, profile = [], None
    for f in files:
        with rasterio.open(f) as src:
            arr = src.read(1).astype("float64")
            if profile is None:
                profile, ref = src.profile.copy(), (src.shape, src.transform, src.crs)
            else:
                assert (src.shape, src.transform, src.crs) == ref, f"{f.name} does not align with the others"
            if src.nodata is not None:
                arr[arr == src.nodata] = np.nan
        stack.append(arr)
    stack = np.stack(stack)                     # (12, rows, cols)
    print(f"Grid: {stack.shape[1]} x {stack.shape[2]} pixels, CRS {ref[2]}")

    # Sanity checks on the inputs
    assert not (stack < 0).any(), "Negative rainfall found"
    print("Monthly mean over the whole box (mm):", np.round(np.nanmean(stack, axis=(1, 2)), 1))

    # 2. Annual P and R --------------------------------------------------------
    P = np.nansum(stack, axis=0)
    P[np.isnan(stack).all(axis=0)] = np.nan
    R = r_factor(P)

    out_prof = profile.copy()
    out_prof.update(dtype="float32", count=1, nodata=-9999, compress="lzw")
    for name, arr in (("annual_P.tif", P), ("R_factor_native.tif", R)):
        with rasterio.open(PROC / name, "w", **out_prof) as dst:
            dst.write(np.where(np.isnan(arr), -9999, arr).astype("float32"), 1)
    print("Saved annual_P.tif and R_factor_native.tif in", PROC)

    # 3. Stats inside the district (needs geopandas); else whole box -----------
    def stats(label, a):
        a = a[~np.isnan(a)]
        print(f"{label}: min {a.min():.1f}  mean {a.mean():.1f}  max {a.max():.1f}  (n={a.size})")

    monthly_mean = np.nanmean(stack, axis=(1, 2))
    try:
        import geopandas as gpd
        roi_file = next(iter(list(ROI_DIR.glob("*.gpkg")) + list(ROI_DIR.glob("*.shp"))))
        roi = gpd.read_file(roi_file).to_crs(ref[2])
        inside = ~geometry_mask(list(roi.geometry), out_shape=P.shape,
                                transform=ref[1], all_touched=True)
        stats("Annual P in Kasungu (mm)", np.where(inside, P, np.nan))
        stats("R in Kasungu (MJ mm ha-1 h-1 yr-1)", np.where(inside, R, np.nan))
        monthly_mean = np.array([np.nanmean(m[inside]) for m in stack])
        print("Monthly mean P in Kasungu (mm):", np.round(monthly_mean, 1))
        print("Pixels touching Kasungu:", int(inside.sum()),
              "(few pixels: state the 5.5 km resolution in the method)")
    except Exception as e:
        print(f"District stats skipped ({type(e).__name__}: {e}). Using whole export box.")
        stats("Annual P, whole box (mm)", P)
        stats("R, whole box", R)

    # 4. Monthly rainfall chart -------------------------------------------------
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(6, 3), dpi=200)
    ax.bar(months, monthly_mean, color="#2b6cb0")
    ax.set_ylabel("Rainfall (mm)")
    ax.set_title("Kasungu monthly rainfall, 2025 (CHIRPS, district mean)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "monthly_rainfall.png")
    print("Saved", OUT / "monthly_rainfall.png")


if __name__ == "__main__":
    main()
"""Locate yearly non-irrigated corn GeoTIFF masks (clean preferred)."""

from __future__ import annotations

from pathlib import Path

from config import AOI_CRS, AOI_HEIGHT, AOI_NODATA, AOI_RES_M, AOI_WIDTH, AOI_YEARS


def clean_name(year: int) -> str:
    return f"non_irrigated_corn_mlrane_{year}_clean.tif"


def parent_name(year: int) -> str:
    return f"non_irrigated_corn_mlrane_{year}.tif"


def find_aoi_raster(year: int, clean_dir: Path, parent_dir: Path | None = None) -> dict:
    parent_dir = parent_dir or clean_dir.parent
    clean = clean_dir / clean_name(year)
    parent = parent_dir / parent_name(year)
    if clean.exists():
        return {
            "year": year,
            "path": clean,
            "source": "clean",
            "status": "ok",
        }
    if parent.exists():
        return {
            "year": year,
            "path": parent,
            "source": "parent_fallback",
            "status": "ok",
        }
    if year in AOI_YEARS:
        return {
            "year": year,
            "path": None,
            "source": None,
            "status": "aoi_file_not_in_local_cache",
            "expected_clean": str(clean),
        }
    return {
        "year": year,
        "path": None,
        "source": None,
        "status": "aoi_raster_missing",
    }


def read_aoi_profile(path: Path) -> dict:
    import rasterio

    with rasterio.open(path) as src:
        nodata = src.nodata if src.nodata is not None else AOI_NODATA
        return {
            "width": src.width,
            "height": src.height,
            "crs": str(src.crs) if src.crs else None,
            "transform": src.transform,
            "bounds": src.bounds,
            "nodata": nodata,
            "dtype": str(src.dtypes[0]),
        }


def assert_aoi_grid(profile: dict, path: Path | None = None) -> None:
    problems = []
    if profile.get("width") != AOI_WIDTH:
        problems.append(f"width {profile.get('width')} != {AOI_WIDTH}")
    if profile.get("height") != AOI_HEIGHT:
        problems.append(f"height {profile.get('height')} != {AOI_HEIGHT}")
    crs = (profile.get("crs") or "").replace("epsg:", "EPSG:")
    if "5070" not in crs:
        problems.append(f"crs {profile.get('crs')} is not EPSG:5070")
    transform = profile.get("transform")
    if transform is not None:
        if abs(transform.a - AOI_RES_M) > 1e-6:
            problems.append(f"xres {transform.a} != {AOI_RES_M}")
        if abs(abs(transform.e) - AOI_RES_M) > 1e-6:
            problems.append(f"yres {transform.e} != -{AOI_RES_M}")
    if problems:
        loc = f" ({path})" if path else ""
        raise AssertionError("AOI grid mismatch" + loc + ": " + "; ".join(problems))


def affine_to_crs_transform(transform) -> list[float]:
    """GDAL/EE crsTransform: [a, b, c, d, e, f]."""
    return [float(transform.a), float(transform.b), float(transform.c),
            float(transform.d), float(transform.e), float(transform.f)]

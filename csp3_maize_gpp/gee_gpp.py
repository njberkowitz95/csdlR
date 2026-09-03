"""Landsat GPP on yearly non-irrigated corn surfaces (GEE + geemap + rasterio).

HI and MC_AGB are never written into rasters and never used to convert GPP.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import numpy as np

from aoi import affine_to_crs_transform, assert_aoi_grid, find_aoi_raster, read_aoi_profile
from config import (
    AOI_CRS,
    AOI_NODATA,
    AOI_RES_M,
    AOI_YEARS,
    COLAB_OUTPUTS,
    COLAB_PHD,
    COLAB_RASTERS,
    EE_DRIVE_FOLDER,
    EE_PROJECT,
    GPP_COLLECTION,
    GPP_MAX_YEAR,
    GPP_QC_CLEAR,
    GPP_SCALE,
    US_NE3_LAT,
    US_NE3_LON,
)

BAND_SEASON = "GPP_kgCm2_season"
BAND_NOBS = "n_obs"


def export_maize_years_from_tables(
    zonal_csv: Path,
    aoi_clean: Path,
    aoi_parent: Path,
    out_dir: Path,
    *,
    ee_project: str | None = None,
) -> list[dict]:
    """Export seasonal GPP GeoTIFFs for maize years that have AOI rasters."""
    import pandas as pd

    ok, _, err = try_ee_initialize(ee_project)
    if not ok:
        return [{"status": "gee_auth_missing", "gee_error": err}]

    zonal = pd.read_csv(zonal_csv)
    results = []
    for _, row in zonal.iterrows():
        if str(row.get("crop")) != "maize":
            continue
        year = int(row["year"])
        if year not in AOI_YEARS or year > GPP_MAX_YEAR:
            continue
        if pd.isna(row.get("buffered_start")) or pd.isna(row.get("gee_filter_end_exclusive")):
            results.append({"year": year, "status": "ops_dates_missing"})
            continue
        aoi = find_aoi_raster(year, aoi_clean, aoi_parent)
        if not aoi.get("path"):
            results.append({"year": year, "status": aoi.get("status")})
            continue
        info = export_year_rasters(
            year,
            date.fromisoformat(str(row["buffered_start"])[:10]),
            date.fromisoformat(str(row["buffered_end"])[:10]),
            date.fromisoformat(str(row["gee_filter_end_exclusive"])[:10]),
            Path(aoi["path"]),
            out_dir,
        )
        results.append(info)
    return results


def try_ee_initialize(project: str | None = None):
    import ee

    project = project or EE_PROJECT or os.environ.get("EE_PROJECT")
    errors = []
    if project:
        try:
            ee.Initialize(project=project)
            return True, project, None
        except Exception as exc:
            errors.append(str(exc))
    try:
        ee.Initialize()
        return True, project, None
    except Exception as exc:
        errors.append(str(exc))
        return False, project, " | ".join(errors)


def seasonal_gpp_images(buffered_start: date, end_exclusive: date):
    """QC-filter (10/11), scale 0.0001, sum GPP and count observations."""
    import ee

    start = buffered_start.isoformat()
    end = end_exclusive.isoformat()
    col = (
        ee.ImageCollection(GPP_COLLECTION)
        .select(["GPP", "QC"])
        .filterDate(start, end)
    )

    def mask_scale(img):
        qc = img.select("QC")
        clear = qc.eq(GPP_QC_CLEAR[0]).Or(qc.eq(GPP_QC_CLEAR[1]))
        return (
            img.select("GPP")
            .multiply(GPP_SCALE)
            .updateMask(clear)
            .copyProperties(img, ["system:time_start"])
        )

    mapped = col.map(mask_scale)
    seasonal = mapped.sum().rename(BAND_SEASON)
    n_obs = mapped.count().rename(BAND_NOBS)
    return seasonal, n_obs, mapped


def _region_from_profile(profile: dict):
    import ee

    b = profile["bounds"]
    return ee.Geometry.Rectangle(
        [b.left, b.bottom, b.right, b.top],
        proj=AOI_CRS,
        geodesic=False,
    )


def _reproject(image, profile: dict):
    import ee

    return image.reproject(
        crs=AOI_CRS,
        crsTransform=affine_to_crs_transform(profile["transform"]),
    )


def mask_to_ee(path: Path, profile: dict):
    """Best-effort corn mask as ee.Image. rasterio always re-applies the mask after export."""
    import ee

    try:
        import geemap
    except ImportError:
        geemap = None
    if geemap is not None:
        for attr in ("ee_image_from_geotiff", "geotiff_to_ee", "raster_to_ee"):
            fn = getattr(geemap, attr, None)
            if fn is None:
                continue
            try:
                img = fn(str(path))
                if img is not None:
                    return img
            except Exception:
                continue
    region = _region_from_profile(profile)
    return ee.Image(1).clip(region)


def _prepare_seasonal_images(year, buffered_start, end_exclusive, aoi_path):
    """QC-scale-sum GPP, reproject to the AOI grid, mask with corn > 0."""
    if year > GPP_MAX_YEAR:
        raise ValueError(f"UMT Landsat GPP is not used after {GPP_MAX_YEAR}")
    if year not in AOI_YEARS:
        raise ValueError(f"{year} has no AOI raster year list entry")

    profile = read_aoi_profile(aoi_path)
    assert_aoi_grid(profile, aoi_path)

    import rasterio

    with rasterio.open(aoi_path) as src:
        corn = src.read(1)
        nodata = src.nodata if src.nodata is not None else AOI_NODATA
        corn_mask = (corn != nodata) & (corn > 0)
        if int(corn_mask.sum()) == 0:
            raise AssertionError(f"{aoi_path} has no valid corn pixels")

    seasonal, n_obs, _ = seasonal_gpp_images(buffered_start, end_exclusive)
    region = _region_from_profile(profile)
    corn_ee = mask_to_ee(aoi_path, profile)
    seasonal = _reproject(seasonal, profile).updateMask(corn_ee.gt(0)).clip(region).rename(BAND_SEASON)
    n_obs = _reproject(n_obs, profile).updateMask(corn_ee.gt(0)).clip(region).rename(BAND_NOBS)
    return seasonal, n_obs, profile, region


def export_year_rasters(
    year: int,
    buffered_start: date,
    buffered_end: date,
    end_exclusive: date,
    aoi_path: Path,
    out_dir: Path,
    *,
    use_geemap: bool = False,
    to_drive_folder: str = EE_DRIVE_FOLDER,
) -> dict:
    """Export seasonal GPP + n_obs for one maize year.

    The MLRA-NE grid is ~29 million pixels (~117 MB float32), so
    ``geemap.ee_export_image`` (getDownloadURL) usually fails. Default is
    ``ee.batch.Export.image.toDrive`` into a top-level Drive folder, then
    ``finalize_year_rasters`` copies into ``PHD/CSP3_GPP_outputs/rasters``
    and applies the corn mask with rasterio. HI / MC_AGB are never applied.
    """
    import ee

    seasonal, n_obs, profile, region = _prepare_seasonal_images(
        year, buffered_start, end_exclusive, aoi_path
    )
    _ = buffered_end  # kept in the signature for audit tables / callers

    sum_name = f"gpp_seasonal_sum_nonirr_corn_{year}.tif"
    nobs_name = f"gpp_nobs_nonirr_corn_{year}.tif"
    out_dir.mkdir(parents=True, exist_ok=True)
    sum_path = out_dir / sum_name
    nobs_path = out_dir / nobs_name
    crs_transform = affine_to_crs_transform(profile["transform"])

    if use_geemap:
        import geemap

        try:
            geemap.ee_export_image(
                seasonal,
                filename=str(sum_path),
                region=region,
                crs=AOI_CRS,
                crs_transform=crs_transform,
                file_per_band=False,
            )
            geemap.ee_export_image(
                n_obs,
                filename=str(nobs_path),
                region=region,
                crs=AOI_CRS,
                crs_transform=crs_transform,
                file_per_band=False,
            )
            apply_local_corn_mask(sum_path, nobs_path, aoi_path)
            zonal = zonal_from_raster(sum_path, nobs_path, aoi_path)
            zonal.update(
                {
                    "year": year,
                    "status": "ok",
                    "exported_via": "geemap.ee_export_image",
                    "sum_path": str(sum_path),
                    "nobs_path": str(nobs_path),
                    "aoi_path": str(aoi_path),
                    "hi_applied_to_gpp": False,
                    "mc_agb_applied_to_gpp": False,
                }
            )
            return zonal
        except Exception as exc:
            geemap_error = str(exc)
    else:
        geemap_error = None

    tasks = []
    for image, name in ((seasonal, sum_name), (n_obs, nobs_name)):
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=name.replace(".tif", "")[:100],
            folder=to_drive_folder,
            fileNamePrefix=name.replace(".tif", ""),
            region=region,
            crs=AOI_CRS,
            crsTransform=crs_transform,
            maxPixels=1e10,
            fileFormat="GeoTIFF",
        )
        task.start()
        status = task.status()
        tasks.append({"name": name, "id": status.get("id") or getattr(task, "id", None), "state": status.get("state")})
    return {
        "year": year,
        "status": "export_started_to_drive",
        "exported_via": "ee.batch.Export.image.toDrive",
        "to_drive_folder": to_drive_folder,
        "tasks": tasks,
        "sum_path": str(sum_path),
        "nobs_path": str(nobs_path),
        "aoi_path": str(aoi_path),
        "geemap_error": geemap_error,
        "hi_applied_to_gpp": False,
        "mc_agb_applied_to_gpp": False,
        "note": (
            "EE toDrive writes to a top-level My Drive folder named "
            f"{to_drive_folder}. Re-run finalize_year_rasters after COMPLETED."
        ),
    }


def drive_search_dirs(extra: list[Path] | None = None) -> list[Path]:
    dirs = [
        COLAB_RASTERS,
        COLAB_OUTPUTS,
        Path("/content/drive/MyDrive") / EE_DRIVE_FOLDER,
        Path("/content/drive/MyDrive") / EE_DRIVE_FOLDER / "rasters",
        Path("/content/drive/MyDrive/rasters"),
        COLAB_PHD / EE_DRIVE_FOLDER,
        COLAB_PHD / EE_DRIVE_FOLDER / "rasters",
    ]
    if extra:
        dirs.extend(extra)
    seen = []
    for d in dirs:
        if d not in seen:
            seen.append(d)
    return seen


def find_exported_tif(name: str, search_dirs: list[Path] | None = None) -> Path | None:
    for folder in search_dirs or drive_search_dirs():
        candidate = folder / name
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def finalize_year_rasters(
    year: int,
    aoi_path: Path,
    dest_dir: Path,
    search_dirs: list[Path] | None = None,
) -> dict:
    """Copy completed Drive GeoTIFFs into dest_dir, mask to corn, compute zonal stats."""
    import shutil

    sum_name = f"gpp_seasonal_sum_nonirr_corn_{year}.tif"
    nobs_name = f"gpp_nobs_nonirr_corn_{year}.tif"
    dest_dir.mkdir(parents=True, exist_ok=True)
    found_sum = find_exported_tif(sum_name, search_dirs)
    found_nobs = find_exported_tif(nobs_name, search_dirs)
    if found_sum is None or found_nobs is None:
        return {
            "year": year,
            "status": "waiting_for_drive_export",
            "sum_found": str(found_sum) if found_sum else None,
            "nobs_found": str(found_nobs) if found_nobs else None,
        }
    sum_path = dest_dir / sum_name
    nobs_path = dest_dir / nobs_name
    if found_sum.resolve() != sum_path.resolve():
        shutil.copy2(found_sum, sum_path)
    if found_nobs.resolve() != nobs_path.resolve():
        shutil.copy2(found_nobs, nobs_path)
    apply_local_corn_mask(sum_path, nobs_path, aoi_path)
    zonal = zonal_from_raster(sum_path, nobs_path, aoi_path)
    zonal.update(
        {
            "year": year,
            "status": "ok",
            "exported_via": "ee.batch.Export.image.toDrive+rasterio_mask",
            "sum_path": str(sum_path),
            "nobs_path": str(nobs_path),
            "aoi_path": str(aoi_path),
            "hi_applied_to_gpp": False,
            "mc_agb_applied_to_gpp": False,
        }
    )
    return zonal


def apply_local_corn_mask(sum_path: Path, nobs_path: Path, aoi_path: Path) -> None:
    import rasterio

    with rasterio.open(aoi_path) as aoi:
        corn = aoi.read(1)
        nodata = aoi.nodata if aoi.nodata is not None else AOI_NODATA
        mask = (corn != nodata) & (corn > 0)
        profile = aoi.profile.copy()
        aoi_crs = aoi.crs

    for path, band_nodata in ((sum_path, np.nan), (nobs_path, 0)):
        with rasterio.open(path) as src:
            arr = src.read(1)
            src_profile = src.profile.copy()
            if src.width != profile["width"] or src.height != profile["height"]:
                raise AssertionError(
                    f"{path} grid {src.width}x{src.height} != AOI "
                    f"{profile['width']}x{profile['height']}"
                )
            if src.crs and aoi_crs and src.crs != aoi_crs:
                raise AssertionError(f"{path} CRS {src.crs} != AOI {aoi_crs}")
        out = np.where(mask, arr, band_nodata)
        src_profile.update(
            compress="LZW",
            nodata=np.nan if np.isnan(band_nodata) else band_nodata,
            dtype=out.dtype,
        )
        # keep float32 for GPP
        if path == sum_path:
            out = out.astype("float32")
            src_profile.update(dtype="float32", nodata=np.nan)
        else:
            out = np.where(mask, arr, 0).astype("int16")
            src_profile.update(dtype="int16", nodata=0)
        with rasterio.open(path, "w", **src_profile) as dst:
            dst.write(out, 1)
            dst.set_band_description(
                1, BAND_SEASON if path == sum_path else BAND_NOBS
            )


def zonal_from_raster(sum_path: Path, nobs_path: Path, aoi_path: Path) -> dict:
    import rasterio

    with rasterio.open(aoi_path) as aoi, rasterio.open(sum_path) as gpp, rasterio.open(nobs_path) as nobs:
        corn = aoi.read(1)
        nodata = aoi.nodata if aoi.nodata is not None else AOI_NODATA
        mask = (corn != nodata) & (corn > 0)
        g = gpp.read(1)
        n = nobs.read(1)
        valid = mask & np.isfinite(g)
        if valid.sum() == 0:
            raise AssertionError(f"{sum_path} has no finite GPP on corn pixels")
        return {
            "n_corn_pixels": int(mask.sum()),
            "n_gpp_pixels": int(valid.sum()),
            "gpp_mean": float(np.nanmean(g[valid])),
            "gpp_median": float(np.nanmedian(g[valid])),
            "gpp_min": float(np.nanmin(g[valid])),
            "gpp_max": float(np.nanmax(g[valid])),
            "nobs_mean": float(np.nanmean(n[mask])),
            "crs": str(gpp.crs),
            "width": gpp.width,
            "height": gpp.height,
            "transform_c": float(gpp.transform.c),
            "transform_f": float(gpp.transform.f),
        }


def sample_us_ne3(seasonal_image) -> float | None:
    import ee

    pt = ee.Geometry.Point([US_NE3_LON, US_NE3_LAT])
    val = seasonal_image.reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=pt,
        scale=AOI_RES_M,
    )
    info = val.getInfo()
    return info.get(BAND_SEASON)


def add_map_layers(year: int, seasonal, aoi_path: Path | None = None):
    """Optional geemap.Map for one year: corn AOI, seasonal GPP, US-Ne3 marker."""
    import ee
    import geemap

    Map = geemap.Map()
    Map.setCenter(US_NE3_LON, US_NE3_LAT, 8)
    vis = {"min": 0, "max": 2, "palette": ["#f7fcf5", "#00441b"]}
    Map.addLayer(seasonal, vis, f"GPP seasonal {year}")
    Map.addLayer(
        ee.Geometry.Point([US_NE3_LON, US_NE3_LAT]),
        {"color": "red"},
        "US-Ne3 / CSP3",
    )
    if aoi_path is not None:
        try:
            Map.add_raster(str(aoi_path), layer_name=f"non_irrigated_corn {year}")
        except Exception:
            pass
    return Map

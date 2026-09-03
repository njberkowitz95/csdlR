"""Audit tables: missing data, growing-season windows, parameter audit, GPP zonal placeholders."""

from __future__ import annotations

import json
from pathlib import Path

from aoi import count_corn_pixels
from config import (
    AOI_YEARS,
    DO_NOT_JOIN,
    GPP_COLLECTION,
    GPP_MAX_YEAR,
    GPP_SCALE,
    US_NE3_LAT,
    US_NE3_LON,
)
from discover_workbooks import soybean_audit_rows


def _iso(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def missing_data_table(ops_rows, phenology_rows, discovery, aoi_lookup) -> list[dict]:
    rows = []
    rows.extend(soybean_audit_rows(discovery))

    ops_by_year = {r["year"]: r for r in ops_rows}
    pheno_by_year = {r["year"]: r for r in phenology_rows}

    row_2014 = ops_by_year.get(2014)
    if row_2014 and not row_2014.get("ops_plant_date"):
        rows.append(
            {
                "year": 2014,
                "issue": "ops_plant_date_missing",
                "detail": (
                    "2014 PLANT is absent from site-history CSP3 (appendix has harvest "
                    "2014-10-07/08 only). Plant date is not filled from Field Activities Log."
                ),
                "workbook": row_2014.get("workbook"),
            }
        )

    if 2015 in ops_by_year and 2015 not in pheno_by_year:
        rows.append(
            {
                "year": 2015,
                "issue": "maize_biomass_workbook_missing",
                "detail": (
                    "2015 is maize in site-history but no CSP 2015 Site 3 workbook exists; "
                    "MC_AGB and HI are NA."
                ),
                "workbook": None,
            }
        )

    for rec in pheno_by_year.values():
        if rec.get("end_is_provisional"):
            rows.append(
                {
                    "year": rec["year"],
                    "issue": "provisional_end_stage",
                    "detail": (
                        f"{rec['end_stage']} on {rec['end_sheet']} is used as provisional_end_date; "
                        "it is not labeled R6 or replaced with harvest."
                    ),
                    "workbook": rec.get("workbook"),
                }
            )
        if rec.get("hi") is None:
            rows.append(
                {
                    "year": rec["year"],
                    "issue": "hi_na",
                    "detail": (
                        f"HI is NA ({rec.get('hi_status')}). Yield shapefiles and S8 are not joined."
                    ),
                    "workbook": rec.get("workbook"),
                }
            )

    for year in (2019, 2021):
        aoi = aoi_lookup.get(year) or {"status": "aoi_raster_missing"}
        rows.append(
            {
                "year": year,
                "issue": "aoi_raster_missing",
                "detail": (
                    "No non_irrigated_corn GeoTIFF for this year. "
                    "2017 is not reused. Phenology/MC tables are still produced."
                ),
                "workbook": None,
                "aoi_status": aoi.get("status"),
            }
        )

    for item in DO_NOT_JOIN:
        rows.append(
            {
                "year": None,
                "issue": "source_not_joined",
                "detail": f"Explicitly not joined: {item}",
                "workbook": item if item.endswith(".xlsx") or item.endswith(".csv") else None,
            }
        )
    return rows


def maize_growing_season(ops_rows, phenology_rows, aoi_lookup) -> list[dict]:
    out = []
    for rec in ops_rows:
        if rec.get("crop") != "maize":
            continue
        year = rec["year"]
        aoi = aoi_lookup.get(year, {})
        has_aoi_year = year in AOI_YEARS
        raster = bool(has_aoi_year and rec.get("ops_plant_date") and rec.get("ops_harvest_date"))
        out.append(
            {
                "year": year,
                "crop": "maize",
                "window_type": "ops_plant_harvest",
                "start_date": rec.get("ops_plant_date"),
                "end_date": rec.get("ops_harvest_date"),
                "end_stage": "HARVEST",
                "end_is_provisional": False,
                "buffered_start": rec.get("buffered_start"),
                "buffered_end": rec.get("buffered_end"),
                "gee_filter_end_exclusive": rec.get("gee_filter_end_exclusive"),
                "used_for_regional_gpp_raster": raster,
                "aoi_year_available": has_aoi_year,
                "aoi_status": aoi.get("status"),
                "source_workbook": rec.get("workbook"),
                "source_sheet": rec.get("sheet"),
                "notes": "Regional GPP rasters use this window for 2001-2017 maize with an AOI GeoTIFF.",
            }
        )
    for rec in phenology_rows:
        year = rec["year"]
        out.append(
            {
                "year": year,
                "crop": "maize",
                "window_type": "phenology_rstage",
                "start_date": rec.get("planting_date"),
                "end_date": rec.get("sampling_date"),
                "end_stage": rec.get("end_stage"),
                "end_is_provisional": rec.get("end_is_provisional"),
                "buffered_start": rec.get("buffered_start"),
                "buffered_end": rec.get("buffered_end"),
                "gee_filter_end_exclusive": rec.get("gee_filter_end_exclusive"),
                "used_for_regional_gpp_raster": False,
                "aoi_year_available": year in AOI_YEARS,
                "aoi_status": aoi_lookup.get(year, {}).get("status"),
                "source_workbook": rec.get("workbook"),
                "source_sheet": rec.get("end_sheet"),
                "notes": (
                    "Attached as phenology attributes for 2013/2017; "
                    "not mixed into the ops-window GeoTIFF. Never replace R6 with harvest."
                ),
            }
        )
    return out


def parameter_audit(discovery, ops_rows, phenology_rows) -> list[dict]:
    rows = []
    for rec in discovery:
        if rec.get("role") != "annual_site3":
            continue
        rows.append(
            {
                "year": rec.get("year"),
                "section": "workbook_discovery",
                "workbook": rec.get("filename"),
                "a1_crop": rec.get("a1_crop"),
                "a1_raw": rec.get("a1_raw"),
                "a1_sheet": rec.get("a1_sheet"),
                "drive_id": rec.get("drive_id"),
                "top_level": rec.get("top_level"),
                "preferred": rec.get("preferred"),
                "path": rec.get("path"),
                "note": rec.get("note"),
            }
        )
    for rec in ops_rows:
        rows.append(
            {
                "year": rec["year"],
                "section": "ops_plant_harvest",
                "crop": rec.get("crop"),
                "crop_source": rec.get("crop_source"),
                "workbook": rec.get("workbook"),
                "sheet": rec.get("sheet"),
                "plant_date": rec.get("ops_plant_date"),
                "plant_cell": rec.get("plant_cell"),
                "plant_header": "DATE / ACTIVITY=PLANT (or appendix title Plant)",
                "harvest_date": rec.get("ops_harvest_date"),
                "harvest_cell": rec.get("harvest_cell"),
                "skipped_plants": json.dumps(rec.get("skipped_plants") or []),
            }
        )
    for rec in phenology_rows:
        rows.append(
            {
                "year": rec["year"],
                "section": "phenology_mc_hi",
                "crop": "maize",
                "workbook": rec.get("workbook"),
                "sheet": rec.get("end_sheet"),
                "planting_doy": rec.get("planting_doy"),
                "planting_date": rec.get("planting_date"),
                "planting_header": rec.get("planting_doy_header"),
                "planting_cell": rec.get("planting_doy_cell"),
                "sampling_date": rec.get("sampling_date"),
                "sampling_header": rec.get("sampling_date_header"),
                "sampling_cell": rec.get("sampling_date_cell"),
                "end_stage": rec.get("end_stage"),
                "end_is_provisional": rec.get("end_is_provisional"),
                "mc_agb": rec.get("mc_agb"),
                "mc_header": rec.get("mc_header") or rec.get("mc_mc_header"),
                "mc_cell": rec.get("mc_cell"),
                "fresh_agb_kg_ha": rec.get("fresh_agb_kg_ha") or rec.get("mc_fresh_agb_kg_ha"),
                "dry_agb_kg_ha": rec.get("dry_agb_kg_ha") or rec.get("mc_dry_agb_kg_ha"),
                "dry_repro_kg_ha": rec.get("dry_repro_kg_ha") or rec.get("mc_dry_repro_kg_ha"),
                "hi": rec.get("hi"),
                "hi_method": rec.get("hi_method"),
                "hi_status": rec.get("hi_status"),
                "hi_header": rec.get("hi_header") or rec.get("weight_header"),
                "kernel_g": rec.get("kernel_g"),
                "subsample_g": rec.get("subsample_g"),
                "kernel_cell": rec.get("kernel_cell"),
                "subsample_cell": rec.get("subsample_cell"),
                "kernel_fraction": rec.get("kernel_fraction"),
            }
        )
    return rows


def gpp_zonal_placeholder(ops_rows, aoi_lookup, gee_ok: bool, gee_error: str | None) -> list[dict]:
    rows = []
    for rec in ops_rows:
        year = rec["year"]
        maize = rec.get("crop") == "maize"
        in_aoi = year in AOI_YEARS
        aoi = aoi_lookup.get(year, {})
        n_corn = None
        if aoi.get("path"):
            try:
                n_corn = count_corn_pixels(Path(aoi["path"]))
            except Exception:
                n_corn = None
        status = "skipped_not_maize"
        if maize and not in_aoi:
            status = "aoi_raster_missing"
        elif maize and in_aoi and not rec.get("ops_plant_date"):
            status = "ops_plant_date_missing"
        elif maize and in_aoi and year > GPP_MAX_YEAR:
            status = "gpp_collection_year_not_used"
        elif maize and in_aoi:
            status = "ok" if gee_ok and aoi.get("path") else (
                "aoi_file_not_in_local_cache" if not aoi.get("path") else "gee_auth_missing"
            )
        rows.append(
            {
                "year": year,
                "crop": rec.get("crop"),
                "window_type": "ops_plant_harvest",
                "buffered_start": rec.get("buffered_start"),
                "buffered_end": rec.get("buffered_end"),
                "gee_filter_end_exclusive": rec.get("gee_filter_end_exclusive"),
                "gpp_collection": GPP_COLLECTION,
                "gpp_qc": "10,11",
                "gpp_scale": GPP_SCALE,
                "aoi_status": aoi.get("status"),
                "aoi_source": aoi.get("source"),
                "gpp_raster_status": status,
                "gpp_mean": None,
                "gpp_median": None,
                "n_corn_pixels": n_corn,
                "us_ne3_lat": US_NE3_LAT,
                "us_ne3_lon": US_NE3_LON,
                "us_ne3_gpp": None,
                "hi_applied_to_gpp": False,
                "mc_agb_applied_to_gpp": False,
                "gee_error": None if status == "skipped_not_maize" else gee_error,
                "output_sum_tif": (
                    f"gpp_seasonal_sum_nonirr_corn_{year}.tif"
                    if maize and in_aoi and rec.get("ops_plant_date")
                    else None
                ),
                "output_nobs_tif": (
                    f"gpp_nobs_nonirr_corn_{year}.tif"
                    if maize and in_aoi and rec.get("ops_plant_date")
                    else None
                ),
            }
        )
    return rows

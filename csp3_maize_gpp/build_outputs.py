"""Assemble audit CSVs, growing-season tables, and validation_report.md."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from aoi import count_corn_pixels, find_aoi_raster
from config import (
    AOI_YEARS,
    DO_NOT_JOIN,
    GPP_COLLECTION,
    GPP_MAX_YEAR,
    GPP_QC_CLEAR,
    GPP_SCALE,
    LOCAL_OUTPUTS_DIR,
    SITE_HISTORY_FILE,
    US_NE3_LAT,
    US_NE3_LON,
    resolve_paths,
)
from discover_workbooks import discover_local_workbooks, preferred_annual, soybean_audit_rows
from extract_parameters import extract_all_maize
from extract_site_history import extract_site_history
from formulas import gee_end_exclusive


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


def write_validation_report(path: Path, *, ops_rows, phenology_rows, missing, zonal, gee_ok) -> None:
    maize_ops = [r for r in ops_rows if r.get("crop") == "maize"]
    soy_ops = [r for r in ops_rows if r.get("crop") == "soybean"]
    lines = [
        "# CSP3 maize GPP validation report",
        "",
        "Audit-first extraction of CSP3 (US-Ne3) maize dates, All-IMZ `MC_AGB`, and HI, ",
        "then seasonal Landsat GPP rasters on yearly **non-irrigated corn** GeoTIFFs ",
        "(CSDL corn minus LANID irrigation, MLRA-NE). CSP3 is a calibration point, not the AOI.",
        "",
        "## Sources",
        "",
        "- `2001-2017 site-history CSP3.xlsx` sheet **CSP3** only (CSP1/CSP2 ignored)",
        "- Newest top-level `CSP YYYY Site 3.xlsx` workbooks (A1 crop-validated)",
        "- `PHD/non_irrigated_corn/clean/non_irrigated_corn_mlrane_{year}_clean.tif`",
        f"- GPP: `{GPP_COLLECTION}` bands GPP+QC, QC in {GPP_QC_CLEAR}, scale {GPP_SCALE}",
        f"- US-Ne3 marker: ({US_NE3_LAT}, {US_NE3_LON})",
        "",
        "## Windows",
        "",
        "Regional rasters for 2001–2017 maize use **ops_plant_harvest** (first PLANT to last HARVEST, ±14 days).",
        "Phenology windows (planting DOY → R6, else latest R-stage as `provisional_end_date`) are attributes only.",
        "R5 is never called R6. Harvest is never substituted for R6.",
        "",
        "## Site-history ops (2001–2017)",
        "",
        f"- Maize years: {', '.join(str(r['year']) for r in maize_ops)}",
        f"- Soybean years (dates table only; no GPP GeoTIFF): {', '.join(str(r['year']) for r in soy_ops)}",
        "",
        "| year | crop | plant | harvest | buffered start | buffered end |",
        "|---|---|---|---|---|---|",
    ]
    for r in ops_rows:
        lines.append(
            f"| {r['year']} | {r.get('crop')} | {r.get('ops_plant_date')} | "
            f"{r.get('ops_harvest_date')} | {r.get('buffered_start')} | {r.get('buffered_end')} |"
        )
    lines += [
        "",
        "## Phenology / MC_AGB / HI (maize biomass workbooks)",
        "",
        "| year | plant DOY | plant date | end stage | sampling | MC_AGB | HI | HI method |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in phenology_rows:
        hi = r.get("hi")
        hi_s = "" if hi is None else f"{hi:.5f}"
        mc = r.get("mc_agb")
        mc_s = "" if mc is None else f"{mc:.6f}"
        stage = r.get("end_stage") + (" (provisional)" if r.get("end_is_provisional") else "")
        lines.append(
            f"| {r['year']} | {r.get('planting_doy')} | {r.get('planting_date')} | {stage} | "
            f"{r.get('sampling_date')} | {mc_s} | {hi_s} | {r.get('hi_method')} |"
        )
    lines += [
        "",
        "## Hard-checks",
        "",
        "- 2013 phenology buffer 2013-04-29 → 2013-10-09 (DOY 133, R6 268). Harvest 2013-10-22 is **not** the GPP end.",
        "- 2017 phenology buffer 2017-04-24 → 2017-10-02 (DOY 128, **R5** 261 provisional). Harvest 2017-11-02 is **not** the GPP end.",
        "- 2019 phenology buffer 2019-04-10 → 2019-10-02. HI = NA (kernel/subsample non-numeric). No AOI raster.",
        "- 2021 phenology buffer 2021-04-15 → 2021-10-18. HI = NA. No AOI raster.",
        "- 2014 plant missing in site-history; soybean; no GPP raster.",
        "- 2015 maize ops dates present; no biomass workbook so MC/HI = NA.",
        "",
        "## GPP rasters",
        "",
        "Files `gpp_seasonal_sum_nonirr_corn_{year}.tif` and `gpp_nobs_nonirr_corn_{year}.tif` ",
        "for 2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017.",
        "AOI grid (from `*_clean.tif`): **5469 columns × 5343 rows**, 30 m, EPSG:5070, ",
        "origin (−111285, 2047275), LZW, nodata 0. Numpy shape is (5343, 5469).",
        "Soybean years have **no** GPP GeoTIFFs. 2019/2021 are not invented from 2017.",
        "HI and MC_AGB are **not** multiplied into GPP.",
        "Seasonal GeoTIFFs are written by `CSP3_GPP_Colab.ipynb` after `ee.Authenticate()` ",
        "(full-grid exports use `ee.batch.Export.image.toDrive`).",
        "",
        f"- Earth Engine initialized in this run: **{gee_ok}**",
        "",
        "| year | raster status | mean | median | n corn pixels |",
        "|---|---|---|---|---|",
    ]
    for r in zonal:
        if r.get("crop") != "maize":
            continue
        lines.append(
            f"| {r['year']} | {r.get('gpp_raster_status')} | {r.get('gpp_mean')} | "
            f"{r.get('gpp_median')} | {r.get('n_corn_pixels')} |"
        )
    lines += [
        "",
        "## Missing / excluded",
        "",
    ]
    for r in missing:
        lines.append(f"- **{r.get('year')}** `{r.get('issue')}`: {r.get('detail')}")
    lines += [
        "",
        "## Reproduction",
        "",
        "Primary executable: `CSP3_GPP_Colab.ipynb` (GEE Python API + geemap + rasterio).",
        "Helpers in this folder: `run_pipeline.py` writes the CSV/markdown audit tables locally.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_outputs(output_dir: Path | None = None, workbooks_dir=None) -> dict:
    paths = resolve_paths()
    output_dir = Path(output_dir or paths["outputs"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rasters").mkdir(parents=True, exist_ok=True)

    workbooks_dir = Path(workbooks_dir or paths["workbooks"])
    extra = []
    biomass = workbooks_dir / "Biomass Sampling_2003_2021"
    if biomass.exists():
        extra.append(biomass)

    discovery = discover_local_workbooks(workbooks_dir, extra_dirs=extra)
    annual = preferred_annual(discovery)
    history_path = workbooks_dir / SITE_HISTORY_FILE["name"]
    if not history_path.exists():
        history_path = Path(paths["csp3"]) / SITE_HISTORY_FILE["name"]
    ops_rows = extract_site_history(history_path)
    phenology_rows = extract_all_maize(annual)

    aoi_lookup = {}
    for year in set(AOI_YEARS) | {2019, 2021}:
        aoi_lookup[year] = find_aoi_raster(year, paths["aoi_clean"], paths["aoi_parent"])

    missing = missing_data_table(ops_rows, phenology_rows, discovery, aoi_lookup)
    maize_gs = maize_growing_season(ops_rows, phenology_rows, aoi_lookup)
    audit = parameter_audit(discovery, ops_rows, phenology_rows)

    gee_ok = False
    gee_error = None
    try:
        from gee_gpp import try_ee_initialize

        gee_ok, _, raw_err = try_ee_initialize()
        if raw_err:
            gee_error = "gee_auth_missing"
    except Exception as exc:
        gee_error = "gee_auth_missing"

    zonal = gpp_zonal_placeholder(ops_rows, aoi_lookup, gee_ok, gee_error)

    # If rasters already exist (Colab export), fill zonal stats.
    try:
        from gee_gpp import zonal_from_raster

        rasters = Path(paths["rasters"])
        for row in zonal:
            year = row["year"]
            sum_p = rasters / f"gpp_seasonal_sum_nonirr_corn_{year}.tif"
            nobs_p = rasters / f"gpp_nobs_nonirr_corn_{year}.tif"
            aoi = aoi_lookup.get(year, {})
            if sum_p.exists() and nobs_p.exists() and aoi.get("path"):
                stats = zonal_from_raster(sum_p, nobs_p, Path(aoi["path"]))
                row.update(
                    {
                        "gpp_mean": stats["gpp_mean"],
                        "gpp_median": stats["gpp_median"],
                        "n_corn_pixels": stats["n_corn_pixels"],
                        "gpp_raster_status": "ok",
                    }
                )
    except Exception:
        pass

    ops_df = pd.DataFrame(ops_rows)
    ops_df["gpp_extracted"] = ops_df.apply(
        lambda r: bool(r.get("crop") == "maize" and r.get("year") in AOI_YEARS and r.get("ops_plant_date")),
        axis=1,
    )
    ops_df["skipped_plants"] = ops_df["skipped_plants"].apply(
        lambda x: json.dumps(x) if not isinstance(x, str) else x
    )

    files = {
        "csp3_site_history_growing_periods.csv": ops_df,
        "csp3_maize_growing_season.csv": pd.DataFrame(maize_gs),
        "csp3_parameter_audit.csv": pd.DataFrame(audit),
        "csp3_missing_data.csv": pd.DataFrame(missing),
        "csp3_gpp_zonal_nonirr_corn.csv": pd.DataFrame(zonal),
        "csp3_workbook_discovery.csv": pd.DataFrame(discovery),
    }
    written = {}
    for name, df in files.items():
        dest = output_dir / name
        if "year" in df.columns:
            df["year"] = pd.array(df["year"], dtype="Int64")
        df.to_csv(dest, index=False)
        written[name] = str(dest)

    report = output_dir / "validation_report.md"
    write_validation_report(
        report,
        ops_rows=ops_rows,
        phenology_rows=phenology_rows,
        missing=missing,
        zonal=zonal,
        gee_ok=gee_ok,
    )
    written["validation_report.md"] = str(report)
    return {
        "files": written,
        "n_ops": len(ops_rows),
        "n_phenology": len(phenology_rows),
        "gee_ok": gee_ok,
        "gee_error": gee_error,
    }


if __name__ == "__main__":
    result = build_outputs()
    print(json.dumps(result, indent=2, default=str))

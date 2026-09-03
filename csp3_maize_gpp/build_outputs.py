"""Assemble audit CSVs, growing-season tables, and validation_report.md."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from aoi import find_aoi_raster
from config import AOI_YEARS, SITE_HISTORY_FILE, resolve_paths
from discover_workbooks import discover_local_workbooks, preferred_annual
from extract_parameters import extract_all_maize
from extract_site_history import extract_site_history
from output_tables import (
    gpp_zonal_placeholder,
    maize_growing_season,
    missing_data_table,
    parameter_audit,
)
from validation_report import write_validation_report


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

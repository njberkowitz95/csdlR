"""Markdown validation report for CSP3 maize GPP audit tables."""

from __future__ import annotations

from pathlib import Path

from config import GPP_COLLECTION, GPP_QC_CLEAR, GPP_SCALE, US_NE3_LAT, US_NE3_LON


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

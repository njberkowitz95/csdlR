# CSP3 maize GPP (Colab)

Audit-first maize growing-season dates, All-IMZ `MC_AGB`, and harvest index from CSP3 Site 3 workbooks, then seasonal Landsat GPP rasters on yearly **non-irrigated corn** GeoTIFFs (CSDL corn minus LANID irrigation, MLRA-NE).

Primary executable: [`CSP3_GPP_Colab.ipynb`](CSP3_GPP_Colab.ipynb) (Earth Engine Python API + geemap + rasterio).

Intended GitHub home: [`njberkowitz95/Yields-and-Fields-CH1`](https://github.com/njberkowitz95/Yields-and-Fields-CH1). Do not modify CSDL map-creation code if this package is still present in `csdlR`.

## Drive layout

| Folder | Id |
|---|---|
| PHD | `1v1BA59utUNTMyGrrE_ImLPLKwt6z1L1Q` |
| PHD/CSP3 | `11QTWHfMmIvRyzcbvLF1LQs39QwCttjmL` |
| PHD/non_irrigated_corn/clean | `1TWEl3i8iqjcHzefHrDZJznWsXra3qTBk` |
| PHD/CSP3_GPP_outputs | `1R1gslopQ3GqYHoZHAkFFVs6g0SBfizm1` |
| My Drive/GitHub/Yields-and-Fields-CH1/csp3_maize_gpp | `1xvLgtKILRyxdD2o1VpxL0VQEnbd_CIhp` |
| PHD/GitHub/Yields-and-Fields-CH1/csp3_maize_gpp | `1okbOVtNyvcMWpThzJN6QxVxt2dqfRfzM` |
| Colab Notebooks | `11sZmBqR8z01WKvb39HqIG5v_eUPbBH16` |

Colab paths are `MyDrive/PHD/...` and `MyDrive/GitHub/Yields-and-Fields-CH1/csp3_maize_gpp/`. Site-history, biomass workbooks, and AOI GeoTIFFs are never overwritten.

## Rules that the code enforces

- Crop from cell **A1** (`CSP YYYY Maize` vs `Soybeans`). Soybean workbooks are audited, not used for MC/HI.
- Dates: `planting_date = Jan 1 + (planting_DOY - 1)`. End date is **R6** sampling; if no R6, latest R-stage is `provisional_end_date`. R5 is never called R6. Harvest is never substituted for R6.
- Ops window (2001–2017): first `PLANT` to last `HARVEST` on sheet **CSP3**, then ±14 days. GEE `filterDate` end is exclusive (`buffered_end + 1`).
- Regional GPP rasters use **ops_plant_harvest** for maize years that have an AOI GeoTIFF. Phenology dates are attributes only (2013/2017).
- `MC_AGB` is All-IMZ Mean of whole-plant moisture (not grain moisture). HI is dry grain / dry AGB, with kernel-partition fallback. 2019/2021 HI stay NA (S8 / yield shapefiles are not joined).
- GPP: `UMT/NTSG/v2/LANDSAT/GPP`, QC 10 and 11, scale 0.0001, no years after 2021. HI is **not** applied to GPP.
- Modeling surface is `non_irrigated_corn_mlrane_{year}_clean.tif` (**5469 × 5343** columns × rows, numpy shape (5343, 5469), 30 m, EPSG:5070, origin −111285 / 2047275). US-Ne3 (`41.1797, -96.4397`) is a calibration point. No AOI for 2019/2021 — do not reuse 2017.

## Local audit tables (no Earth Engine)

Workbooks are gitignored. With the xlsx files in `data/workbooks/`:

```bash
cd csp3_maize_gpp
python3 -m pytest tests -q
python3 run_pipeline.py
```

Writes `outputs/csp3_*.csv` and `outputs/validation_report.md`. GeoTIFF export requires Colab `ee.Authenticate()`; the full MLRA-NE grid is exported with `ee.batch.Export.image.toDrive` (then rasterio applies the corn mask).

## Outputs

1. `CSP3_GPP_Colab.ipynb`
2. `rasters/gpp_seasonal_sum_nonirr_corn_{year}.tif` and `gpp_nobs_nonirr_corn_{year}.tif` for 2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017
3. `csp3_parameter_audit.csv`
4. `csp3_site_history_growing_periods.csv`
5. `csp3_maize_growing_season.csv`
6. `csp3_missing_data.csv`
7. `csp3_gpp_zonal_nonirr_corn.csv`
8. `validation_report.md`

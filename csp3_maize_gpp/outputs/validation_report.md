# CSP3 maize GPP validation report

Audit-first extraction of CSP3 (US-Ne3) maize dates, All-IMZ `MC_AGB`, and HI, 
then seasonal Landsat GPP rasters on yearly **non-irrigated corn** GeoTIFFs 
(CSDL corn minus LANID irrigation, MLRA-NE). CSP3 is a calibration point, not the AOI.

## Sources

- `2001-2017 site-history CSP3.xlsx` sheet **CSP3** only (CSP1/CSP2 ignored)
- Newest top-level `CSP YYYY Site 3.xlsx` workbooks (A1 crop-validated)
- `PHD/non_irrigated_corn/clean/non_irrigated_corn_mlrane_{year}_clean.tif`
- GPP: `UMT/NTSG/v2/LANDSAT/GPP` bands GPP+QC, QC in (10, 11), scale 0.0001
- US-Ne3 marker: (41.1797, -96.4397)

## Windows

Regional rasters for 2001–2017 maize use **ops_plant_harvest** (first PLANT to last HARVEST, ±14 days).
Phenology windows (planting DOY → R6, else latest R-stage as `provisional_end_date`) are attributes only.
R5 is never called R6. Harvest is never substituted for R6.

## Site-history ops (2001–2017)

- Maize years: 2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017
- Soybean years (dates table only; no GPP GeoTIFF): 2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016

| year | crop | plant | harvest | buffered start | buffered end |
|---|---|---|---|---|---|
| 2001 | maize | 2001-05-14 | 2001-10-29 | 2001-04-30 | 2001-11-12 |
| 2002 | soybean | 2002-05-20 | 2002-10-11 | 2002-05-06 | 2002-10-25 |
| 2003 | maize | 2003-05-13 | 2003-10-16 | 2003-04-29 | 2003-10-30 |
| 2004 | soybean | 2004-06-02 | 2004-10-12 | 2004-05-19 | 2004-10-26 |
| 2005 | maize | 2005-04-26 | 2005-10-18 | 2005-04-12 | 2005-11-01 |
| 2006 | soybean | 2006-05-11 | 2006-10-14 | 2006-04-27 | 2006-10-28 |
| 2007 | maize | 2007-05-02 | 2007-11-01 | 2007-04-18 | 2007-11-15 |
| 2008 | soybean | 2008-05-13 | 2008-10-09 | 2008-04-29 | 2008-10-23 |
| 2009 | maize | 2009-04-22 | 2009-11-11 | 2009-04-08 | 2009-11-25 |
| 2010 | soybean | 2010-05-19 | 2010-10-06 | 2010-05-05 | 2010-10-20 |
| 2011 | maize | 2011-05-02 | 2011-10-18 | 2011-04-18 | 2011-11-01 |
| 2012 | soybean | 2012-05-15 | 2012-10-01 | 2012-05-01 | 2012-10-15 |
| 2013 | maize | 2013-05-13 | 2013-10-22 | 2013-04-29 | 2013-11-05 |
| 2014 | soybean | None | 2014-10-08 | None | None |
| 2015 | maize | 2015-04-30 | 2015-10-29 | 2015-04-16 | 2015-11-12 |
| 2016 | soybean | 2016-05-20 | 2016-10-21 | 2016-05-06 | 2016-11-04 |
| 2017 | maize | 2017-05-08 | 2017-11-02 | 2017-04-24 | 2017-11-16 |

## Phenology / MC_AGB / HI (maize biomass workbooks)

| year | plant DOY | plant date | end stage | sampling | MC_AGB | HI | HI method |
|---|---|---|---|---|---|---|---|
| 2013 | 133 | 2013-05-13 | R6 | 2013-09-25 | 0.474320 | 0.55639 | partition-derived |
| 2017 | 128 | 2017-05-08 | R5 (provisional) | 2017-09-18 | 0.589313 | 0.53254 | partition-derived |
| 2019 | 114 | 2019-04-24 | R6 | 2019-09-18 | 0.504555 |  | None |
| 2021 | 119 | 2021-04-29 | R6 | 2021-10-04 | 0.470629 |  | None |

## Hard-checks

- 2013 phenology buffer 2013-04-29 → 2013-10-09 (DOY 133, R6 268). Harvest 2013-10-22 is **not** the GPP end.
- 2017 phenology buffer 2017-04-24 → 2017-10-02 (DOY 128, **R5** 261 provisional). Harvest 2017-11-02 is **not** the GPP end.
- 2019 phenology buffer 2019-04-10 → 2019-10-02. HI = NA (kernel/subsample non-numeric). No AOI raster.
- 2021 phenology buffer 2021-04-15 → 2021-10-18. HI = NA. No AOI raster.
- 2014 plant missing in site-history; soybean; no GPP raster.
- 2015 maize ops dates present; no biomass workbook so MC/HI = NA.

## GPP rasters

Files `gpp_seasonal_sum_nonirr_corn_{year}.tif` and `gpp_nobs_nonirr_corn_{year}.tif` 
for 2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017.
Soybean years have **no** GPP GeoTIFFs. 2019/2021 are not invented from 2017.
HI and MC_AGB are **not** multiplied into GPP.

- Earth Engine initialized in this run: **False**

| year | raster status | mean | median | n corn pixels |
|---|---|---|---|---|
| 2001 | aoi_file_not_in_local_cache | None | None | None |
| 2003 | aoi_file_not_in_local_cache | None | None | None |
| 2005 | aoi_file_not_in_local_cache | None | None | None |
| 2007 | aoi_file_not_in_local_cache | None | None | None |
| 2009 | aoi_file_not_in_local_cache | None | None | None |
| 2011 | aoi_file_not_in_local_cache | None | None | None |
| 2013 | aoi_file_not_in_local_cache | None | None | None |
| 2015 | aoi_file_not_in_local_cache | None | None | None |
| 2017 | aoi_file_not_in_local_cache | None | None | None |

## Missing / excluded

- **2014** `soybean_biomass_workbook_excluded`: A1='CSP 2014 Soybeans' on V2 (162); MC_AGB and HI are not computed from soybean workbooks
- **2016** `soybean_biomass_workbook_excluded`: A1='CSP 2016 Soybeans' on V2 (166); MC_AGB and HI are not computed from soybean workbooks
- **2018** `soybean_biomass_workbook_excluded`: A1='CSP 2018 Soybeans' on V2 (158); MC_AGB and HI are not computed from soybean workbooks
- **2020** `soybean_biomass_workbook_excluded`: A1='CSP 2020 Soybeans' on V1 (157); MC_AGB and HI are not computed from soybean workbooks
- **2014** `ops_plant_date_missing`: 2014 PLANT is absent from site-history CSP3 (appendix has harvest 2014-10-07/08 only). Plant date is not filled from Field Activities Log.
- **2015** `maize_biomass_workbook_missing`: 2015 is maize in site-history but no CSP 2015 Site 3 workbook exists; MC_AGB and HI are NA.
- **2017** `provisional_end_stage`: R5 on R5 (261) is used as provisional_end_date; it is not labeled R6 or replaced with harvest.
- **2019** `hi_na`: HI is NA (kernel_or_subsample_nonnumeric). Yield shapefiles and S8 are not joined.
- **2021** `hi_na`: HI is NA (kernel_or_subsample_nonnumeric). Yield shapefiles and S8 are not joined.
- **2019** `aoi_raster_missing`: No non_irrigated_corn GeoTIFF for this year. 2017 is not reused. Phenology/MC tables are still produced.
- **2021** `aoi_raster_missing`: No non_irrigated_corn GeoTIFF for this year. 2017 is not reused. Phenology/MC tables are still produced.
- **None** `source_not_joined`: Explicitly not joined: S8_CSP3_Geophysics_Yield_Data_20221005.xlsx
- **None** `source_not_joined`: Explicitly not joined: yield shapefiles
- **None** `source_not_joined`: Explicitly not joined: Field Activities Log 2014 to 2021.csv

## Reproduction

Primary executable: `CSP3_GPP_Colab.ipynb` (GEE Python API + geemap + rasterio).
Helpers in this folder: `run_pipeline.py` writes the CSV/markdown audit tables locally.

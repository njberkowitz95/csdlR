Seasonal GPP GeoTIFFs are written here by `CSP3_GPP_Colab.ipynb` after `ee.Authenticate()`.

Filenames (maize years with an AOI mask only):

- `gpp_seasonal_sum_nonirr_corn_{year}.tif` — sum of QC 10/11 Landsat GPP × 0.0001
- `gpp_nobs_nonirr_corn_{year}.tif` — count of unmasked 16-day observations

Years: 2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017.

The full MLRA-NE grid is ~29 million pixels, so Colab uses `ee.batch.Export.image.toDrive` into a top-level Drive folder named `CSP3_GPP_outputs`, then copies into `PHD/CSP3_GPP_outputs/rasters` and applies the yearly corn mask with rasterio. HI and `MC_AGB` are never written into these rasters. Soybean years and 2019/2021 have no files here.

"""AOI GeoTIFF grid must match the Drive clean masks (not the swapped plan listing)."""

from pathlib import Path

import pytest

from aoi import assert_aoi_grid, count_corn_pixels, read_aoi_profile
from config import AOI_HEIGHT, AOI_ORIGIN_X, AOI_ORIGIN_Y, AOI_WIDTH, LOCAL_AOI_DIR

AOI_2013 = LOCAL_AOI_DIR / "non_irrigated_corn_mlrane_2013_clean.tif"


def test_config_width_is_columns_not_numpy_shape():
    # rasterio width (columns) x height (rows). Numpy shape is (5343, 5469).
    assert AOI_WIDTH == 5469
    assert AOI_HEIGHT == 5343
    assert AOI_ORIGIN_X == -111285.0
    assert AOI_ORIGIN_Y == 2047275.0


@pytest.mark.skipif(not AOI_2013.exists(), reason="2013 clean AOI tif not cached")
def test_clean_tif_matches_config_grid():
    profile = read_aoi_profile(AOI_2013)
    assert_aoi_grid(profile, AOI_2013)
    n = count_corn_pixels(AOI_2013)
    assert n > 0
    assert n == 3553355

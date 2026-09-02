"""Drive IDs, AOI years, phenology checkpoints, and path helpers for CSP3 GPP."""

from __future__ import annotations

from datetime import date
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
LOCAL_WORKBOOKS_DIR = PACKAGE_DIR / "data" / "workbooks"
LOCAL_AOI_DIR = PACKAGE_DIR / "data" / "aoi"
LOCAL_OUTPUTS_DIR = PACKAGE_DIR / "outputs"
LOCAL_RASTERS_DIR = LOCAL_OUTPUTS_DIR / "rasters"

# Earth Engine project id. Set in Colab before ee.Initialize, or export EE_PROJECT.
EE_PROJECT = None
GPP_COLLECTION = "UMT/NTSG/v2/LANDSAT/GPP"
GPP_SCALE = 0.0001
GPP_QC_CLEAR = (10, 11)
GPP_MAX_YEAR = 2021

BUFFER_DAYS = 14

US_NE3_LAT = 41.1797
US_NE3_LON = -96.4397
US_NE3_NAME = "US-Ne3 / CSP3"

# Yearly non-irrigated corn GeoTIFF grid (MLRA-NE).
AOI_WIDTH = 5343
AOI_HEIGHT = 5469
AOI_RES_M = 30
AOI_CRS = "EPSG:5070"
AOI_NODATA = 0
AOI_YEARS = (2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017)

DRIVE_FOLDERS = {
    "PHD": "1v1BA59utUNTMyGrrE_ImLPLKwt6z1L1Q",
    "CSP3": "11QTWHfMmIvRyzcbvLF1LQs39QwCttjmL",
    "non_irrigated_corn": "1mSZ9bWw00T-9bOgF6VTZePFk83EoX2H_",
    "non_irrigated_corn_clean": "1TWEl3i8iqjcHzefHrDZJznWsXra3qTBk",
    "CSP3_GPP_outputs": "1R1gslopQ3GqYHoZHAkFFVs6g0SBfizm1",
    "CSP3_GPP_outputs_rasters": "1OZuv5EO3rGGkXS5I7o9G6vhph-fAIsG0",
}

COLAB_PHD = Path("/content/drive/MyDrive/PHD")
COLAB_CSP3 = COLAB_PHD / "CSP3"
COLAB_AOI_CLEAN = COLAB_PHD / "non_irrigated_corn" / "clean"
COLAB_AOI_PARENT = COLAB_PHD / "non_irrigated_corn"
COLAB_OUTPUTS = COLAB_PHD / "CSP3_GPP_outputs"
COLAB_RASTERS = COLAB_OUTPUTS / "rasters"

SITE_HISTORY_FILE = {
    "name": "2001-2017 site-history CSP3.xlsx",
    "drive_id": "1teas5SssbwyocZ4ir1oOzqBaxq1Gd07p",
    "sheet": "CSP3",
}

# Newest top-level annual Site 3 workbooks. 2020 lives under Biomass Sampling_2003_2021.
ANNUAL_WORKBOOKS = {
    2013: {
        "name": "CSP 2013  Site 3.xlsx",
        "drive_id": "1o1jEUwhgxvEZCFp9df6YdfLPiP0x3RTE",
        "top_level": True,
    },
    2014: {
        "name": "CSP 2014   Site 3.xlsx",
        "drive_id": "1At4VG8SHThiNifvoHCwE3ToDtHsYVf3b",
        "top_level": True,
    },
    2016: {
        "name": "CSP 2016  Site 3.xlsx",
        "drive_id": "1x0ppGNKkQpkIWDbRUiDiJgd4QfWyRigk",
        "top_level": True,
    },
    2017: {
        "name": "CSP 2017  Site 3.xlsx",
        "drive_id": "1aaX9ZmT3D7wJpLiY74joEfiJlyHbV_zN",
        "top_level": True,
    },
    2018: {
        "name": "CSP 2018   Site 3.xlsx",
        "drive_id": "13nGp3YoerskCIGpi_EntZ9noB2-BEFWZ",
        "top_level": True,
    },
    2019: {
        "name": "CSP 2019  Site 3.xlsx",
        "drive_id": "1dhGjhl6ofHXrPw1FWreCO4ma9qLZEIzu",
        "top_level": True,
    },
    2020: {
        "name": "CSP 2020   Site 3.xlsx",
        "drive_id": "1hrLUTPUaEEE5W54XW4cHWiydf5yNwufT",
        "top_level": False,
        "note": "Not a PHD/CSP3 top-level file; copy under Biomass Sampling_2003_2021",
    },
    2021: {
        "name": "CSP 2021  Site 3.xlsx",
        "drive_id": "1OTyKtDRoTtzLBsjqxmOXBa-XDq9gddUt",
        "top_level": True,
    },
}

AOI_CLEAN_TIF = {
    2001: "1yjvh-F9KZ6i35Q68i-e6AhIbHUiEls2x",
    2003: "12hVAKvv2eeEJeC8rsf9WH8WR6Q26nvGh",
    2005: "1ZnsVdvIkM77c8e6STY5gYKjke16KfIs2",
    2007: "16gS39fsIYw_r7gJOl65UTvVS1RLvraEo",
    2009: "1O8wKrzXRfXsLFQSaYAzinsK5TE0uiCH4",
    2011: "1rNEr0JCd9vnrAH24NzRFU60jQc6TdxPp",
    2013: "1CIs4RbaAHKEIT1ZhXCxgVwlo99Icp4Qi",
    2015: "1wW9vmivUGOlEDcTnICKVk6jcyV5iPxI_",
    2017: "1pX3td3RjoN-x88SLzwUD2IRpNWMF5Ok-",
}

# Phenology / MC / HI hard-checks. Mismatch must stop the pipeline.
PHENOLOGY_CHECKPOINTS = {
    2013: {
        "planting_doy": 133,
        "end_stage": "R6",
        "end_is_provisional": False,
        "sampling_doy": 268,
        "buffered_start": date(2013, 4, 29),
        "buffered_end": date(2013, 10, 9),
        "mc_agb": 0.4743198165775913,
        "fresh_agb_kg_ha": 36898.46708036483,
        "dry_agb_kg_ha": 18447.11801329712,
        "hi": 0.5563912969247679,
        "hi_method": "partition-derived",
    },
    2017: {
        "planting_doy": 128,
        "end_stage": "R5",
        "end_is_provisional": True,
        "sampling_doy": 261,
        "buffered_start": date(2017, 4, 24),
        "buffered_end": date(2017, 10, 2),
        "mc_agb": 0.5893134166596617,
        "fresh_agb_kg_ha": 54413.32599898723,
        "dry_agb_kg_ha": 22201.86878326517,
        "hi": 0.5325425946283838,
        "hi_method": "partition-derived",
    },
    2019: {
        "planting_doy": 114,
        "end_stage": "R6",
        "end_is_provisional": False,
        "sampling_doy": 261,
        "buffered_start": date(2019, 4, 10),
        "buffered_end": date(2019, 10, 2),
        "mc_agb": 0.5045546473534683,
        "fresh_agb_kg_ha": 36199.82686684895,
        "dry_agb_kg_ha": 17814.238904671984,
        "hi": None,
        "hi_method": None,
    },
    2021: {
        "planting_doy": 119,
        "end_stage": "R6",
        "end_is_provisional": False,
        "sampling_doy": 277,
        "buffered_start": date(2021, 4, 15),
        "buffered_end": date(2021, 10, 18),
        "mc_agb": 0.4706287878627474,
        "fresh_agb_kg_ha": 39748.865328159365,
        "dry_agb_kg_ha": 20871.14956096837,
        "hi": None,
        "hi_method": None,
    },
}

OPS_CHECKPOINTS = {
    2001: {"crop": "maize", "plant": date(2001, 5, 14), "harvest": date(2001, 10, 29)},
    2002: {"crop": "soybean", "plant": date(2002, 5, 20), "harvest": date(2002, 10, 11)},
    2003: {"crop": "maize", "plant": date(2003, 5, 13), "harvest": date(2003, 10, 16)},
    2004: {"crop": "soybean", "plant": date(2004, 6, 2), "harvest": date(2004, 10, 12)},
    2005: {"crop": "maize", "plant": date(2005, 4, 26), "harvest": date(2005, 10, 18)},
    2006: {"crop": "soybean", "plant": date(2006, 5, 11), "harvest": date(2006, 10, 14)},
    2007: {"crop": "maize", "plant": date(2007, 5, 2), "harvest": date(2007, 11, 1)},
    2008: {"crop": "soybean", "plant": date(2008, 5, 13), "harvest": date(2008, 10, 9)},
    2009: {"crop": "maize", "plant": date(2009, 4, 22), "harvest": date(2009, 11, 11)},
    2010: {"crop": "soybean", "plant": date(2010, 5, 19), "harvest": date(2010, 10, 6)},
    2011: {"crop": "maize", "plant": date(2011, 5, 2), "harvest": date(2011, 10, 18)},
    2012: {"crop": "soybean", "plant": date(2012, 5, 15), "harvest": date(2012, 10, 1)},
    2013: {"crop": "maize", "plant": date(2013, 5, 13), "harvest": date(2013, 10, 22)},
    2014: {"crop": "soybean", "plant": None, "harvest": date(2014, 10, 8)},
    2015: {"crop": "maize", "plant": date(2015, 4, 30), "harvest": date(2015, 10, 29)},
    2016: {"crop": "soybean", "plant": date(2016, 5, 20), "harvest": date(2016, 10, 21)},
    2017: {"crop": "maize", "plant": date(2017, 5, 8), "harvest": date(2017, 11, 2)},
}

DO_NOT_JOIN = (
    "S8_CSP3_Geophysics_Yield_Data_20221005.xlsx",
    "yield shapefiles",
    "Field Activities Log 2014 to 2021.csv",
)


class CheckpointError(Exception):
    """Raised when a hard-check disagrees with a workbook cell."""

    def __init__(self, message: str, *, workbook=None, sheet=None, cell=None, value=None):
        parts = [message]
        if workbook:
            parts.append(f"workbook={workbook}")
        if sheet:
            parts.append(f"sheet={sheet}")
        if cell:
            parts.append(f"cell={cell}")
        if value is not None:
            parts.append(f"value={value!r}")
        super().__init__(" | ".join(parts))
        self.workbook = workbook
        self.sheet = sheet
        self.cell = cell
        self.value = value


def resolve_paths(drive_root: Path | None = None) -> dict:
    """Return workbook/AOI/output paths for Colab (Drive) or a local clone."""
    if drive_root is None and COLAB_PHD.exists():
        drive_root = COLAB_PHD
    if drive_root is not None:
        return {
            "mode": "colab",
            "phd": drive_root,
            "csp3": drive_root / "CSP3",
            "aoi_clean": drive_root / "non_irrigated_corn" / "clean",
            "aoi_parent": drive_root / "non_irrigated_corn",
            "outputs": drive_root / "CSP3_GPP_outputs",
            "rasters": drive_root / "CSP3_GPP_outputs" / "rasters",
            "workbooks": drive_root / "CSP3",
        }
    return {
        "mode": "local",
        "phd": None,
        "csp3": LOCAL_WORKBOOKS_DIR,
        "aoi_clean": LOCAL_AOI_DIR,
        "aoi_parent": LOCAL_AOI_DIR,
        "outputs": LOCAL_OUTPUTS_DIR,
        "rasters": LOCAL_RASTERS_DIR,
        "workbooks": LOCAL_WORKBOOKS_DIR,
    }

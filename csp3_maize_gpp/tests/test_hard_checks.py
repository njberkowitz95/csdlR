"""Integration hard-checks against cached Site 3 workbooks."""

from pathlib import Path

import pytest

from config import LOCAL_WORKBOOKS_DIR, PHENOLOGY_CHECKPOINTS, CheckpointError
from discover_workbooks import discover_local_workbooks, preferred_annual
from extract_parameters import extract_all_maize
from extract_site_history import extract_site_history, should_skip_plant

WORKBOOKS = LOCAL_WORKBOOKS_DIR
HISTORY = WORKBOOKS / "2001-2017 site-history CSP3.xlsx"


@pytest.mark.skipif(not HISTORY.exists(), reason="site-history xlsx not cached")
def test_site_history_ops_checkpoints():
    rows = extract_site_history(HISTORY)
    by_year = {r["year"]: r for r in rows}
    assert by_year[2013]["ops_harvest_date"] == "2013-10-22"
    assert by_year[2017]["ops_harvest_date"] == "2017-11-02"
    assert by_year[2014]["ops_plant_date"] is None
    assert by_year[2014]["crop"] == "soybean"
    maize = [r["year"] for r in rows if r["crop"] == "maize"]
    soy = [r["year"] for r in rows if r["crop"] == "soybean"]
    assert maize == [2001, 2003, 2005, 2007, 2009, 2011, 2013, 2015, 2017]
    assert soy == [2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016]


def test_skip_replant_and_preplant():
    assert should_skip_plant("Replant flooded areas", None)
    assert should_skip_plant("Preplant", None)
    assert should_skip_plant(None, "Complete Planting after rain delay")
    assert not should_skip_plant("Plant Corn", "Pioneer 1498AM")


@pytest.mark.skipif(not (WORKBOOKS / "CSP 2013  Site 3.xlsx").exists(), reason="xlsx not cached")
def test_maize_phenology_mc_hi_hard_checks():
    discovery = discover_local_workbooks(WORKBOOKS)
    annual = preferred_annual(discovery)
    rows = extract_all_maize(annual)
    by_year = {r["year"]: r for r in rows}
    assert set(by_year) >= {2013, 2017, 2019, 2021}

    r13 = by_year[2013]
    assert r13["end_stage"] == "R6"
    assert r13["end_is_provisional"] is False
    assert r13["sampling_date"] == "2013-09-25"
    assert r13["sampling_date"] != "2013-10-22"
    assert r13["hi_method"] == "partition-derived"

    r17 = by_year[2017]
    assert r17["end_stage"] == "R5"
    assert r17["end_is_provisional"] is True
    assert r17["sampling_date"] == "2017-09-18"
    assert r17["sampling_date"] != "2017-11-02"

    for year, exp in PHENOLOGY_CHECKPOINTS.items():
        got = by_year[year]
        assert got["planting_doy"] == exp["planting_doy"]
        assert got["end_stage"] == exp["end_stage"]
        if exp["hi"] is None:
            assert got["hi"] is None
        else:
            assert got["hi"] == pytest.approx(exp["hi"])

    soy_years = [rec["year"] for rec in annual.values() if rec.get("a1_crop") == "soybean"]
    assert 2014 in soy_years and 2016 in soy_years

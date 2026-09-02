"""Unit tests for date math, MC_AGB, and harvest index (no workbook I/O)."""

from datetime import date

import pytest

from formulas import (
    buffer_window,
    coerce_moisture_fraction,
    gee_end_exclusive,
    harvest_index_direct,
    harvest_index_partition,
    kernel_fraction,
    mc_agb,
    planting_date_from_doy,
)


def test_planting_date_from_doy():
    assert planting_date_from_doy(2013, 133) == date(2013, 5, 13)
    assert planting_date_from_doy(2017, 128) == date(2017, 5, 8)
    assert planting_date_from_doy(2019, 114) == date(2019, 4, 24)
    assert planting_date_from_doy(2021, 119) == date(2021, 4, 29)
    assert planting_date_from_doy(2013, 1) == date(2013, 1, 1)


def test_phenology_buffers_match_hard_checks():
    cases = [
        (2013, 133, 268, date(2013, 4, 29), date(2013, 10, 9)),
        (2017, 128, 261, date(2017, 4, 24), date(2017, 10, 2)),
        (2019, 114, 261, date(2019, 4, 10), date(2019, 10, 2)),
        (2021, 119, 277, date(2021, 4, 15), date(2021, 10, 18)),
    ]
    for year, p_doy, e_doy, b0, b1 in cases:
        start = planting_date_from_doy(year, p_doy)
        end = planting_date_from_doy(year, e_doy)
        buffered = buffer_window(start, end, 14)
        assert buffered == (b0, b1)
        assert gee_end_exclusive(b1).toordinal() == b1.toordinal() + 1


def test_mc_agb_formula_and_known_years():
    # Plant-level row where AH is exactly (Fresh-Dry)/Fresh (2013 R6 plant 1).
    assert mc_agb(45896.86319314339, 22113.29795187172) == pytest.approx(0.5181958762886597)
    # All-IMZ Mean of masses is NOT equal to All-IMZ Mean of moisture (mean of ratios).
    ratio_of_means = mc_agb(36898.46708036483, 18447.11801329712)
    assert ratio_of_means == pytest.approx(0.500057, rel=1e-5)
    assert ratio_of_means != pytest.approx(0.4743198165775913)
    assert coerce_moisture_fraction(47.43) == pytest.approx(0.4743)
    assert coerce_moisture_fraction(0.4743) == 0.4743
    with pytest.raises(ValueError):
        mc_agb(0, 1)
    with pytest.raises(ValueError):
        mc_agb(10, 11)


def test_partition_hi_2013_2017():
    hi13 = harvest_index_partition(12657.672093579358, 18447.11801329712, 1058.6, 1305.5)
    assert hi13["method"] == "partition-derived"
    assert hi13["kernel_fraction"] == pytest.approx(1058.6 / 1305.5)
    assert hi13["hi"] == pytest.approx(0.5563912969247679)
    hi17 = harvest_index_partition(14148.458287731257, 22201.86878326517, 1049.1, 1255.4)
    assert hi17["hi"] == pytest.approx(0.5325425946283838)
    assert harvest_index_direct(10, 20) == 0.5
    with pytest.raises(ValueError):
        kernel_fraction(10, 0)


def test_never_use_repro_share_as_hi():
    dry_repro, dry_agb = 12657.672093579358, 18447.11801329712
    repro_share = dry_repro / dry_agb
    hi = harvest_index_partition(dry_repro, dry_agb, 1058.6, 1305.5)["hi"]
    assert hi == pytest.approx(0.5563912969247679)
    assert abs(hi - repro_share) > 0.05
    assert hi < repro_share

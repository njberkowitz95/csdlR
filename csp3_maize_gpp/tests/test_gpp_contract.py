"""GPP helper contract: HI / MC_AGB must not enter the raster math."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gee_gpp_source_does_not_apply_hi_or_mc():
    text = (ROOT / "gee_gpp.py").read_text(encoding="utf-8")
    assert "multiply(GPP_SCALE)" in text or "GPP_SCALE" in text
    assert "QC" in text
    # HI and MC are documented as not applied; never multiplied into the image.
    assert "hi_applied_to_gpp" in text
    assert ".multiply(hi" not in text.lower()
    assert "mc_agb" not in text.lower() or "mc_agb_applied_to_gpp" in text
    assert "harvest_index" not in text.lower()

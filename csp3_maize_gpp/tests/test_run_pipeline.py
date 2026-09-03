"""CLI output-path helpers (no Earth Engine)."""

from pathlib import Path

from run_pipeline import raster_output_dir


def test_raster_output_dir_uses_rasters_subdir_when_outputs_set():
    default = Path("/tmp/csp3/outputs/rasters")
    assert raster_output_dir(None, default) == default
    assert raster_output_dir(Path("/tmp/custom_out"), default) == Path("/tmp/custom_out/rasters")

#!/usr/bin/env python3
"""Run CSP3 audit extraction (and GPP raster export when Earth Engine is authenticated)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from build_outputs import build_outputs
from config import AOI_YEARS, resolve_paths
from gee_gpp import export_year_rasters, try_ee_initialize


def raster_output_dir(outputs: Path | None, default_rasters: Path) -> Path:
    """GeoTIFFs go under ``rasters/``, matching Colab ``OUT/rasters``.

    If ``--outputs`` already names a ``rasters`` directory, use it as-is so
    callers do not get ``.../rasters/rasters``.
    """
    if outputs is None:
        return Path(default_rasters)
    out = Path(outputs)
    if out.name == "rasters":
        return out
    return out / "rasters"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, default=None)
    parser.add_argument("--export-rasters", action="store_true")
    parser.add_argument("--ee-project", default=None)
    args = parser.parse_args()

    result = build_outputs(args.outputs)
    print("Wrote audit tables:")
    for name, path in result["files"].items():
        print(f"  {name}: {path}")

    if not args.export_rasters:
        return 0

    ok, project, err = try_ee_initialize(args.ee_project)
    if not ok:
        print(f"Earth Engine not initialized ({err}). Skipping raster export.")
        print("Run CSP3_GPP_Colab.ipynb after ee.Authenticate() to write GeoTIFFs.")
        return 0

    import pandas as pd

    paths = resolve_paths()
    out_dir = raster_output_dir(args.outputs, paths["rasters"])
    out_dir.mkdir(parents=True, exist_ok=True)
    zonal_csv = Path(result["files"]["csp3_gpp_zonal_nonirr_corn.csv"])
    zonal = pd.read_csv(zonal_csv)
    from aoi import find_aoi_raster

    for _, row in zonal.iterrows():
        year = int(row["year"])
        if row.get("crop") != "maize" or year not in AOI_YEARS:
            continue
        if pd.isna(row.get("buffered_start")):
            continue
        aoi = find_aoi_raster(year, paths["aoi_clean"], paths["aoi_parent"])
        if not aoi.get("path"):
            print(f"{year}: AOI raster not local ({aoi.get('status')})")
            continue
        info = export_year_rasters(
            year,
            date.fromisoformat(str(row["buffered_start"])[:10]),
            date.fromisoformat(str(row["buffered_end"])[:10]),
            date.fromisoformat(str(row["gee_filter_end_exclusive"])[:10]),
            Path(aoi["path"]),
            out_dir,
        )
        print(year, info.get("status"), info.get("exported_via"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

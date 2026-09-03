"""Discover annual Site 3 workbooks and crop-validate cell A1."""

from __future__ import annotations

import re
from pathlib import Path

from openpyxl import load_workbook

from config import ANNUAL_WORKBOOKS, LOCAL_WORKBOOKS_DIR, SITE_HISTORY_FILE
from headers import normalize_header

YEAR_IN_NAME = re.compile(r"CSP\s+(20\d{2})", re.I)
CROP_IN_A1 = re.compile(r"\b(maize|soybeans?|corn)\b", re.I)


def parse_crop_from_a1(a1) -> tuple[str | None, str]:
    if a1 is None:
        return None, "A1 empty"
    text = str(a1)
    match = CROP_IN_A1.search(text)
    if not match:
        return None, f"A1 has no maize/soybean token: {text!r}"
    token = match.group(1).lower()
    if token.startswith("soy"):
        return "soybean", text
    return "maize", text


def is_stage_sheet_name(name: str) -> bool:
    return bool(re.match(r"^(V\d+|R\d+)\s*\(\d+\)\s*$", str(name).strip(), re.I))


def iter_candidate_xlsx(workbooks_dir: Path):
    for path in sorted(workbooks_dir.glob("*.xlsx")):
        if path.name.startswith("~$"):
            continue
        yield path


def discover_local_workbooks(workbooks_dir: Path | None = None, extra_dirs=None) -> list[dict]:
    workbooks_dir = workbooks_dir or LOCAL_WORKBOOKS_DIR
    search_dirs = [workbooks_dir]
    if extra_dirs:
        search_dirs.extend(extra_dirs)
    rows = []
    history = workbooks_dir / SITE_HISTORY_FILE["name"]
    if history.exists():
        rows.append(
            {
                "year": None,
                "role": "site_history",
                "path": str(history),
                "filename": history.name,
                "drive_id": SITE_HISTORY_FILE["drive_id"],
                "top_level": True,
                "a1_crop": None,
                "a1_raw": None,
                "a1_sheet": None,
                "preferred": True,
            }
        )

    found_years = set()
    seen_names = set()
    for search_dir in search_dirs:
        if search_dir is None or not Path(search_dir).exists():
            continue
        for path in iter_candidate_xlsx(Path(search_dir)):
            if path.name == SITE_HISTORY_FILE["name"] or path.name in seen_names:
                continue
            seen_names.add(path.name)
            year_match = YEAR_IN_NAME.search(path.name)
            if not year_match:
                continue
            year = int(year_match.group(1))
            meta = ANNUAL_WORKBOOKS.get(year, {})
            preferred_name = meta.get("name")
            preferred = preferred_name is None or path.name == preferred_name
            crop, a1_raw, a1_sheet = read_a1_crop(path)
            rows.append(
                {
                    "year": year,
                    "role": "annual_site3",
                    "path": str(path),
                    "filename": path.name,
                    "drive_id": meta.get("drive_id"),
                    "top_level": meta.get("top_level", True),
                    "a1_crop": crop,
                    "a1_raw": a1_raw,
                    "a1_sheet": a1_sheet,
                    "preferred": preferred,
                    "note": meta.get("note"),
                }
            )
            if preferred:
                found_years.add(year)

    for year, meta in ANNUAL_WORKBOOKS.items():
        if year not in found_years:
            rows.append(
                {
                    "year": year,
                    "role": "annual_site3",
                    "path": None,
                    "filename": meta["name"],
                    "drive_id": meta["drive_id"],
                    "top_level": meta.get("top_level", True),
                    "a1_crop": None,
                    "a1_raw": None,
                    "a1_sheet": None,
                    "preferred": True,
                    "note": "listed in config but not found locally",
                    "missing_local": True,
                }
            )
    return rows


def read_a1_crop(path: Path) -> tuple[str | None, str | None, str | None]:
    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        for name in wb.sheetnames:
            if not is_stage_sheet_name(name):
                continue
            ws = wb[name]
            a1 = ws["A1"].value
            crop, raw = parse_crop_from_a1(a1)
            return crop, (None if a1 is None else str(a1)), name
        # fall back to first sheet
        ws = wb[wb.sheetnames[0]]
        a1 = ws["A1"].value
        crop, raw = parse_crop_from_a1(a1)
        return crop, (None if a1 is None else str(a1)), wb.sheetnames[0]
    finally:
        wb.close()


def preferred_annual(records: list[dict]) -> dict[int, dict]:
    """Newest top-level (preferred) workbook per year."""
    out = {}
    for row in records:
        if row.get("role") != "annual_site3" or not row.get("preferred"):
            continue
        if row.get("path") is None:
            continue
        out[int(row["year"])] = row
    return out


def soybean_audit_rows(records: list[dict]) -> list[dict]:
    rows = []
    for year, rec in sorted(preferred_annual(records).items()):
        if rec.get("a1_crop") != "soybean":
            continue
        rows.append(
            {
                "year": year,
                "issue": "soybean_biomass_workbook_excluded",
                "detail": (
                    f"A1={rec.get('a1_raw')!r} on {rec.get('a1_sheet')}; "
                    "MC_AGB and HI are not computed from soybean workbooks"
                ),
                "workbook": rec.get("filename"),
                "a1_crop": rec.get("a1_crop"),
            }
        )
    return rows

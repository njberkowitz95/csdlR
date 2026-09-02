"""Date math, MC_AGB, and harvest-index formulas (no GPP conversion)."""

from __future__ import annotations

from datetime import date, timedelta


def planting_date_from_doy(year: int, doy: int) -> date:
    """planting_date = January 1 + (planting_DOY - 1)."""
    if doy < 1 or doy > 366:
        raise ValueError(f"DOY out of range: {doy}")
    return date(year, 1, 1) + timedelta(days=int(doy) - 1)


def doy_from_date(d: date) -> int:
    return (d - date(d.year, 1, 1)).days + 1


def buffer_window(start: date, end: date, days: int = 14) -> tuple[date, date]:
    return start - timedelta(days=days), end + timedelta(days=days)


def gee_end_exclusive(buffered_end: date) -> date:
    """Earth Engine filterDate end is exclusive: buffered_end + 1 day."""
    return buffered_end + timedelta(days=1)


def mc_agb(fresh, dry) -> float:
    """Whole-plant AGB moisture: (Fresh - Dry) / Fresh. Not grain moisture."""
    fresh = float(fresh)
    dry = float(dry)
    if fresh <= 0:
        raise ValueError("Fresh AGB must be > 0")
    if dry < 0 or dry > fresh:
        raise ValueError(f"Dry AGB {dry} is not in [0, Fresh={fresh}]")
    return (fresh - dry) / fresh


def coerce_moisture_fraction(value: float) -> float:
    """Workbook AH is usually a fraction; if stored as percent (>1), divide by 100."""
    value = float(value)
    if value > 1.0:
        return value / 100.0
    return value


def harvest_index_direct(dry_grain, dry_agb) -> float:
    """HI = dry grain / total dry AGB."""
    dry_grain = float(dry_grain)
    dry_agb = float(dry_agb)
    if dry_agb <= 0:
        raise ValueError("Dry AGB must be > 0")
    if dry_grain < 0:
        raise ValueError("Dry grain must be >= 0")
    return dry_grain / dry_agb


def kernel_fraction(kernel_g, subsample_g) -> float:
    kernel_g = float(kernel_g)
    subsample_g = float(subsample_g)
    if subsample_g <= 0:
        raise ValueError("Reproductive subsample weight must be > 0")
    if kernel_g < 0 or kernel_g > subsample_g * 1.01:
        raise ValueError(f"Kernel weight {kernel_g} vs subsample {subsample_g}")
    return kernel_g / subsample_g


def harvest_index_partition(dry_repro, dry_agb, kernel_g, subsample_g) -> dict:
    """Kernel-partition HI: (Dry Repro * kernel/subsample) / Dry AGB.

    Never use Pct. Biomass in Repro or Dry Repro/Dry AGB without the kernel fraction.
    """
    frac = kernel_fraction(kernel_g, subsample_g)
    dry_grain = float(dry_repro) * frac
    hi = harvest_index_direct(dry_grain, dry_agb)
    return {
        "kernel_fraction": frac,
        "dry_grain_kg_ha": dry_grain,
        "hi": hi,
        "method": "partition-derived",
    }

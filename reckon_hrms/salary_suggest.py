"""Salary band suggestions from the 2026 company payroll benchmark.

Pure data, no Frappe import, so the rules are unit-testable. Every answer carries the confidence,
the source basis and the caveat from the benchmark. A suggestion is never a guaranteed salary.
"""

from __future__ import annotations

import difflib
import json
from functools import lru_cache
from pathlib import Path

BENCHMARK_PATH = Path(__file__).with_name("benchmarks") / "payroll_benchmark_2026.json"

CAVEAT = ("Indicative market range, not a guaranteed salary or a legal reference. "
          "Calibrate with the company's own payroll data before any offer.")


@lru_cache(maxsize=1)
def load_benchmark(path: str = str(BENCHMARK_PATH)) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def segments(data: dict | None = None) -> list[dict]:
    data = data or load_benchmark()
    return [
        {"key": key, "label": seg["label"], "role_count": len(seg["roles"])}
        for key, seg in data["segments"].items()
    ]


def find_roles(segment: str, query: str, limit: int = 5, data: dict | None = None) -> list[dict]:
    """Roles in a segment whose names match the query: exact, then substring, then close spelling."""
    data = data or load_benchmark()
    seg = data["segments"].get(segment)
    if not seg or not query:
        return []
    needle = query.strip().lower()
    roles = seg["roles"]
    exact = [r for r in roles if r["role"].lower() == needle]
    contains = [r for r in roles if needle in r["role"].lower() and r not in exact]
    names = [r["role"] for r in roles]
    close = [r for r in roles if r["role"] in difflib.get_close_matches(query.strip(), names, n=limit, cutoff=0.6)
             and r not in exact and r not in contains]
    return (exact + contains + close)[:limit]


def position_in_band(gross: float, low: float, high: float) -> dict:
    """Where a current gross sits against the band. Below or above the band is reported, never capped."""
    if gross < low:
        return {"position": "below", "percent_into_band": None}
    if gross > high:
        return {"position": "above", "percent_into_band": None}
    span = high - low
    pct = round(100 * (gross - low) / span, 1) if span else 100.0
    return {"position": "within", "percent_into_band": pct}


def suggest(segment: str, role: str, current_gross: float | None = None, data: dict | None = None) -> dict:
    """Suggest a band for a role in a segment, with confidence and the nearest alternatives."""
    data = data or load_benchmark()
    if segment not in data["segments"]:
        return {"status": "unknown_segment", "caveat": CAVEAT}
    matches = find_roles(segment, role, data=data)
    if not matches:
        return {
            "status": "no_match",
            "message": "No benchmark for this role. Treat it as a research gap and use company data.",
            "caveat": CAVEAT,
        }
    chosen = matches[0]
    result = {
        "status": "matched",
        "segment": segment,
        "role": chosen["role"],
        "level": chosen["level"],
        "min": chosen["min"],
        "max": chosen["max"],
        "midpoint": chosen["midpoint"],
        "confidence": chosen["confidence"],
        "confidence_meaning": (
            "Medium: several current market sources agree." if chosen["confidence"] == "Medium"
            else "Low: sparse sample or broad estimate."
        ),
        "source_basis": chosen["source_basis"],
        "role_notes": chosen["notes"],
        "alternatives": [r["role"] for r in matches[1:]],
        "caveat": CAVEAT,
    }
    if current_gross is not None:
        result["current_gross"] = current_gross
        result.update(position_in_band(float(current_gross), chosen["min"], chosen["max"]))
    return result

"""Attendance-based deduction for late entry and early exit, as approved by HR.

Pure rules, no Frappe import, so they are unit-testable. A late entry or early exit on a day counts
as one mark for that day, even when both happen. Absent days are not counted here, because HRMS
already leaves them unpaid. Each day's pay is base salary divided by the company divisor, so a
deduction is always a visible amount, never a hidden cut.
"""

from __future__ import annotations

DEFAULT_MARKS_PER_DAY = 3
DEFAULT_DIVISOR = 30
DEFAULT_CAP = 0  # 0 means no cap


def marks_for_days(day_rows: list[dict]) -> int:
    """Count days with a late entry or early exit. Absent days are ignored.

    Each row: {"late_entry": bool, "early_exit": bool, "status": "Present" | "Half Day" | "Absent" | ...}.
    """
    marks = 0
    for row in day_rows:
        if row.get("status") == "Absent":
            continue
        if row.get("late_entry") or row.get("early_exit"):
            marks += 1
    return marks


def days_deducted(marks: int, marks_per_day: int = DEFAULT_MARKS_PER_DAY) -> int:
    """Whole days deducted: every ``marks_per_day`` marks equal one day. Partial groups count for nothing."""
    if marks_per_day <= 0:
        return 0
    return marks // marks_per_day


def deduction_amount(base: float, days: int, divisor: int = DEFAULT_DIVISOR, cap: float = DEFAULT_CAP) -> float:
    """Amount for the days, rounded to 2 places. Zero when there are no days or no base salary."""
    if days <= 0 or base <= 0 or divisor <= 0:
        return 0.0
    amount = round(base / divisor * days, 2)
    if cap and cap > 0:
        amount = min(amount, round(cap, 2))
    return amount

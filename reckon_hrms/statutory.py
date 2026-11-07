"""Statutory calculations for Bangladesh SME payroll: WPPF and gratuity. Pure Python.

Rates and rules follow the Bangladesh Labour Act 2006 (as amended) and the Companies/WPPF rules as
commonly applied. Each rate is a parameter so the HR owner can set it per company. These are not legal
or accounting advice; confirm with the company's auditor before a payout.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

WPPF_RATE = Decimal("0.05")          # 5% of gross profit to the Workers' Profit Participation Fund
WPPF_MIN_EMPLOYEES = 10              # the fund applies to establishments with 10 or more workers

# Gratuity: days of last basic wage per completed year of service. The Labour Act sets a shorter
# rate for the first 5 years and a longer one after; both are parameters here.
GRATUITY_MIN_YEARS = 1
GRATUITY_DAYS_FIRST_5 = Decimal("14")
GRATUITY_DAYS_AFTER_5 = Decimal("30")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def wppf_contribution(gross_profit, workers: int, rate: Decimal = WPPF_RATE) -> Decimal:
    """Annual WPPF contribution. Zero when the profit is negative or the establishment is too small."""
    if workers < WPPF_MIN_EMPLOYEES:
        return Decimal("0.00")
    profit = Decimal(str(gross_profit))
    if profit <= 0:
        return Decimal("0.00")
    return _money(profit * rate)


def gratuity(last_basic, years_of_service: Decimal | float | int) -> Decimal:
    """Gratuity payable for the completed years of service on the last basic wage."""
    years = int(Decimal(str(years_of_service)))  # completed years only
    if years < GRATUITY_MIN_YEARS:
        return Decimal("0.00")
    first = min(years, 5)
    after = max(0, years - 5)
    daily = Decimal(str(last_basic)) / Decimal("30")
    total = daily * (GRATUITY_DAYS_FIRST_5 * first + GRATUITY_DAYS_AFTER_5 * after)
    return _money(total)


def provident_fund(basic, employee_rate: Decimal = Decimal("0.05"), employer_rate: Decimal = Decimal("0.05")) -> dict:
    """Monthly PF contributions on basic pay. Employee and employer each contribute the rate."""
    base = Decimal(str(basic))
    return {"employee": _money(base * employee_rate), "employer": _money(base * employer_rate)}

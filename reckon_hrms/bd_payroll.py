"""Bangladesh SME payroll rules. Pure Python, no Frappe import, so the arithmetic is unit-testable.

These follow the commonly used rules for a small employer. Tax slabs and festival bonus rules change
by budget and by the Labour Act; the HR owner or accountant must confirm them before a payroll run.
They are not legal or tax advice.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# Individual income tax slabs (annual taxable income, rate). Tax-free band first, then each band.
TAX_FREE_LIMIT = Decimal("350000")
TAX_SLABS = (
    (Decimal("100000"), Decimal("0.05")),   # 350,001 - 450,000
    (Decimal("300000"), Decimal("0.10")),   # 450,001 - 750,000
    (Decimal("400000"), Decimal("0.15")),   # 750,001 - 1,150,000
    (Decimal("500000"), Decimal("0.20")),   # 1,150,001 - 1,650,000
    (None, Decimal("0.25")),                # above
)

FESTIVALS_PER_YEAR = 2  # Eid-ul-Fitr and Eid-ul-Adha
FULL_BONUS_MONTHS = 12  # one month's basic for a full year of service

# Bilingual labels for pay slips and reports (English, Bangla).
LABELS = {
    "Basic Salary": ("Basic Salary", "মূল বেতন"),
    "House Rent Allowance": ("House Rent", "বাড়ি ভাড়া"),
    "Medical Allowance": ("Medical", "চিকিৎসা ভাতা"),
    "Conveyance Allowance": ("Conveyance", "যাতায়াত ভাতা"),
    "Festival Bonus": ("Festival Bonus", "উৎসব বোনাস"),
    "Provident Fund (Employee)": ("Provident Fund", "ভবিষ্য তহবিল"),
    "Income Tax (TDS)": ("Income Tax (TDS)", "আয়কর (উৎসে)"),
    "Gross Pay": ("Gross Pay", "মোট আয়"),
    "Total Deduction": ("Total Deduction", "মোট কর্তন"),
    "Net Pay": ("Net Pay", "নিট বেতন"),
}

_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _money(value) -> Decimal:
    return _d(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def annual_tax(taxable: Decimal | float | int) -> Decimal:
    """Income tax on an annual taxable amount, using the slabs above."""
    income = _d(taxable)
    if income <= TAX_FREE_LIMIT:
        return Decimal("0")
    remaining = income - TAX_FREE_LIMIT
    tax = Decimal("0")
    for width, rate in TAX_SLABS:
        if width is None or remaining <= width:
            tax += remaining * rate
            break
        tax += width * rate
        remaining -= width
    return _money(tax)


def monthly_tds(gross_monthly, pf_employee_monthly=0) -> Decimal:
    """Monthly tax deduction at source. Employee provident fund is taken out of taxable income."""
    taxable_annual = (_d(gross_monthly) - _d(pf_employee_monthly)) * 12
    return _money(annual_tax(taxable_annual) / 12)


def festival_bonus(basic_monthly, months_in_service: int, festivals: int = FESTIVALS_PER_YEAR) -> Decimal:
    """Festival bonus per festival. One month's basic for a full year, pro rata under a year.

    Returns the amount for a single festival. Multiply by the festivals paid this year as needed.
    """
    months = max(0, min(int(months_in_service), FULL_BONUS_MONTHS))
    if festivals <= 0 or months == 0:
        return Decimal("0")
    per_festival = _d(basic_monthly) * months / FULL_BONUS_MONTHS / festivals
    return _money(per_festival)


def to_bangla_digits(value) -> str:
    return f"{_money(value):,.2f}".translate(_BN_DIGITS)


def bilingual(label: str) -> tuple[str, str]:
    return LABELS.get(label, (label, label))


def bank_sheet_rows(slips: list[dict]) -> list[list[str]]:
    """Rows for a bank transfer sheet: code, name, bank, account, net pay. slips are dicts."""
    header = ["Employee", "Name", "Bank", "Account", "Net Pay"]
    rows = [header]
    for s in slips:
        rows.append([
            str(s.get("employee", "")),
            str(s.get("employee_name", "")),
            str(s.get("bank_name") or ""),
            str(s.get("bank_ac_no") or ""),
            f"{_money(s.get('net_pay')):.2f}",
        ])
    return rows

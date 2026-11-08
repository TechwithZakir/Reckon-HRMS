"""Regenerate payroll_benchmark_2026.json from the ReckonERP Company Payroll Benchmark workbook.

Run offline by a developer (needs openpyxl; the app itself does not import it):

    python reckon_hrms/benchmarks/build_from_workbook.py path/to/ReckonERP_Bangladesh_Company_Payroll_Benchmark_2026.xlsx

Figures come straight from the "Role Benchmarks" sheet. Midpoints are recomputed and checked against
the workbook. Component, leave and department choices per segment are product assumptions, marked
as such in the output so a customer admin can confirm them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).with_name("payroll_benchmark_2026.json")

# Workbook industry label -> stable segment key used by the app.
SEGMENTS = {
    "IT / Software": "it_software",
    "Manufacturing / RMG / Textile": "manufacturing_rmg_textile",
    "Construction / Engineering": "construction_engineering",
    "Corporate / Finance": "corporate_finance",
    "Sales / Marketing": "sales_marketing",
    "Pharmaceuticals": "pharmaceuticals",
    "Trading / Distribution": "trading_distribution",
    "Healthcare": "healthcare",
    "Education / NGO / Services": "education_ngo_services",
    "Retail / Logistics": "retail_logistics",
}

# Earning components that suit each segment. Assumed from the Earning Components sheet's usage
# pattern; customers confirm or change them when they choose the segment.
COMPONENTS = {
    "it_software": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                    "Mobile Allowance", "Attendance Incentive", "Performance Bonus", "Festival Bonus", "Overtime"],
    "manufacturing_rmg_textile": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                                  "Meal Allowance", "Attendance Incentive", "Shift Allowance", "Festival Bonus", "Overtime"],
    "construction_engineering": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                                 "Meal Allowance", "Site Allowance", "Shift Allowance", "Festival Bonus", "Overtime"],
    "corporate_finance": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                          "Mobile Allowance", "Performance Bonus", "Festival Bonus", "Overtime"],
    "sales_marketing": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                        "Mobile Allowance", "Sales Commission", "Performance Bonus", "Festival Bonus"],
    "pharmaceuticals": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                        "Meal Allowance", "Sales Commission", "Performance Bonus", "Festival Bonus", "Overtime"],
    "trading_distribution": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                             "Meal Allowance", "Sales Commission", "Shift Allowance", "Festival Bonus", "Overtime"],
    "healthcare": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                   "Meal Allowance", "Shift Allowance", "Festival Bonus", "Overtime"],
    "education_ngo_services": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                               "Mobile Allowance", "Performance Bonus", "Festival Bonus"],
    "retail_logistics": ["Basic Salary", "House Rent Allowance", "Medical Allowance", "Conveyance Allowance",
                         "Meal Allowance", "Shift Allowance", "Attendance Incentive", "Festival Bonus", "Overtime"],
}

# Deduction masters every segment can use. Attendance-linked deductions are policy settings, not masters.
RECOVERY_DEDUCTIONS = ["Loan Recovery", "Salary Advance Recovery", "Other Adjustment"]

# Leave types by name. Entitlement days are not set here: the guide says leave rules are company-configured.
LEAVE_TYPES = ["Casual Leave", "Sick Leave", "Earned Leave", "Unpaid Leave", "Maternity Leave",
               "Compensatory Off"]

# Starter departments: a product assumption, not from the workbook.
DEPARTMENTS = {
    "it_software": ["Engineering", "Quality Assurance", "Product", "Support", "Sales", "Human Resources", "Finance"],
    "manufacturing_rmg_textile": ["Production", "Quality", "Merchandising", "Store", "Human Resources", "Accounts"],
    "construction_engineering": ["Project Management", "Site Operations", "Engineering", "Procurement", "Accounts",
                                 "Human Resources"],
    "corporate_finance": ["Finance", "Accounts", "Human Resources", "Operations", "Administration"],
    "sales_marketing": ["Sales", "Marketing", "Key Accounts", "Human Resources", "Accounts"],
    "pharmaceuticals": ["Production", "Quality Assurance", "Sales", "Regulatory", "Human Resources", "Accounts"],
    "trading_distribution": ["Sales and Distribution", "Warehouse", "Accounts", "Procurement", "Human Resources"],
    "healthcare": ["Clinical", "Administration", "Billing and Accounts", "Human Resources", "Support Services"],
    "education_ngo_services": ["Academic", "Programmes", "Administration", "Finance", "Human Resources"],
    "retail_logistics": ["Store Operations", "Logistics", "Warehouse", "Procurement", "Human Resources", "Accounts"],
}


def _number(value) -> int:
    return round(float(value))


def build(workbook_path: Path) -> dict:
    import openpyxl

    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    sheet = wb["Role Benchmarks"]
    header = [c.value for c in sheet[1]]
    index = {name: header.index(name) for name in header if name}
    roles_by_segment: dict[str, list[dict]] = {key: [] for key in SEGMENTS.values()}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row[index["Industry"]]:
            continue
        industry = row[index["Industry"]]
        key = SEGMENTS.get(industry)
        if not key:
            raise SystemExit(f"Unmapped industry in workbook: {industry}")
        low = _number(row[index["Gross Min BDT"]])
        high = _number(row[index["Gross Max BDT"]])
        mid = _number(row[index["Indicative Midpoint BDT"]])
        if (low + high) // 2 != mid and abs((low + high) / 2 - mid) > 1:
            raise SystemExit(f"Midpoint mismatch for {row[index['Role']]}: {mid} vs {(low + high) / 2}")
        roles_by_segment[key].append({
            "role": row[index["Role"]],
            "level": row[index["Level"]],
            "min": low,
            "max": high,
            "midpoint": mid,
            "confidence": row[index["Confidence"]],
            "source_basis": row[index["Source Basis"]],
            "notes": row[index["Notes"]],
        })

    segments = {}
    for label, key in SEGMENTS.items():
        segments[key] = {
            "label": label,
            "roles": roles_by_segment[key],
            "components": COMPONENTS[key],
            "recovery_deductions": RECOVERY_DEDUCTIONS,
            "leave_types": LEAVE_TYPES,
            "departments": DEPARTMENTS[key],
            "assumptions_note": "Components and departments are starter assumptions; the customer confirms them.",
        }
    total = sum(len(s["roles"]) for s in segments.values())
    return {
        "baseline": "2026-11-08",
        "currency": "BDT",
        "period": "monthly gross",
        "caveat": "Indicative market ranges, not a national average or legal reference. Validate with customer payroll data.",
        "role_count": total,
        "segments": segments,
    }


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    data = build(Path(argv[1]))
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} with {data['role_count']} roles in {len(data['segments'])} segments")


if __name__ == "__main__":
    main(sys.argv)

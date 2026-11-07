"""Tenant seed for Reckon HRMS.

The platform calls this once per tenant Company. It must add only generic,
non-sensitive defaults. It must never copy employees, salaries, attendance,
bank details or any other business data from another tenant.

This milestone seeds nothing yet. The defaults (leave types, shifts, salary
components) come with the Setup Wizard step.
"""

from __future__ import annotations


def run_hrms_seed(company: str, seed_version: str) -> dict:
    return {"company": company, "seed_version": seed_version, "seeded": []}

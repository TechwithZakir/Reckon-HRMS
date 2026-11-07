"""Payroll anomaly checks. Pure Python: each rule returns findings a payroll reviewer can act on.

Rules are deliberately simple and explainable. They flag for human review; they never change a slip.
"""

from __future__ import annotations

from decimal import Decimal

NET_JUMP_RATIO = Decimal("0.30")   # flag a net pay change of more than 30% against last month
TDS_TOLERANCE = Decimal("5")       # tax should match the calculated monthly TDS within 5 taka


def check_net_jump(current_net, previous_net) -> dict | None:
    cur, prev = Decimal(str(current_net)), Decimal(str(previous_net))
    if prev <= 0:
        return None
    change = abs(cur - prev) / prev
    if change > NET_JUMP_RATIO:
        return {"rule": "net_pay_jump", "severity": "high",
                "detail": f"Net pay moved {change * 100:.0f}% from last month."}
    return None


def check_tds(recorded_tds, expected_tds) -> dict | None:
    if abs(Decimal(str(recorded_tds)) - Decimal(str(expected_tds))) > TDS_TOLERANCE:
        return {"rule": "tds_mismatch", "severity": "high",
                "detail": f"TDS {recorded_tds} differs from the expected {expected_tds}."}
    return None


def check_duplicate_bank(accounts: list[tuple[str, str]]) -> list[dict]:
    """accounts: (employee, bank account number). The same account on two employees is suspicious."""
    seen: dict[str, str] = {}
    findings = []
    for employee, account in accounts:
        if not account:
            continue
        if account in seen and seen[account] != employee:
            findings.append({"rule": "duplicate_bank_account", "severity": "high",
                             "detail": f"{employee} and {seen[account]} share a bank account."})
        seen.setdefault(account, employee)
    return findings


def check_zero_attendance(employee: str, present_days: int, working_days: int) -> dict | None:
    if working_days > 0 and present_days == 0:
        return {"rule": "no_attendance", "severity": "medium",
                "detail": f"{employee} has no attendance in a {working_days}-day period but a salary slip."}
    return None


def review(slips: list[dict]) -> list[dict]:
    """Run every rule across a payroll run. Each slip dict: employee, net_pay, previous_net, tds,
    expected_tds, bank_ac_no, present_days, working_days."""
    findings = []
    for s in slips:
        for f in (check_net_jump(s["net_pay"], s["previous_net"]) if s.get("previous_net") else None,
                  check_tds(s["tds"], s["expected_tds"]),
                  check_zero_attendance(s["employee"], s["present_days"], s["working_days"])):
            if f:
                findings.append(dict(f, employee=s["employee"]))
    findings += check_duplicate_bank([(s["employee"], s.get("bank_ac_no", "")) for s in slips])
    return findings

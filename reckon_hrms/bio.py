"""Biometric (fingerprint/face terminal) punch import. Pure Python parser, no Frappe import.

Terminals export CSV with an employee code, a timestamp and a direction (IN/OUT or 0/1). Rows are
normalised here; the Frappe layer resolves the code to an Employee and writes Employee Checkin rows,
skipping any punch that already exists.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

DIRECTION = {"in": "IN", "out": "OUT", "0": "IN", "1": "OUT", "check in": "IN", "check out": "OUT"}
TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M:%S")


def parse_time(text: str) -> datetime:
    value = (text or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised punch time: {text!r}")


def parse_punches(csv_text: str) -> tuple[list[dict], list[dict]]:
    """Return (valid punches, errors). Header names are matched loosely: code, time, direction."""
    reader = csv.DictReader(io.StringIO(csv_text))
    fields = {(f or "").strip().lower(): f for f in (reader.fieldnames or [])}

    def col(*names):
        for n in names:
            if n in fields:
                return fields[n]
        return None

    code_col = col("employee", "employee_code", "emp_code", "code", "user_id")
    time_col = col("time", "timestamp", "punch_time", "datetime")
    dir_col = col("direction", "log_type", "type", "status")
    if not (code_col and time_col):
        raise ValueError("CSV needs employee code and time columns.")

    punches, errors = [], []
    for line_no, row in enumerate(reader, start=2):
        code = (row.get(code_col) or "").strip()
        raw_dir = (row.get(dir_col) or "").strip().lower() if dir_col else ""
        try:
            when = parse_time(row.get(time_col) or "")
        except ValueError as exc:
            errors.append({"line": line_no, "error": str(exc)})
            continue
        if not code:
            errors.append({"line": line_no, "error": "Missing employee code"})
            continue
        direction = DIRECTION.get(raw_dir)  # None means decide from the sequence later
        punches.append({"employee_code": code, "time": when, "log_type": direction})
    punches.sort(key=lambda p: (p["employee_code"], p["time"]))
    return punches, errors


def infer_directions(punches: list[dict]) -> list[dict]:
    """Where a terminal gives no direction, alternate IN/OUT per employee per day."""
    last: dict[tuple[str, str], str] = {}
    out = []
    for p in punches:
        if p["log_type"]:
            out.append(p)
            continue
        key = (p["employee_code"], p["time"].date().isoformat())
        nxt = "OUT" if last.get(key) == "IN" else "IN"
        last[key] = nxt
        out.append(dict(p, log_type=nxt))
    return out

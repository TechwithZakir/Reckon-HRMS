"""ZKTeco / ZKBio Time punch sync: the parts that need no Frappe, so they can be tested alone.

Adapted from "ZKTeco Checkin Sync" by DeliveryDevs-ERP (MIT licence, see docs/THIRD_PARTY.md). That app
keeps one site-wide configuration; Reckon HRMS keeps one device per company, so a tenant's device only
ever reads and writes that tenant's employees, and the server is only ever asked to reach public hosts.
"""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime

AUTH_SCHEMES = ("Bearer", "Token", "JWT")  # the ZKBio Time versions differ; the first one the server accepts is kept
TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M")
MAX_PAGES = 20
PAGE_SIZE = 1000


def is_public_address(value: str) -> bool:
    """True only for an address on the public internet."""
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified
        or (ip.version == 4 and ip in ipaddress.ip_network("100.64.0.0/10"))  # carrier-grade NAT
    )


def assert_public_host(host: str, resolver=socket.getaddrinfo) -> None:
    """Refuse a host that is, or resolves to, a private, loopback or other internal address.

    The server connects to what a customer types here, so without this a device could be pointed at the
    server's own services or its cloud metadata address.
    """
    host = (host or "").strip().strip("[]")
    if not host or host.lower() in {"localhost", "localhost.localdomain"} or host.lower().endswith((".local", ".internal", ".localhost")):
        raise ValueError("Use the public IP address or domain of your ZKBio Time server.")
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            addresses = sorted({info[4][0] for info in resolver(host, None)})
        except OSError as exc:
            raise ValueError(f"The address {host} could not be found.") from exc
    if not addresses or not all(is_public_address(a) for a in addresses):
        raise ValueError("That address is on a private network. Your ZKBio Time server must be reachable from the internet.")


def base_url(host: str, port, https: bool = False) -> str:
    port = int(port) if port not in (None, "") else (443 if https else 80)
    if not 1 <= port <= 65535:
        raise ValueError("The port must be between 1 and 65535.")
    host = (host or "").strip().strip("[]")
    host = f"[{host}]" if ":" in host else host
    return f"{'https' if https else 'http'}://{host}:{port}"


def auth_headers(scheme: str, token: str) -> dict:
    return {"Content-Type": "application/json", "Authorization": f"{scheme} {token}"}


def normalise_response(payload) -> tuple[list, str | None]:
    """The list of transactions in a ZKBio Time response, and the address of the next page when there is one."""
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        rows = payload.get("data")
        if not isinstance(rows, list):
            rows = payload.get("results")
        return (rows if isinstance(rows, list) else []), (payload.get("next") or None)
    return [], None


def parse_time(value) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def log_type(punch_state, display=None) -> str:
    """IN or OUT: ZKBio Time sends state "0" for check in and "1" for check out."""
    if str(punch_state) == "1" or str(display or "").strip().lower() in {"check out", "break out", "overtime out"}:
        return "OUT"
    return "IN"


def parse_transaction(row: dict) -> dict | None:
    """One transaction as ``{code, time, log_type, device, id}``, or ``None`` when it lacks a code or a time."""
    if not isinstance(row, dict):
        return None
    code = str(row.get("emp_code") or "").strip()
    when = parse_time(row.get("punch_time"))
    if not code or not when:
        return None
    return {
        "code": code,
        "time": when,
        "log_type": log_type(row.get("punch_state"), row.get("punch_state_display")),
        "device": str(row.get("terminal_alias") or row.get("terminal_sn") or "ZKTeco Device"),
        "id": str(row.get("id") or ""),
    }


def checkin_device_label(parsed: dict) -> str:
    """The Employee Checkin device id: the terminal and the transaction id, so one punch is never stored twice."""
    return f"{parsed['device']} (ZKTeco-{parsed['id']})" if parsed["id"] else parsed["device"]

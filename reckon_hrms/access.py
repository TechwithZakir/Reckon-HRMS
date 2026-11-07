"""Reckon HRMS tenant access. Delegates to the platform, which owns team and role reconciliation.

Kept so existing callers (the seed) keep working; the logic lives in reckon_saas_platform.team.
"""

from __future__ import annotations

from reckon_saas_platform.team import ensure_tenant_roles as _ensure_tenant_roles
from reckon_saas_platform.team import reconcile_user as _reconcile_user
from reckon_saas_platform.team import sync_tenant_user_access as _sync_tenant_user_access

from reckon_hrms.saas_module import get_module_definition


def ensure_tenant_roles(company: str) -> dict:
    return _ensure_tenant_roles(get_module_definition(), company)


def reconcile_user(user: str) -> None:
    _reconcile_user(user)


def apply_assignment(user: str, company: str, role_profile: str | None) -> None:
    _reconcile_user(user)


def sync_tenant_user_access(doc, method=None) -> None:
    _sync_tenant_user_access(doc, method)

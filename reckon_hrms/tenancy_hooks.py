"""doc_events wrappers for the platform's tenant functions.

Frappe calls doc_events hooks as ``hook(doc, method)``. The platform functions take
``user`` as their second argument, so passing them directly would treat the event
name as a user. These wrappers pass the session user explicitly.
"""

import frappe

from reckon_saas_platform.tenant_security import (
    bind_doc_to_tenant,
    validate_tenant_company_immutable,
    validate_tenant_owned_doc,
)


def bind_company(doc, method=None, *args, **kwargs):
    bind_doc_to_tenant(doc, user=frappe.session.user)


def validate_company_immutable(doc, method=None, *args, **kwargs):
    validate_tenant_company_immutable(doc)


def validate_owned(doc, method=None, *args, **kwargs):
    validate_tenant_owned_doc(doc, user=frappe.session.user)

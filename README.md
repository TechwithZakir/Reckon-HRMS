# Reckon HRMS

Compact, company-wise SaaS HRMS and payroll for small businesses. Frappe HRMS is the engine; `reckon_saas_platform` provides tenants and companies, the same way it does for Reckon Distribution.

Version 1 modules: Employees, Attendance & Shifts, Leave, Payroll.

## How it plugs into the SaaS platform

- `reckon_saas_modules` registers the module (`reckon_hrms.saas_module`): key `hrms`, admin role `Reckon HRMS Admin`, module roles, and the seed handler.
- Company-owned HRMS doctypes (`reckon_hrms/constants.py`) use the platform's `tenant_security` functions for queries, permission checks and company binding. A tenant user sees one Company only.
- The seed handler (`reckon_hrms.seed.run_hrms_seed`) runs per tenant Company. It must never copy another tenant's data.

## Status: milestone 2 (SaaS registration)

- Not installed on any site yet. Next: install on `distribution-test.localhost`, verify each TENANT_OWNED_DOCTYPES entry has a `company` field in the inspected HRMS version, then run the platform's module sync.
- Setup Wizard, compact workspace and PWA branding come after that.

## Tests

```bash
python -m unittest discover -s tests
```

# Reckon HRMS

Compact, company-wise SaaS HRMS and payroll for small businesses, built on Frappe HRMS.

Version 1 modules: Employees, Attendance & Shifts, Leave, Payroll.

## Status: milestone 1 (skeleton)

- Frappe app `reckon_hrms` (depends on frappe, erpnext, hrms).
- Company-wise access helper for Employee, with framework-free tests.
- Not yet installed on any site. Workspace, setup wizard, and module trimming come next.

## Tests

```bash
python -m unittest discover -s tests
```

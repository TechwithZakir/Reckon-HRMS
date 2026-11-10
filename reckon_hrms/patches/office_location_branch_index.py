"""Office locations are now one per branch: drop the old unique index on company. Idempotent."""

import frappe


def execute():
    table = "tabHRMS Office Location"
    indexes = frappe.db.sql(f"SHOW INDEX FROM `{table}` WHERE Key_name = 'company' AND Non_unique = 0")
    if indexes:
        frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP INDEX `company`")

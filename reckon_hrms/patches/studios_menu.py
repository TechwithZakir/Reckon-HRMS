"""Rebuild the left navigation with HR Studio and Payroll Studio first. Idempotent."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

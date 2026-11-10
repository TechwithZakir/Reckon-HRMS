"""Rebuild the Reckon HRMS left navigation: one entry per item, all HR and payroll reports grouped."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

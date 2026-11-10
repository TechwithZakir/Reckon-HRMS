"""Rebuild the left navigation with Office Location label and without Employee Checkin. Idempotent."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

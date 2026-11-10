"""Rebuild the Reckon HRMS left navigation so Setup (one page for company, salary rules and run) is first."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

"""Re-apply the menu so Home opens the new overview page and Dashboard keeps the charts."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

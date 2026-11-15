"""Put Home first in the Reckon HRMS menu and let every item show its icon (re-applies the menu)."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

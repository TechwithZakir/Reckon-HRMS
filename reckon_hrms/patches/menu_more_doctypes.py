"""Re-apply the menu so every list the Studios open also sits in the Reckon HRMS menu."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

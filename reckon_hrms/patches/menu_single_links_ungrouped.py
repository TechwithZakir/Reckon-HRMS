"""Re-apply the menu: one-item groups become plain links, related items stay under their heading."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

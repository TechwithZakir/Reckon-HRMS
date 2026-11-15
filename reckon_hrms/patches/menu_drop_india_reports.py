"""Re-apply the menu without the India-only Provident Fund report and the advance report tenants cannot open."""

from reckon_hrms.patches.desk_menu_arrangement import execute as arrange_menu


def execute():
    arrange_menu()

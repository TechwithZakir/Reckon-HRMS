"""Friendlier Reckon HRMS workspace group names, applied to the grouped links and content blocks."""

from reckon_hrms.patches import holiday_list_and_workspace, workspace_content


def execute():
    holiday_list_and_workspace.execute()
    workspace_content.execute()

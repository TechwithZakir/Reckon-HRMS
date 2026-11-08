"""Paging limits for server-paged lists. Pure Python, so the rules are unit-testable."""

MAX_PAGE = 100
DEFAULT_PAGE = 25


def page_bounds(start, page_length) -> tuple[int, int]:
    """Clamp paging inputs: start is never negative, length is 1..MAX_PAGE."""
    try:
        start_i = max(0, int(start or 0))
    except (TypeError, ValueError):
        start_i = 0
    try:
        length_i = int(page_length or DEFAULT_PAGE)
    except (TypeError, ValueError):
        length_i = DEFAULT_PAGE
    return start_i, min(MAX_PAGE, max(1, length_i))

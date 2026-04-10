"""Query construction for the Oxford planning scraper."""

from models import ApplicationStatusMode


def build_search_payload(
    *,
    csrf_token: str,
    week: str,
    ward_code: str,
    parish_code: str = "",
    status_mode: ApplicationStatusMode = "validated",
) -> dict[str, str]:
    """Build the weekly list form payload for a single query attempt.

    Args:
        csrf_token: CSRF token extracted from the weekly-list form.
        week: Exact week label from the weekly-list dropdown.
        ward_code: Ward code submitted to the Oxford weekly-list form.
        parish_code: Optional parish code submitted to the Oxford weekly-list form.
        status_mode: Which weekly-list toggle to use: ``validated`` or ``decided``.

    Returns:
        Form payload for a single weekly-list request.
    """
    return {
        "_csrf": csrf_token,
        "searchCriteria.parish": parish_code,
        "searchCriteria.ward": ward_code,
        "week": week,
        "dateType": "DC_Decided" if status_mode == "decided" else "DC_Validated",
        "searchType": "Application",
    }

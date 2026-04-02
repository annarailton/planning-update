"""Tests for the planning service."""

import httpx
import pytest

from schemas.planning import PlanningApplicationDateType
from services.planning_service import PlanningService

FORM_HTML = """
<form id="weeklyListForm">
  <input type="hidden" name="_csrf" value="csrf-token-123" />
  <select name="searchCriteria.ward" id="ward">
    <option value="">All</option>
    <option value="HINKPK">Hinksey Park</option>
    <option value="STMARY">St Marys Ward</option>
  </select>
  <select name="week" id="week">
    <option value="30 Mar 2026">30 Mar 2026</option>
    <option value="23 Mar 2026">23 Mar 2026</option>
  </select>
</form>
"""

SEARCH_RESULTS_HTML = """
<html>
  <body>
    <ul id="searchresults">
      <li class="searchresult">
        <a href="/online-applications/applicationDetails.do?keyVal=ABC123&amp;activeTab=summary" class="summaryLink">
          <div class="summaryLinkTextClamp">Erection of two-storey rear extension.</div>
        </a>
        <p class="address">1 Example Street Oxford OX1 1AA</p>
        <p class="metaInfo">
          Ref. No:
          26/00001/FUL
        </p>
      </li>
    </ul>
  </body>
</html>
"""

DETAIL_HTML = """
<html>
  <body>
    <a href="/online-applications/applicationDetails.do?activeTab=summary&amp;keyVal=ABC124" id="subtab_summary" class="active">
      <span>Summary</span>
    </a>
    <table id="simpleDetailsTable" summary="Case Details">
      <tr><th scope="row">Reference</th><td>26/00002/H42</td></tr>
      <tr><th scope="row">Address</th><td>2 Example Street Oxford OX1 1AB</td></tr>
      <tr><th scope="row">Proposal</th><td>Single storey rear extension.</td></tr>
    </table>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_get_weekly_applications_parses_search_results() -> None:
    """The service should parse multi-result weekly search pages."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=FORM_HTML)

        form = dict(
            item.split("=", 1) for item in request.content.decode("utf-8").split("&")
        )
        assert form["_csrf"] == "csrf-token-123"
        assert form["searchCriteria.ward"] == "HINKPK"
        assert form["week"] == "30+Mar+2026"
        assert form["dateType"] == "DC_Validated"
        return httpx.Response(200, text=SEARCH_RESULTS_HTML)

    service = PlanningService(transport=httpx.MockTransport(handler))

    response = await service.get_weekly_applications(ward="Hinksey Park")

    assert response.total_count == 1
    assert response.filters.ward == "Hinksey Park"
    assert response.filters.week_beginning == "30 Mar 2026"
    assert response.applications[0].application_id == "26/00001/FUL"
    assert response.applications[0].location == "1 Example Street Oxford OX1 1AA"
    assert response.applications[0].summary == "Erection of two-storey rear extension."
    assert response.applications[0].ward == "Hinksey Park"
    assert (
        response.applications[0].detail_url
        == "https://public.oxford.gov.uk/online-applications/applicationDetails.do?keyVal=ABC123&activeTab=summary"
    )


@pytest.mark.asyncio
async def test_get_weekly_applications_parses_single_application_summary() -> None:
    """The service should normalize a single-result redirect to summary view."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, text=FORM_HTML)

        return httpx.Response(
            200,
            text=DETAIL_HTML,
            request=request,
            headers={"content-type": "text/html"},
        )

    service = PlanningService(transport=httpx.MockTransport(handler))

    response = await service.get_weekly_applications(
        ward="HINKPK",
        week_beginning="23 Mar 2026",
        date_type=PlanningApplicationDateType.DECIDED,
    )

    assert response.total_count == 1
    assert response.filters.date_type == PlanningApplicationDateType.DECIDED
    assert response.filters.week_beginning == "23 Mar 2026"
    assert response.applications[0].application_id == "26/00002/H42"
    assert response.applications[0].location == "2 Example Street Oxford OX1 1AB"
    assert response.applications[0].summary == "Single storey rear extension."
    assert response.applications[0].ward == "Hinksey Park"
    assert (
        response.applications[0].detail_url
        == "https://public.oxford.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal=ABC124"
    )

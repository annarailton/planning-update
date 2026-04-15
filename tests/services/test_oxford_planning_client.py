"""Tests for Oxford planning HTTP client helpers."""

import backoff
import requests

from planning_update.services.oxford_planning_client import (
    fetch_form,
    request_with_backoff,
    summarize_response,
)


class DummyResponse:
    """Simple response test double."""

    def __init__(
        self,
        *,
        status_code: int,
        text: str = "",
        url: str = "https://example.com",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


class DummySession:
    """Minimal session double that replays queued results."""

    def __init__(self, results: list[object]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def request(self, method: str, url: str, **kwargs) -> DummyResponse:
        self.calls.append((method, url, kwargs))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def patch_backoff_sleep(monkeypatch) -> list[float]:
    """Patch backoff's internal sleep function and collect requested waits."""
    sleep_calls: list[float] = []
    monkeypatch.setattr(backoff._sync.time, "sleep", sleep_calls.append)
    return sleep_calls


def patch_backoff_jitter(monkeypatch) -> None:
    """Patch jitter to keep retry waits deterministic in tests."""
    monkeypatch.setattr(backoff, "full_jitter", lambda value: value / 2)


def test_request_with_backoff_retries_rate_limit_then_succeeds(monkeypatch) -> None:
    """429 responses should be retried with exponential backoff."""
    session = DummySession(
        [
            DummyResponse(status_code=429),
            DummyResponse(status_code=200, text="ok"),
        ]
    )
    patch_backoff_jitter(monkeypatch)
    sleep_calls = patch_backoff_sleep(monkeypatch)

    response = request_with_backoff(
        session,
        method="GET",
        url="https://example.com",
    )

    assert response.status_code == 200
    assert len(session.calls) == 2
    assert sleep_calls == [2.0]


def test_request_with_backoff_retries_connection_errors_then_succeeds(
    monkeypatch,
) -> None:
    """Transient connection failures should be retried."""
    session = DummySession(
        [
            requests.ConnectionError("boom"),
            DummyResponse(status_code=200, text="ok"),
        ]
    )
    patch_backoff_jitter(monkeypatch)
    sleep_calls = patch_backoff_sleep(monkeypatch)

    response = request_with_backoff(
        session,
        method="GET",
        url="https://example.com",
    )

    assert response.status_code == 200
    assert len(session.calls) == 2
    assert sleep_calls == [1.0]


def test_request_with_backoff_retries_5xx_with_shorter_backoff_than_429(
    monkeypatch,
) -> None:
    """Transient 5xx responses should use the non-rate-limit retry policy."""
    session = DummySession(
        [
            DummyResponse(status_code=503),
            DummyResponse(status_code=200, text="ok"),
        ]
    )
    patch_backoff_jitter(monkeypatch)
    sleep_calls = patch_backoff_sleep(monkeypatch)

    response = request_with_backoff(
        session,
        method="GET",
        url="https://example.com",
    )

    assert response.status_code == 200
    assert len(session.calls) == 2
    assert sleep_calls == [1.0]


def test_request_with_backoff_does_not_retry_non_retriable_http_error(
    monkeypatch,
) -> None:
    """Client errors other than 429 should fail immediately."""
    session = DummySession([DummyResponse(status_code=404)])
    sleep_calls = patch_backoff_sleep(monkeypatch)

    try:
        request_with_backoff(
            session,
            method="GET",
            url="https://example.com",
        )
    except requests.HTTPError as exc:
        assert exc.response is not None
        assert exc.response.status_code == 404
    else:
        raise AssertionError("Expected HTTPError")

    assert len(session.calls) == 1
    assert sleep_calls == []


def test_request_with_backoff_raises_after_exhausting_retries(monkeypatch) -> None:
    """Retriable failures should still raise once retries are exhausted."""
    session = DummySession([DummyResponse(status_code=503) for _ in range(5)])
    patch_backoff_jitter(monkeypatch)
    sleep_calls = patch_backoff_sleep(monkeypatch)

    try:
        request_with_backoff(
            session,
            method="GET",
            url="https://example.com",
        )
    except requests.HTTPError as exc:
        assert exc.response is not None
        assert exc.response.status_code == 503
    else:
        raise AssertionError("Expected HTTPError")

    assert len(session.calls) == 5
    assert sleep_calls == [1.0, 2.0, 4.0, 8.0]


def test_summarize_response_includes_status_url_and_snippet() -> None:
    """Response summaries should include the key diagnostics fields."""
    response = DummyResponse(
        status_code=403,
        url="https://example.com/blocked",
        text="<html><title>Access denied</title><body>Forbidden</body></html>",
        headers={"Content-Type": "text/html"},
    )

    summary = summarize_response(response)

    assert "status=403" in summary
    assert "url=https://example.com/blocked" in summary
    assert "content_type=text/html" in summary
    assert "Access denied" in summary


def test_fetch_form_raises_with_response_details_when_page_is_unexpected(
    monkeypatch,
) -> None:
    """Form parsing failures should include a compact response diagnostic."""
    monkeypatch.setattr(
        "planning_update.services.oxford_planning_client.request_with_backoff",
        lambda session, *, method, url, **kwargs: DummyResponse(
            status_code=200,
            url=url,
            text="<html><title>Blocked</title><body>Access denied</body></html>",
            headers={"Content-Type": "text/html"},
        ),
    )

    try:
        fetch_form(DummySession([]))
    except RuntimeError as exc:
        message = str(exc)
        assert "Could not find CSRF token on weekly list page." in message
        assert "Response details:" in message
        assert "status=200" in message
        assert "Access denied" in message
    else:
        raise AssertionError("Expected RuntimeError")

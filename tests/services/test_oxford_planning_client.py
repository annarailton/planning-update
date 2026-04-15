"""Tests for Oxford planning HTTP client helpers."""

import backoff
import requests

from planning_update.services.oxford_planning_client import request_with_backoff


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


def test_request_with_backoff_retries_rate_limit_then_succeeds(monkeypatch) -> None:
    """429 responses should be retried with exponential backoff."""
    session = DummySession(
        [
            DummyResponse(status_code=429),
            DummyResponse(status_code=200, text="ok"),
        ]
    )
    sleep_calls = patch_backoff_sleep(monkeypatch)

    response = request_with_backoff(
        session,
        method="GET",
        url="https://example.com",
    )

    assert response.status_code == 200
    assert len(session.calls) == 2
    assert sleep_calls == [0.5]


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
    sleep_calls = patch_backoff_sleep(monkeypatch)

    response = request_with_backoff(
        session,
        method="GET",
        url="https://example.com",
    )

    assert response.status_code == 200
    assert len(session.calls) == 2
    assert sleep_calls == [0.5]


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
    session = DummySession([DummyResponse(status_code=503) for _ in range(4)])
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

    assert len(session.calls) == 4
    assert sleep_calls == [0.5, 1.0, 2.0]

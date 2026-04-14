"""Shared pytest fixtures for tests."""

from collections.abc import Callable
from datetime import date

import pytest

from planning_update.models import Application, ApplicationRef


@pytest.fixture
def application_factory() -> Callable[..., Application]:
    """Build a baseline application with optional field overrides."""

    def factory(**overrides) -> Application:
        values = {
            "application_ref": ApplicationRef(value="26/00281/FUL"),
            "proposal": "Test proposal",
            "url": "https://example.com/app",
            "address": "1 Test Street",
            "ward": "Churchill Ward",
            "parish": None,
            "received": date(2026, 2, 2),
            "validated": date(2026, 2, 9),
            "decided": date(2026, 4, 9),
            "consultation_deadline": date(2026, 3, 16),
            "determination_deadline": date(2026, 4, 6),
            "status": "Decided",
            "decision": "Approved",
        }
        values.update(overrides)
        return Application(
            **values,
        )

    return factory

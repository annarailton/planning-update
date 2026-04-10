"""Tests for the application data models."""

from datetime import date

import pytest

from models import Application, ApplicationRef


@pytest.mark.parametrize(
    "reference",
    ["26/00281/FUL", "26/00206/LBC", "26/00744/H42"],
)
def test_application_ref_accepts_known_valid_references(reference: str) -> None:
    """ApplicationRef should accept known valid planning references."""
    assert ApplicationRef(value=reference).value == reference


@pytest.mark.parametrize(
    "reference",
    [
        "skip to main content",
        "26-00281-FUL",
        "26/281/FUL",
    ],
)
def test_application_ref_rejects_invalid_references(reference: str) -> None:
    """ApplicationRef should reject malformed planning references."""
    with pytest.raises(ValueError, match="Invalid application reference"):
        ApplicationRef(value=reference)


def test_application_parses_dates_to_datetimes() -> None:
    """Application should parse Oxford planning date strings to dates."""
    application = Application(
        application_ref=ApplicationRef(value="26/00281/FUL"),
        proposal="Test proposal",
        url="https://example.com",
        address="1 Test Street",
        received="Thu 12 Mar 2026",
        validated="Fri 13 Mar 2026",
        decided="Sat 14 Mar 2026",
        status="Registered",
    )

    assert application.received == date(2026, 3, 12)
    assert application.validated == date(2026, 3, 13)
    assert application.decided == date(2026, 3, 14)


def test_application_model_validate_parses_updated_date_strings() -> None:
    """Application.model_validate should parse updated Oxford date strings."""
    application = Application(
        application_ref=ApplicationRef(value="26/00281/FUL"),
        proposal="Test proposal",
        url="https://example.com",
        address="1 Test Street",
        received="Thu 12 Mar 2026",
        validated="Fri 13 Mar 2026",
    )

    updated = Application.model_validate(
        application.model_dump() | {"decided": "Sat 14 Mar 2026"}
    )

    assert updated.decided == date(2026, 3, 14)

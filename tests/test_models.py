"""Tests for the application data models."""

import pytest

from models import ApplicationRef


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

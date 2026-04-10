"""Tests for ward-name normalization and resolution."""

import pytest

from config import normalize_ward_name, resolve_ward_code


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("  Churchill Ward ", "churchill"),
        ("St Clement's Ward", "st clements"),
        ("Carfax & Jericho Ward", "carfax and jericho"),
        ("Headington Hill and Northway", "headington hill and northway"),
        ("  St. Clement's  ", "st clements"),
        ("  St. Marys  ", "st marys"),
    ],
)
def test_normalize_ward_name_strips_case_and_suffix(
    raw_name: str,
    expected: str,
) -> None:
    """Normalization should ignore case and a trailing ward suffix."""
    assert normalize_ward_name(raw_name) == expected


@pytest.mark.parametrize(
    ("ward_name", "expected_code"),
    [
        ("churchill", "CHURCH"),
        ("Churchill Ward", "CHURCH"),
        ("headington", "HEAD"),
        ("hinksey park", "HINKPK"),
        ("Headington Hill", "HHLNOR"),
        ("Headington Hill And Northway", "HHLNOR"),
        ("Carfax", "CARJER"),
        ("Jericho", "CARJER"),
        ("Carfax and Jericho ward", "CARJER"),
        ("St Clements", "STCLEM"),
        ("Churchil", "CHURCH"),
    ],
)
def test_resolve_ward_code_matches_expected_code(
    ward_name: str,
    expected_code: str,
) -> None:
    """Resolution should match exact, alias, and fuzzy ward-name inputs."""
    assert resolve_ward_code(ward_name) == expected_code


def test_resolve_ward_code_rejects_unknown_ward() -> None:
    """Resolution should fail clearly for unknown wards."""
    with pytest.raises(ValueError, match="Unknown ward"):
        resolve_ward_code("not-a-real-ward")

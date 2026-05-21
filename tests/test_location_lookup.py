"""Tests for ward-name and parish-name normalization and resolution."""

import pytest

from planning_update.lookup.location_lookup import (
    normalize_name,
    resolve_division_name,
    resolve_parish_code,
    resolve_ward_code,
)


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
    assert normalize_name(raw_name) == expected


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("Littlemore Parish Council", "littlemore"),
        ("Risinghurst & Sandhills Parish Council", "risinghurst and sandhills"),
        (" old marston ", "old marston"),
    ],
)
def test_normalize_parish_name_strips_case_and_suffix(
    raw_name: str,
    expected: str,
) -> None:
    """Normalization should ignore parish-council suffix and punctuation."""
    assert normalize_name(raw_name) == expected


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("Cowley ED", "cowley"),
        ("Churchill & Lye Valley ED", "churchill and lye valley"),
        ("Summertown & Walton Manor", "summertown and walton manor"),
    ],
)
def test_normalize_division_name_strips_case_and_suffix(
    raw_name: str,
    expected: str,
) -> None:
    """Normalization should ignore county-division suffix and punctuation."""
    assert normalize_name(raw_name, removable_suffixes=("ed",)) == expected


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


@pytest.mark.parametrize(
    ("parish_name", "expected_code"),
    [
        ("Littlemore", "LPC"),
        ("Littlemore Parish Council", "LPC"),
        ("Old Marston", "OLD"),
        ("Risinghurst and Sandhills", "RPC"),
        ("Littlemor", "LPC"),
    ],
)
def test_resolve_parish_code_matches_expected_code(
    parish_name: str,
    expected_code: str,
) -> None:
    """Resolution should match exact and fuzzy parish-name inputs."""
    assert resolve_parish_code(parish_name) == expected_code


@pytest.mark.parametrize(
    ("division_name", "expected_name"),
    [
        ("Cowley", "Cowley"),
        ("Cowley ED", "Cowley"),
        ("Churchill and Lye Valley", "Churchill & Lye Valley"),
        ("Summertown and Walton Manor", "Summertown & Walton Manor"),
        ("Wolvercote and Cutteslowe", "Wolvercote & Cutteslowe"),
        ("Cowly", "Cowley"),
    ],
)
def test_resolve_division_name_matches_expected_name(
    division_name: str,
    expected_name: str,
) -> None:
    """Resolution should match exact and fuzzy division-name inputs."""
    assert resolve_division_name(division_name) == expected_name


def test_resolve_ward_code_rejects_unknown_ward() -> None:
    """Resolution should fail clearly for unknown wards."""
    with pytest.raises(ValueError, match="Unknown ward"):
        resolve_ward_code("not-a-real-ward")


def test_resolve_parish_code_rejects_unknown_parish() -> None:
    """Resolution should fail clearly for unknown parishes."""
    with pytest.raises(ValueError, match="Unknown parish"):
        resolve_parish_code("not-a-real-parish")


def test_resolve_division_name_rejects_unknown_division() -> None:
    """Resolution should fail clearly for unknown divisions."""
    with pytest.raises(ValueError, match="Unknown division"):
        resolve_division_name("not-a-real-division")

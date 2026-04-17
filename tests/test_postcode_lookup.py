"""Tests for local postcode-to-ward lookup helpers."""

import pytest

from planning_update.constants import CODEPOINT_CSV_PATH
from planning_update.lookup.postcode_lookup import (
    lookup_postcode_in_oxford_wards,
    normalize_postcode,
)


@pytest.mark.parametrize(
    ("raw_postcode", "expected"),
    [
        (" ox1  4aq ", "OX14AQ"),
        ("OX1 4AQ", "OX14AQ"),
        ("ox14aq", "OX14AQ"),
    ],
)
def test_normalize_postcode_strips_spacing_and_case(
    raw_postcode: str,
    expected: str,
) -> None:
    """Postcodes should normalize to uppercase without spaces."""
    assert normalize_postcode(raw_postcode) == expected


@pytest.mark.parametrize(
    ("postcode", "expected_ward"),
    [
        pytest.param(
            "OX4 1DD",
            "St Clement's",
            id="east-oxford-community-centre",
        ),
        pytest.param(
            "OX4 4HF",
            "Rose Hill & Iffley",
            id="rose-hill-community-centre",
        ),
        pytest.param(
            "OX3 9RF",
            "Headington Hill & Northway",
            id="northway-community-centre",
        ),
        pytest.param(
            "OX4 4NL",
            "Littlemore",
            id="littlemore-community-centre",
        ),
        pytest.param(
            "OX1 4RP",
            "Hinksey Park",
            id="south-oxford-community-centre",
        ),
    ],
)
def test_lookup_postcode_in_oxford_wards_returns_matching_ward(
    postcode: str,
    expected_ward: str,
) -> None:
    """A postcode inside Oxford should resolve to a ward name and coordinates."""
    result = lookup_postcode_in_oxford_wards(
        postcode,
        codepoint_csv_path=CODEPOINT_CSV_PATH,
    )

    assert result.ward_name == expected_ward


@pytest.mark.parametrize(
    "postcode",
    [
        pytest.param("OX16 5QB", id="banbury-town-hall"),
        pytest.param("OX26 6AL", id="bicester-town-hall"),
        pytest.param("OX11 7JN", id="didcot-town-hall"),
    ],
)
def test_lookup_postcode_in_oxford_wards_reports_outside_oxford(
    postcode: str,
) -> None:
    """A postcode outside Oxford should return no ward match."""
    result = lookup_postcode_in_oxford_wards(
        postcode,
        codepoint_csv_path=CODEPOINT_CSV_PATH,
    )

    assert result.ward_name is None


@pytest.mark.parametrize(
    "postcode",
    [
        pytest.param("OX9 9ZZ", id="unknown-postcode"),
        pytest.param(
            "OX14 3HJ", id="abingdon-town-hall"
        ),  # not in the OX CSV for some reason
        pytest.param("M60 2LA", id="manchester-town-hall"),
        pytest.param("B1 1BB", id="birmingham-town-hall"),
        pytest.param("SW1A 0AA", id="houses-of-parliament"),
    ],
)
def test_postcode_missing_from_codepoint_csv(
    postcode: str,
) -> None:
    """Postcodes missing from the checked-in Code-Point CSV should fail clearly."""
    with pytest.raises(ValueError, match="was not found"):
        lookup_postcode_in_oxford_wards(
            postcode,
            codepoint_csv_path=CODEPOINT_CSV_PATH,
        )

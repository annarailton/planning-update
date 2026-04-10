"""Configuration helpers for the Oxford planning scraper."""

from __future__ import annotations

import json
import re
from pathlib import Path

from rapidfuzz import process

CONFIG_DATA_PATH = Path(__file__).with_name("ward_mappings.json")
WARD_FUZZY_MATCH_THRESHOLD = 85


def load_mapping_options() -> dict[str, list[dict[str, str]]]:
    """Load ward and parish options from the JSON config file.

    Returns:
        Parsed mapping data keyed by section name.
    """
    return json.loads(CONFIG_DATA_PATH.read_text())


def normalize_ward_name(value: str) -> str:
    """Normalize a ward name for forgiving CLI matching.

    Args:
        value: Raw ward name input.

    Returns:
        A normalized comparison key.
    """
    normalized = value.strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("'", "")
    # Drop the standalone word "ward" so users can omit or include it
    normalized = re.sub(r"\bward\b", "", normalized)
    # Replace non-alphanumeric punctuation with spaces to smooth variants
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    # Collapse any repeated whitespace created by earlier cleanup steps
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def build_ward_alias_to_code() -> dict[str, str]:
    """Build a forgiving alias lookup for ward names.

    Returns:
        A mapping from normalized ward aliases to ward code.
    """
    aliases: dict[str, str] = {}

    for ward_name, ward_code in WARD_NAME_TO_CODE.items():
        normalized_name = normalize_ward_name(ward_name)
        aliases[normalized_name] = ward_code

        if " and " in normalized_name:
            for part in normalized_name.split(" and "):
                alias = part.strip()
                if alias:
                    aliases[alias] = ward_code

    return aliases


def resolve_ward_code(ward_name: str) -> str:
    """Resolve a human-readable ward name to the configured ward code.

    Args:
        ward_name: Human-readable ward name from the CLI.

    Returns:
        The first configured ward code for the provided ward name.

    Raises:
        ValueError: If the ward name is not present in the configured mapping.
    """
    requested_name = normalize_ward_name(ward_name)
    ward_code = WARD_ALIAS_TO_CODE.get(requested_name)
    if ward_code:
        return ward_code

    fuzzy_match = process.extractOne(
        requested_name,
        list(WARD_ALIAS_TO_CODE),
        score_cutoff=WARD_FUZZY_MATCH_THRESHOLD,
    )
    if fuzzy_match is not None:
        matched_alias, _, _ = fuzzy_match
        return WARD_ALIAS_TO_CODE[matched_alias]

    available_wards = ", ".join(sorted(WARD_NAME_TO_CODE))
    raise ValueError(f"Unknown ward '{ward_name}'. Available wards: {available_wards}")


_MAPPING_DATA = load_mapping_options()
WARD_NAME_TO_CODE = {
    option["name"]: option["code"] for option in _MAPPING_DATA["wards"]
}
WARD_ALIAS_TO_CODE = build_ward_alias_to_code()

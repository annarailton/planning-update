"""Configuration helpers for the Oxford planning scraper."""

from __future__ import annotations

import json
import re
from pathlib import Path

from rapidfuzz import process

CONFIG_DATA_PATH = Path(__file__).with_name("ward_mappings.json")
FUZZY_MATCH_THRESHOLD = 85


def load_mapping_options() -> dict[str, list[dict[str, str]]]:
    """Load ward and parish options from the JSON config file.

    Returns:
        Parsed mapping data keyed by section name.
    """
    return json.loads(CONFIG_DATA_PATH.read_text())


def normalize_name(
    value: str,
    removable_suffixes: tuple[str, ...] = ("ward", "parish council"),
) -> str:
    """Normalize a name for forgiving CLI matching.

    Args:
        value: Raw name input.
        removable_suffixes: Whole-word suffix phrases to strip before matching.

    Returns:
        A normalized comparison key.
    """
    normalized = value.strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("'", "")
    for suffix in removable_suffixes:
        # Drop optional suffix phrases so users can shorten the input.
        normalized = re.sub(rf"\b{re.escape(suffix)}\b", "", normalized)
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
        normalized_name = normalize_name(ward_name)
        aliases[normalized_name] = ward_code

        if " and " in normalized_name:
            for part in normalized_name.split(" and "):
                alias = part.strip()
                if alias:
                    aliases[alias] = ward_code

    return aliases


def build_parish_alias_to_code() -> dict[str, str]:
    """Build a forgiving alias lookup for parish names.

    Returns:
        A mapping from normalized parish aliases to parish code.
    """
    return {
        normalize_name(parish_name): parish_code
        for parish_name, parish_code in PARISH_NAME_TO_CODE.items()
    }


def resolve_code(
    raw_name: str,
    *,
    alias_to_code: dict[str, str],
    name_to_code: dict[str, str],
    kind: str,
) -> str:
    """Resolve a human-readable area name to its configured code.

    Args:
        raw_name: Human-readable name from the CLI.
        alias_to_code: Normalized alias lookup for the area type.
        name_to_code: Canonical name-to-code lookup for the area type.
        kind: Human-readable area kind used in error messages.

    Returns:
        The configured code for the provided name.

    Raises:
        ValueError: If the name is not present in the configured mapping.
    """
    requested_name = normalize_name(raw_name)
    resolved_code = alias_to_code.get(requested_name)
    if resolved_code:
        return resolved_code

    fuzzy_match = process.extractOne(
        requested_name,
        list(alias_to_code),
        score_cutoff=FUZZY_MATCH_THRESHOLD,
    )
    if fuzzy_match is not None:
        matched_alias, _, _ = fuzzy_match
        return alias_to_code[matched_alias]

    available_names = ", ".join(sorted(name_to_code))
    raise ValueError(
        f"Unknown {kind} '{raw_name}'. Available {kind}s: {available_names}"
    )


def resolve_ward_code(ward_name: str) -> str:
    """Resolve a human-readable ward name to the configured ward code.

    Args:
        ward_name: Human-readable ward name from the CLI.

    Returns:
        The configured ward code for the provided ward name.
    """
    return resolve_code(
        ward_name,
        alias_to_code=WARD_ALIAS_TO_CODE,
        name_to_code=WARD_NAME_TO_CODE,
        kind="ward",
    )


def resolve_parish_code(parish_name: str) -> str:
    """Resolve a human-readable parish name to the configured parish code.

    Args:
        parish_name: Human-readable parish name from the CLI.

    Returns:
        The configured parish code for the provided parish name.
    """
    return resolve_code(
        parish_name,
        alias_to_code=PARISH_ALIAS_TO_CODE,
        name_to_code=PARISH_NAME_TO_CODE,
        kind="parish",
    )


_MAPPING_DATA = load_mapping_options()
WARD_CODE_TO_NAME = {
    option["code"]: option["name"] for option in _MAPPING_DATA["wards"]
}
WARD_NAME_TO_CODE = {
    option["name"]: option["code"] for option in _MAPPING_DATA["wards"]
}
WARD_ALIAS_TO_CODE = build_ward_alias_to_code()
PARISH_CODE_TO_NAME = {
    option["code"]: option["name"] for option in _MAPPING_DATA["parishes"]
}
PARISH_NAME_TO_CODE = {
    option["name"]: option["code"] for option in _MAPPING_DATA["parishes"]
}
PARISH_ALIAS_TO_CODE = build_parish_alias_to_code()

"""Configuration constants for the Oxford planning scraper."""

from __future__ import annotations

from collections import defaultdict

DEFAULT_WARD_NAME = "Hinksey Park"

WARD_OPTIONS = (
    ("BARTSD", "Barton And Sandhills Ward"),
    ("BBLEYS", "Blackbird Leys Ward"),
    ("CARJER", "Carfax And Jericho Ward"),
    ("CHURCH", "Churchill Ward"),
    ("COWLEY", "Cowley Ward"),
    ("CUTSUN", "Cutteslowe And Sunnymead Ward"),
    ("DONN", "Donnington Ward"),
    ("HHLNOR", "Headington Hill And Northway Ward"),
    ("HEAD", "Headington Ward"),
    ("HINKPK", "Hinksey Park"),
    ("HOLYWE", "Holywell Ward"),
    ("LITTM", "Littlemore Ward"),
    ("LYEVAL", "Lye Valley Ward"),
    ("MARST", "Marston Ward"),
    ("NORBRK", "Northfield Brook Ward"),
    ("OSNYST", "Osney And St. Thomas Ward"),
    ("OCB", "Outside City Boundary"),
    ("OSCB", "Outside City Boundary"),
    ("QUARIS", "Quarry And Risinghurst Ward"),
    ("RHIFF", "Rose Hill And Iffley Ward"),
    ("STCLEM", "St Clement's Ward"),
    ("STMARY", "St Marys Ward"),
    ("SUMTN1", "Summertown"),
    ("TEMCOW", "Temple Cowley Ward"),
    ("WALTMA", "Walton Manor Ward"),
    ("WOLVER", "Wolvercote Ward"),
)

PARISH_OPTIONS = (
    ("BPC", "Blackbird Leys Parish Council"),
    ("LPC", "Littlemore Parish Council"),
    ("OLD", "Old Marston Parish Council"),
    ("OSCB", "Outside City Boundary"),
    ("RPC", "Risinghurst And Sandhills Parish Council"),
)


def build_code_to_name(options: tuple[tuple[str, str], ...]) -> dict[str, str]:
    """Build a code-to-name lookup from option tuples."""
    return dict(options)


def build_name_to_codes(
    options: tuple[tuple[str, str], ...],
) -> dict[str, tuple[str, ...]]:
    """Build a name-to-codes lookup that preserves duplicate names."""
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for code, name in options:
        grouped[name].append(code)
    return {name: tuple(codes) for name, codes in grouped.items()}


WARD_CODE_TO_NAME = build_code_to_name(WARD_OPTIONS)
WARD_NAME_TO_CODES = build_name_to_codes(WARD_OPTIONS)

PARISH_CODE_TO_NAME = build_code_to_name(PARISH_OPTIONS)
PARISH_NAME_TO_CODES = build_name_to_codes(PARISH_OPTIONS)

DEFAULT_WARD_CODE = WARD_NAME_TO_CODES[DEFAULT_WARD_NAME][0]

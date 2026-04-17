"""Postcode-to-ward lookup helpers for local Oxford boundary data."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape

from ..constants import BOUNDARIES_PATH, CODEPOINT_CSV_PATH

# Code-Point Open and the checked-in ward boundaries use different coordinate
# systems, so postcode points need to be reprojected before we can compare them.
#
# - Code-Point Open stores postcode centroids as British National Grid easting /
#   northing coordinates (`EPSG:27700`).
# - The checked-in Oxford ward GeoJSON uses WGS84 longitude / latitude
#   coordinates (`EPSG:4326`).
#
# We keep a shared transformer here so postcode points can be converted once
# before:
#
# - the point-in-polygon ward check
# - printing user-friendly latitude / longitude values
#
# `always_xy=True` keeps the axis order explicit:
#
# - easting, northing in
# - longitude, latitude out

BNG_TO_WGS84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


@dataclass(frozen=True)
class PostcodeLookupResult:
    """Resolved postcode coordinates and containing Oxford ward."""

    postcode: str
    normalized_postcode: str
    latitude: float
    longitude: float
    easting: int
    northing: int
    ward_name: str | None


def normalize_postcode(postcode: str) -> str:
    """Normalize a postcode for file matching, removing whitespace and uppercasing.

    Examples:
        >>> normalize_postcode("OX1 4AQ")
        'OX14AQ'
        >>> normalize_postcode(" ox1   4aq ")
        'OX14AQ'
    """
    return re.sub(r"\s+", "", postcode).upper()


def load_ward_boundaries(path: Path = BOUNDARIES_PATH) -> list[tuple[str, object]]:
    """Load ward shapes from the checked-in Oxford GeoJSON file."""
    geojson = json.loads(path.read_text(encoding="utf-8"))
    return [
        (feature["properties"]["WardName"], shape(feature["geometry"]))
        for feature in geojson["features"]
    ]


def lookup_postcode_row(
    postcode: str,
    codepoint_csv_path: Path = CODEPOINT_CSV_PATH,
) -> tuple[str, int, int]:
    """Return the normalized postcode and BNG coordinates from a Code-Point CSV."""
    target_postcode = normalize_postcode(postcode)

    with codepoint_csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            if row[0].lower() == "postcode":
                continue
            if normalize_postcode(row[0]) != target_postcode:
                continue
            return target_postcode, int(row[2]), int(row[3])

    raise ValueError(f"Postcode '{postcode}' was not found in {codepoint_csv_path}.")


def lookup_postcode_in_oxford_wards(
    postcode: str,
    codepoint_csv_path: Path = CODEPOINT_CSV_PATH,
    boundaries_path: Path = BOUNDARIES_PATH,
) -> PostcodeLookupResult:
    """Resolve a postcode to lat/lon and the containing Oxford ward, if any."""
    normalized_postcode, easting, northing = lookup_postcode_row(
        postcode,
        codepoint_csv_path=codepoint_csv_path,
    )
    longitude, latitude = BNG_TO_WGS84.transform(easting, northing)
    point = Point(longitude, latitude)

    ward_name = None
    for candidate_ward_name, ward_geometry in load_ward_boundaries(boundaries_path):
        if ward_geometry.covers(point):
            ward_name = candidate_ward_name
            break

    return PostcodeLookupResult(
        postcode=postcode,
        normalized_postcode=normalized_postcode,
        latitude=latitude,
        longitude=longitude,
        easting=easting,
        northing=northing,
        ward_name=ward_name,
    )

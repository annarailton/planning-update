"""Postcode-to-ward lookup helpers for local Oxford boundary data."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

from ..constants import BOUNDARIES_PATH, CODEPOINT_CSV_PATH, PARISH_BOUNDARIES_PATH
from .location_lookup import normalize_name

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
WGS84_TO_BNG = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)


@dataclass(frozen=True)
class PostcodeLookupResult:
    """Resolved postcode coordinates and containing Oxford boundaries."""

    postcode: str
    normalized_postcode: str
    latitude: float
    longitude: float
    easting: int
    northing: int
    ward_name: str | None
    parish_name: str | None


def normalize_postcode(postcode: str) -> str:
    """Normalize a postcode for file matching, removing whitespace and uppercasing.

    Examples:
        >>> normalize_postcode("OX1 4AQ")
        'OX14AQ'
        >>> normalize_postcode(" ox1   4aq ")
        'OX14AQ'
    """
    return re.sub(r"\s+", "", postcode).upper()


@lru_cache(maxsize=None)
def load_ward_boundaries(path: Path = BOUNDARIES_PATH) -> list[tuple[str, object]]:
    """Load ward shapes from the checked-in Oxford GeoJSON file."""
    geojson = json.loads(path.read_text(encoding="utf-8"))
    return [
        (feature["properties"]["WardName"], shape(feature["geometry"]))
        for feature in geojson["features"]
    ]


@lru_cache(maxsize=None)
def load_parish_boundaries(
    path: Path = PARISH_BOUNDARIES_PATH,
) -> list[tuple[str, object]]:
    """Load parish shapes from the checked-in Oxford GeoJSON file."""
    geojson = json.loads(path.read_text(encoding="utf-8"))
    return [
        (feature["properties"]["PARNCP24NM"], shape(feature["geometry"]))
        for feature in geojson["features"]
    ]


@lru_cache(maxsize=None)
def load_ward_boundaries_bng(path: Path = BOUNDARIES_PATH) -> dict[str, object]:
    """Load ward shapes transformed into British National Grid coordinates."""
    return {
        normalize_name(ward_name): transform(WGS84_TO_BNG.transform, ward_geometry)
        for ward_name, ward_geometry in load_ward_boundaries(path)
    }


@lru_cache(maxsize=None)
def load_parish_boundaries_bng(
    path: Path = PARISH_BOUNDARIES_PATH,
) -> dict[str, object]:
    """Load parish shapes transformed into British National Grid coordinates."""
    return {
        normalize_name(parish_name): transform(WGS84_TO_BNG.transform, parish_geometry)
        for parish_name, parish_geometry in load_parish_boundaries(path)
    }


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
    parish_boundaries_path: Path = PARISH_BOUNDARIES_PATH,
) -> PostcodeLookupResult:
    """Resolve a postcode to lat/lon and the containing Oxford boundaries.

    These can be a ward, a parish, both, or neither depending on where the postcode lies.
    """
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

    parish_name = None
    for candidate_parish_name, parish_geometry in load_parish_boundaries(
        parish_boundaries_path
    ):
        if parish_geometry.covers(point):
            parish_name = candidate_parish_name
            break

    return PostcodeLookupResult(
        postcode=postcode,
        normalized_postcode=normalized_postcode,
        latitude=latitude,
        longitude=longitude,
        easting=easting,
        northing=northing,
        ward_name=ward_name,
        parish_name=parish_name,
    )


def postcode_is_within_ward_distance(
    postcode: str,
    ward_name: str,
    *,
    distance_meters: float,
    codepoint_csv_path: Path = CODEPOINT_CSV_PATH,
    boundaries_path: Path = BOUNDARIES_PATH,
) -> bool:
    """Return whether a postcode lies inside or near an Oxford ward boundary."""
    _, easting, northing = lookup_postcode_row(
        postcode,
        codepoint_csv_path=codepoint_csv_path,
    )
    ward_geometry = load_ward_boundaries_bng(boundaries_path).get(
        normalize_name(ward_name)
    )
    if ward_geometry is None:
        raise ValueError(f"Unknown ward boundary '{ward_name}'.")

    postcode_point = Point(easting, northing)
    if distance_meters <= 0:
        return ward_geometry.covers(postcode_point)

    return ward_geometry.buffer(distance_meters).covers(postcode_point)


def postcode_is_within_parish_distance(
    postcode: str,
    parish_name: str,
    *,
    distance_meters: float,
    codepoint_csv_path: Path = CODEPOINT_CSV_PATH,
    boundaries_path: Path = PARISH_BOUNDARIES_PATH,
) -> bool:
    """Return whether a postcode lies inside or near an Oxford parish boundary."""
    _, easting, northing = lookup_postcode_row(
        postcode,
        codepoint_csv_path=codepoint_csv_path,
    )
    parish_geometry = load_parish_boundaries_bng(boundaries_path).get(
        normalize_name(parish_name)
    )
    if parish_geometry is None:
        raise ValueError(f"Unknown parish boundary '{parish_name}'.")

    postcode_point = Point(easting, northing)
    if distance_meters <= 0:
        return parish_geometry.covers(postcode_point)

    return parish_geometry.buffer(distance_meters).covers(postcode_point)

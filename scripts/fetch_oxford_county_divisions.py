"""Fetch and store Oxford county division boundaries.

This is intended as a one-off bootstrap script for checking the county division
polygons into the repository. It writes the filtered GeoJSON plus a small
metadata file so we retain the source, filter, and fetch date alongside the
data.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests
from shapely.geometry import shape
from shapely.ops import unary_union

BOUNDARIES_DIR = Path("data") / "boundaries"
CITY_WARDS_PATH = BOUNDARIES_DIR / "oxford_city_wards.geojson"
GEOJSON_PATH = BOUNDARIES_DIR / "oxford_city_county_divisions.geojson"
METADATA_PATH = BOUNDARIES_DIR / "oxford_city_county_divisions.metadata.json"
SOURCE_SERVICE_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "CED_MAY_2025_EN_BFE/FeatureServer"
)
SOURCE_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "CED_MAY_2025_EN_BFE/FeatureServer/0/query"
)
QUERY_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "outSR": "4326",
    "geometryType": "esriGeometryEnvelope",
    "inSR": "4326",
    "spatialRel": "esriSpatialRelIntersects",
}
REQUEST_TIMEOUT_SECONDS = 30
MIN_CITY_INTERSECTION_AREA = 0.000001


def normalize_division_name(name: str) -> str:
    """Return the display name used for checked-in county divisions."""
    return name.removesuffix(" ED")


def parse_args() -> argparse.Namespace:
    """Parse command-line flags."""
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Oxfordshire county divisions overlapping Oxford city and "
            "store them in the repo."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files instead of treating this as a one-off fetch.",
    )
    return parser.parse_args()


def load_oxford_city_boundary() -> object:
    """Load Oxford city as the union of the checked-in city ward boundaries."""
    payload = json.loads(CITY_WARDS_PATH.read_text(encoding="utf-8"))
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("Oxford ward boundary file did not include any features.")

    return unary_union([shape(feature["geometry"]) for feature in features])


def build_query_params(city_boundary: object) -> dict[str, str]:
    """Build the ArcGIS query for divisions near Oxford city."""
    minx, miny, maxx, maxy = city_boundary.bounds
    return {
        **QUERY_PARAMS,
        "geometry": f"{minx},{miny},{maxx},{maxy}",
    }


def fetch_geojson() -> dict[str, object]:
    """Download county division GeoJSON from the ONS ArcGIS endpoint."""
    city_boundary = load_oxford_city_boundary()
    response = requests.get(
        SOURCE_URL,
        params=build_query_params(city_boundary),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("type") != "FeatureCollection":
        raise ValueError(
            "County division boundary response was not a GeoJSON FeatureCollection."
        )

    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError(
            "County division boundary response did not include any features."
        )

    return payload


def filter_to_oxford_city(geojson: dict[str, object]) -> dict[str, object]:
    """Keep county divisions that overlap the Oxford city boundary."""
    city_boundary = load_oxford_city_boundary()
    features = geojson["features"]
    filtered_features = []

    for feature in features:
        feature["properties"]["NAME"] = normalize_division_name(
            str(feature["properties"]["CED25NM"])
        )
        division_geometry = shape(feature["geometry"])
        if (
            division_geometry.intersection(city_boundary).area
            >= MIN_CITY_INTERSECTION_AREA
        ):
            filtered_features.append(feature)

    if not filtered_features:
        raise ValueError("No county divisions overlapped the Oxford city boundary.")

    return {
        "type": "FeatureCollection",
        "features": filtered_features,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    """Write JSON atomically to avoid partial files."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)

    temp_path.replace(path)


def build_metadata(*, geojson: dict[str, object]) -> dict[str, object]:
    """Build a small provenance record for the checked-in boundary file."""
    features = geojson["features"]
    division_names = sorted(str(feature["properties"]["NAME"]) for feature in features)
    return {
        "source_service_url": SOURCE_SERVICE_URL,
        "source_url": SOURCE_URL,
        "query_params": build_query_params(load_oxford_city_boundary()),
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "feature_count": len(features),
        "division_names": division_names,
        "filter": (
            "County divisions with meaningful intersection against "
            f"{CITY_WARDS_PATH}; tiny edge slivers below "
            f"{MIN_CITY_INTERSECTION_AREA} square degrees are ignored."
        ),
        "notes": (
            "Oxford county division boundaries filtered from ONS Open Geography "
            "County Electoral Division (May 2025) Boundaries EN BFE."
        ),
    }


def main() -> None:
    """Fetch the county division GeoJSON and write it into the repository."""
    args = parse_args()

    if not args.force and (GEOJSON_PATH.exists() or METADATA_PATH.exists()):
        raise SystemExit(
            "Boundary files already exist. Re-run with --force to refresh them."
        )

    geojson = filter_to_oxford_city(fetch_geojson())
    feature_count = len(geojson["features"])

    write_json(GEOJSON_PATH, geojson)
    write_json(METADATA_PATH, build_metadata(geojson=geojson))

    print(f"Stored {feature_count} Oxford county division boundaries at {GEOJSON_PATH}")
    print(f"Stored source metadata at {METADATA_PATH}")


if __name__ == "__main__":
    main()

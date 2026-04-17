"""Fetch and store the current Oxford city parish boundaries.

This is intended as a one-off bootstrap script for checking the parish polygons
into the repository. It writes the filtered GeoJSON plus a small metadata file
so we retain the source and fetch date alongside the data.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests

BOUNDARIES_DIR = Path("data") / "boundaries"
GEOJSON_PATH = BOUNDARIES_DIR / "oxford_city_parishes.geojson"
METADATA_PATH = BOUNDARIES_DIR / "oxford_city_parishes.metadata.json"
SOURCE_URL = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Parishes_and_Non_Civil_Parished_Areas_December_2024_Boundaries_EW_BGC/"
    "FeatureServer/0/query"
)
PARISH_NAMES = (
    "Blackbird Leys",
    "Littlemore",
    "Old Marston",
    "Risinghurst and Sandhills",
)
QUERY_PARAMS = {
    "where": (
        "PARNCP24NM IN ('Blackbird Leys','Littlemore',"
        "'Old Marston','Risinghurst and Sandhills')"
    ),
    "outFields": "*",
    "f": "geojson",
}
REQUEST_TIMEOUT_SECONDS = 30


def parse_args() -> argparse.Namespace:
    """Parse command-line flags."""
    parser = argparse.ArgumentParser(
        description="Fetch Oxford city parish boundaries and store them in the repo."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files instead of treating this as a one-off fetch.",
    )
    return parser.parse_args()


def fetch_geojson() -> dict[str, object]:
    """Download the Oxford parish GeoJSON subset from the ONS ArcGIS endpoint."""
    response = requests.get(
        SOURCE_URL,
        params=QUERY_PARAMS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("type") != "FeatureCollection":
        raise ValueError(
            "Oxford parish boundary response was not a GeoJSON FeatureCollection."
        )

    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError(
            "Oxford parish boundary response did not include any features."
        )

    fetched_parishes = {feature["properties"]["PARNCP24NM"] for feature in features}
    if fetched_parishes != set(PARISH_NAMES):
        raise ValueError(
            "Oxford parish boundary response did not match the expected four parishes."
        )

    return payload


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


def build_metadata(*, feature_count: int) -> dict[str, object]:
    """Build a small provenance record for the checked-in boundary file."""
    return {
        "source_url": SOURCE_URL,
        "query_params": QUERY_PARAMS,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "feature_count": feature_count,
        "parish_names": list(PARISH_NAMES),
        "notes": (
            "Oxford city parish boundaries filtered from the ONS Parishes and "
            "Non Civil Parished Areas (December 2024) Boundaries EW BGC dataset."
        ),
    }


def main() -> None:
    """Fetch the parish GeoJSON and write it into the repository."""
    args = parse_args()

    if not args.force and (GEOJSON_PATH.exists() or METADATA_PATH.exists()):
        raise SystemExit(
            "Boundary files already exist. Re-run with --force to refresh them."
        )

    geojson = fetch_geojson()
    feature_count = len(geojson["features"])

    write_json(GEOJSON_PATH, geojson)
    write_json(METADATA_PATH, build_metadata(feature_count=feature_count))

    print(f"Stored {feature_count} Oxford parish boundaries at {GEOJSON_PATH}")
    print(f"Stored source metadata at {METADATA_PATH}")


if __name__ == "__main__":
    main()

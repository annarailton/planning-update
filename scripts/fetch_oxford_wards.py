"""Fetch and store the current Oxford city ward boundaries.

This is intended as a one-off bootstrap script for checking the ward polygons
into the repository. It writes the live GeoJSON plus a small metadata file so
we retain the source and fetch date alongside the data.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests

BOUNDARIES_DIR = Path("data") / "boundaries"
GEOJSON_PATH = BOUNDARIES_DIR / "oxford_city_wards.geojson"
METADATA_PATH = BOUNDARIES_DIR / "oxford_city_wards.metadata.json"
SOURCE_URL = (
    "https://services-eu1.arcgis.com/tnmBQqa3VPEwVeKN/arcgis/rest/services/"
    "Oxford_Wards_2023/FeatureServer/0/query"
)
QUERY_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
}
REQUEST_TIMEOUT_SECONDS = 30


def parse_args() -> argparse.Namespace:
    """Parse command-line flags."""
    parser = argparse.ArgumentParser(
        description="Fetch Oxford city ward boundaries and store them in the repo."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files instead of treating this as a one-off fetch.",
    )
    return parser.parse_args()


def fetch_geojson() -> dict[str, object]:
    """Download the live ward GeoJSON from Oxford's ArcGIS endpoint."""
    response = requests.get(
        SOURCE_URL,
        params=QUERY_PARAMS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    if payload.get("type") != "FeatureCollection":
        raise ValueError(
            "Oxford ward boundary response was not a GeoJSON FeatureCollection."
        )

    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("Oxford ward boundary response did not include any features.")

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
        "notes": (
            "Current Oxford city ward boundaries fetched from Oxford City Council's "
            "ArcGIS FeatureServer endpoint."
        ),
    }


def main() -> None:
    """Fetch the ward GeoJSON and write it into the repository."""
    args = parse_args()

    if not args.force and (GEOJSON_PATH.exists() or METADATA_PATH.exists()):
        raise SystemExit(
            "Boundary files already exist. Re-run with --force to refresh them."
        )

    geojson = fetch_geojson()
    feature_count = len(geojson["features"])

    write_json(GEOJSON_PATH, geojson)
    write_json(METADATA_PATH, build_metadata(feature_count=feature_count))

    print(f"Stored {feature_count} Oxford ward boundaries at {GEOJSON_PATH}")
    print(f"Stored source metadata at {METADATA_PATH}")


if __name__ == "__main__":
    main()

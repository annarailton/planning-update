#!/usr/bin/env python3
"""Generate ERD diagram from SQLAlchemy models.

Usage:
    python scripts/generate_erd.py [output_file]

    output_file: Optional output path (default: docs/erd.png)
                 Supports: .png, .svg, .pdf, .dot

Examples:
    python scripts/generate_erd.py                    # docs/erd.png
    python scripts/generate_erd.py docs/erd.svg      # SVG format
    python scripts/generate_erd.py erd.pdf           # PDF format
"""

import sys
from pathlib import Path

# Add packages to path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from eralchemy2 import render_er
from packages.db import Base
# Import models to register them with Base
from packages.db.models import User, File, Bucket, Job  # noqa


def main():
    # Default output
    output = sys.argv[1] if len(sys.argv) > 1 else "docs/erd.png"
    output_path = Path(output)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating ERD from SQLAlchemy models...")
    print(f"  Models: User, File, Bucket, Job")
    print(f"  Output: {output_path}")

    # Generate ERD
    render_er(Base, str(output_path))

    print(f"\nDone! Open {output_path} to view your ERD.")


if __name__ == "__main__":
    main()

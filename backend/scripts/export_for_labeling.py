#!/usr/bin/env python
"""
Export a random sample of ingested HN comments to CSV for manual labeling.

Usage
-----
From the repo root (with the backend virtualenv active and DATABASE_URL set):

    python backend/scripts/export_for_labeling.py \
        --limit 300 \
        --output data/labeled_sample.csv

Or from inside backend/:

    python scripts/export_for_labeling.py --limit 300

The exported CSV has blank columns for stance, sentiment, toxicity, and notes.
Fill these in manually, then use evaluate_classifiers.py to measure accuracy.

Labeling guidelines
-------------------
stance    : SUPPORT | OPPOSE | MIXED | NEUTRAL  (relative to the thread subject)
            Off-topic comments → NEUTRAL
            Short comments (<15 words) → label but note in 'notes' column
sentiment : POSITIVE | NEUTRAL | NEGATIVE
toxicity  : 0 (none) | 1 (mild) | 2 (moderate) | 3 (severe)
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import sys
from pathlib import Path

# Allow running from the backend/ directory without installing the package.
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
sys.path.insert(0, str(_BACKEND))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export HN comments to a blank-label CSV for manual annotation."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=300,
        help="Number of comments to export (default: 300).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(_BACKEND.parent / "data" / "labeled_sample.csv"),
        help="Path to write the CSV file.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "ERROR: DATABASE_URL environment variable is not set.\n"
            "Example: export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname",
            file=sys.stderr,
        )
        sys.exit(1)

    # Deferred import — avoids triggering app.database engine creation before
    # DATABASE_URL is confirmed present.
    from sqlalchemy import create_engine  # noqa: PLC0415
    from sqlalchemy.orm import Session  # noqa: PLC0415

    from app.models import Comment, Post  # noqa: PLC0415

    engine = create_engine(database_url)

    with Session(engine) as db:
        # Fetch non-deleted comments that have a body
        rows = (
            db.query(
                Comment.id,
                Comment.external_id,
                Comment.topic_id,
                Comment.post_id,
                Comment.body,
                Post.target_terms,
            )
            .join(Post, Post.id == Comment.post_id)
            .filter(Comment.body.isnot(None))
            .filter(Comment.body != "")
            .all()
        )

    if not rows:
        print(
            "No eligible comments found in the database.\n"
            "Run at least one ingestion cycle first.",
            file=sys.stderr,
        )
        sys.exit(1)

    random.seed(args.seed)
    sample = random.sample(rows, min(args.limit, len(rows)))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "external_id",
        "topic_id",
        "post_id",
        "target_terms",
        "body",
        "stance",
        "sentiment",
        "toxicity",
        "notes",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sample:
            writer.writerow(
                {
                    "id": row.id,
                    "external_id": row.external_id,
                    "topic_id": row.topic_id,
                    "post_id": row.post_id,
                    "target_terms": row.target_terms or "",
                    "body": row.body,
                    "stance": "",
                    "sentiment": "",
                    "toxicity": "",
                    "notes": "",
                }
            )

    print(f"Exported {len(sample)} comments to: {output_path}")
    print()
    print("Labeling instructions:")
    print("  stance    : SUPPORT | OPPOSE | MIXED | NEUTRAL")
    print("              (relative to the thread subject; off-topic → NEUTRAL)")
    print("  sentiment : POSITIVE | NEUTRAL | NEGATIVE")
    print("  toxicity  : 0=none | 1=mild | 2=moderate | 3=severe")
    print("  notes     : optional free text (e.g. 'low-confidence, <15 words')")
    print()
    print("Label at least 200 rows, then run evaluate_classifiers.py.")


if __name__ == "__main__":
    main()

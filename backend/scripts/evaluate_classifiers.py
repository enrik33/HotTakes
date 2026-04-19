#!/usr/bin/env python
"""
Evaluate all three classifiers against a manually labeled CSV.

Usage
-----
    python backend/scripts/evaluate_classifiers.py \
        --input  data/labeled_sample.csv \
        --output reports/

Or from inside backend/:

    python scripts/evaluate_classifiers.py --input ../data/labeled_sample.csv

Input CSV must have at least these columns (produced by export_for_labeling.py):
    body, target_terms, stance, sentiment, toxicity

  stance    : SUPPORT | OPPOSE | MIXED | NEUTRAL
  sentiment : POSITIVE | NEUTRAL | NEGATIVE
  toxicity  : 0 | 1 | 2 | 3   (0=none, 3=severe)

Rows with empty labels in a column are skipped for that column's metric.

Output
------
A JSON file  reports/classification_report_<YYYYMMDD_HHMMSS>.json  containing:

  {
    "generated_at": "...",
    "n_evaluated": {"stance": 200, "sentiment": 200, "toxicity": 200},
    "stance": {
      "accuracy": 0.82,
      "per_class": {"SUPPORT": {"precision":…, "recall":…, "f1":…}, ...},
      "macro": {"precision":…, "recall":…, "f1":…},
      "micro": {"precision":…, "recall":…, "f1":…},
      "confusion_matrix": {"SUPPORT": {"SUPPORT": 45, "OPPOSE": 3, ...}, ...}
    },
    "sentiment": {
      "accuracy": 0.79,
      "per_class": {...},
      "macro": {...},
      "micro": {...}
    },
    "toxicity": {
      "mae": 0.12,
      "note": "Manual 0-3 scaled to [0.0, 1.0]; model scores are already [0.0, 1.0]."
    }
  }

Dependencies
------------
numpy, scikit-learn (already in requirements.txt)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
sys.path.insert(0, str(_BACKEND))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate sentiment / stance / toxicity classifiers against a labeled CSV."
    )
    parser.add_argument(
        "--input",
        default=str(_BACKEND.parent / "data" / "labeled_sample.csv"),
        help="Path to labeled CSV (default: data/labeled_sample.csv).",
    )
    parser.add_argument(
        "--output",
        default=str(_BACKEND.parent / "reports"),
        help="Output directory for the JSON report (default: reports/).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for model inference (default: 32).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Metric helpers — pure Python, no sklearn needed for the basic case
# ---------------------------------------------------------------------------


class _Metrics(NamedTuple):
    accuracy: float
    per_class: dict
    macro: dict
    micro: dict
    confusion: dict


def _classification_metrics(y_true: list[str], y_pred: list[str]) -> _Metrics:
    """Compute accuracy, per-class P/R/F1, macro, micro, and confusion matrix."""
    labels = sorted(set(y_true) | set(y_pred))

    # Confusion matrix: true → pred count
    cm: dict[str, dict[str, int]] = {lbl: defaultdict(int) for lbl in labels}
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) if y_true else 0.0

    per_class: dict[str, dict[str, float]] = {}
    sum_p = sum_r = sum_f = 0.0
    tp_total = fp_total = fn_total = 0

    for lbl in labels:
        tp = cm[lbl].get(lbl, 0)
        fp = sum(cm[other].get(lbl, 0) for other in labels if other != lbl)
        fn = sum(cm[lbl].get(other, 0) for other in labels if other != lbl)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        per_class[lbl] = {"precision": precision, "recall": recall, "f1": f1}
        sum_p += precision
        sum_r += recall
        sum_f += f1
        tp_total += tp
        fp_total += fp
        fn_total += fn

    n = len(labels)
    macro = {
        "precision": sum_p / n if n else 0.0,
        "recall": sum_r / n if n else 0.0,
        "f1": sum_f / n if n else 0.0,
    }
    micro_p = tp_total / (tp_total + fp_total) if (tp_total + fp_total) else 0.0
    micro_r = tp_total / (tp_total + fn_total) if (tp_total + fn_total) else 0.0
    micro_f = (
        2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0
    )
    micro = {"precision": micro_p, "recall": micro_r, "f1": micro_f}

    # Serialise confusion matrix (defaultdict → plain dict)
    cm_plain = {lbl: dict(cm[lbl]) for lbl in labels}

    return _Metrics(accuracy, per_class, macro, micro, cm_plain)


def _round_dict(d: dict, ndigits: int = 4) -> dict:
    return {k: round(v, ndigits) if isinstance(v, float) else v for k, v in d.items()}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    # Deferred import so the script can be invoked with --help without
    # requiring the full backend environment.
    from app.services.sentiment_service import (
        classify_sentiment_batch,
        reset_pipeline as reset_sent,
    )  # noqa: PLC0415
    from app.services.stance_classifier import (
        classify_stance_batch,
        reset_pipeline as reset_stance,
    )  # noqa: PLC0415
    from app.services.toxicity_service import (
        score_toxicity_batch,
        reset_pipeline as reset_tox,
    )  # noqa: PLC0415
    from app.services.stance_gate import split_target_terms  # noqa: PLC0415

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Load labeled CSV
    # ------------------------------------------------------------------
    rows: list[dict] = []
    with input_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("ERROR: CSV is empty.", file=sys.stderr)
        sys.exit(1)

    # Validate required columns
    required = {"body", "target_terms", "stance", "sentiment", "toxicity"}
    missing = required - set(rows[0].keys())
    if missing:
        print(f"ERROR: Missing columns in CSV: {missing}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Prepare subsets (only rows with non-empty labels)
    # ------------------------------------------------------------------

    def _valid(row: dict, col: str) -> bool:
        return bool(row.get(col, "").strip())

    stance_rows = [r for r in rows if _valid(r, "stance")]
    sentiment_rows = [r for r in rows if _valid(r, "sentiment")]
    toxicity_rows = [r for r in rows if _valid(r, "toxicity")]

    print(
        f"Loaded {len(rows)} rows. "
        f"Labeled: stance={len(stance_rows)}, "
        f"sentiment={len(sentiment_rows)}, "
        f"toxicity={len(toxicity_rows)}"
    )

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path),
        "n_evaluated": {
            "stance": len(stance_rows),
            "sentiment": len(sentiment_rows),
            "toxicity": len(toxicity_rows),
        },
    }

    # ------------------------------------------------------------------
    # Stance
    # ------------------------------------------------------------------
    if stance_rows:
        print("Running stance classifier…")
        bodies = [r["body"] for r in stance_rows]
        target_lists = [split_target_terms(r["target_terms"]) for r in stance_rows]
        y_true_stance = [r["stance"].strip().upper() for r in stance_rows]

        # Group by same target_terms to batch efficiently
        y_pred_stance: list[str] = []
        for body, targets in zip(bodies, target_lists):
            pred = classify_stance_batch([body], target_terms=targets, batch_size=1)
            y_pred_stance.extend(pred)

        reset_stance()
        m = _classification_metrics(y_true_stance, y_pred_stance)
        report["stance"] = {
            "accuracy": round(m.accuracy, 4),
            "per_class": {k: _round_dict(v) for k, v in m.per_class.items()},
            "macro": _round_dict(m.macro),
            "micro": _round_dict(m.micro),
            "confusion_matrix": m.confusion,
        }
        print(f"  stance accuracy = {m.accuracy:.1%}")

    # ------------------------------------------------------------------
    # Sentiment
    # ------------------------------------------------------------------
    if sentiment_rows:
        print("Running sentiment classifier…")
        bodies = [r["body"] for r in sentiment_rows]
        y_true_sent = [r["sentiment"].strip().upper() for r in sentiment_rows]
        y_pred_sent = classify_sentiment_batch(bodies, batch_size=args.batch_size)
        reset_sent()

        m = _classification_metrics(y_true_sent, y_pred_sent)
        report["sentiment"] = {
            "accuracy": round(m.accuracy, 4),
            "per_class": {k: _round_dict(v) for k, v in m.per_class.items()},
            "macro": _round_dict(m.macro),
            "micro": _round_dict(m.micro),
        }
        print(f"  sentiment accuracy = {m.accuracy:.1%}")

    # ------------------------------------------------------------------
    # Toxicity (regression — MAE)
    # ------------------------------------------------------------------
    if toxicity_rows:
        print("Running toxicity scorer…")
        bodies = [r["body"] for r in toxicity_rows]
        # Manual labels are 0-3; normalise to [0.0, 1.0] to compare with model output.
        y_true_tox_raw = [r["toxicity"].strip() for r in toxicity_rows]
        try:
            y_true_tox = [int(v) / 3.0 for v in y_true_tox_raw]
        except ValueError as e:
            print(f"ERROR: Invalid toxicity label: {e}", file=sys.stderr)
            sys.exit(1)

        y_pred_tox = score_toxicity_batch(bodies, batch_size=args.batch_size)
        reset_tox()

        mae = sum(abs(t - p) for t, p in zip(y_true_tox, y_pred_tox)) / len(y_true_tox)
        report["toxicity"] = {
            "mae": round(mae, 4),
            "note": "Manual 0-3 scaled to [0.0, 1.0]; model scores are already [0.0, 1.0].",
        }
        print(f"  toxicity MAE = {mae:.4f}")

    # ------------------------------------------------------------------
    # Write report
    # ------------------------------------------------------------------
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"classification_report_{timestamp}.json"

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport written to: {report_path}")


if __name__ == "__main__":
    main()

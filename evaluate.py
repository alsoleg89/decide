"""Measure errors among accepted decisions against labels; never calls a model."""

import argparse
import json
import math
from pathlib import Path


def unique_rows(path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows):
        raise ValueError("Expected nonempty JSONL records with string IDs")
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate IDs")
    return by_id


def risk_coverage(records, labels, threshold, inputs=None):
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be 0..1")
    if not records or records.keys() != labels.keys():
        raise ValueError("Predictions and labels must have exactly the same nonempty set of IDs")
    sizes = None
    if inputs is not None:
        if inputs.keys() != records.keys() or any("content" not in row for row in inputs.values()):
            raise ValueError("Inputs must contain content and exactly match prediction IDs")
        sizes = {key: len(json.dumps({"id": key, "content": row["content"]},
                                    ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")) + 1
                 for key, row in inputs.items()}
    accepted, errors, failed = [], [], 0
    for key, row in records.items():
        expected = labels[key].get("expected")
        if not isinstance(expected, str) or not expected:
            raise ValueError("Every label must have a nonempty expected string")
        if "error" in row:
            failed += 1
            continue
        confidence = row.get("confidence")
        if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence) or not 0 <= confidence <= 1
            or not isinstance(row.get("choice"), str) or not row["choice"]):
            raise ValueError("Invalid prediction")
        if confidence >= threshold and row.get("reason") != "review_label":
            accepted.append(key)
            if row["choice"] != expected:
                errors.append(key)
    result = {
        "threshold": threshold, "total": len(records), "accepted": len(accepted),
        "review": len(records) - len(accepted), "failed": failed,
        "review_fraction": (len(records) - len(accepted)) / len(records),
        "accepted_errors": len(errors),
        "accepted_error_rate": len(errors) / len(accepted) if accepted else None,
        "accepted_error_ids": errors,
    }
    if sizes is not None:
        total_bytes = sum(sizes.values())
        accepted_bytes = sum(sizes[key] for key in accepted)
        result["input_jsonl_bytes"] = total_bytes
        result["review_input_jsonl_bytes"] = total_bytes - accepted_bytes
        result["input_bytes_kept_out_of_review_fraction"] = accepted_bytes / total_bytes
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, required=True, help="JSONL: {id, expected}")
    parser.add_argument("--results", type=Path, required=True, help="decide results.jsonl")
    parser.add_argument("--inputs", type=Path, help="Optional original {id, content} JSONL for input-byte accounting")
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--max-review-fraction", type=float)
    parser.add_argument("--max-accepted-error-rate", type=float)
    args = parser.parse_args()
    for value in [args.threshold, args.max_review_fraction, args.max_accepted_error_rate]:
        if value is not None and not 0 <= value <= 1:
            parser.error("Threshold and rate limits must be finite numbers in 0..1")
    try:
        records, labels = unique_rows(args.results), unique_rows(args.labels)
        inputs = unique_rows(args.inputs) if args.inputs else None
        result = risk_coverage(records, labels, args.threshold, inputs)
        result["threshold_sweep"] = [risk_coverage(records, labels, value, inputs)
                                     for value in [0, 0.5, 0.8, 0.9, 0.95, 0.99, 1]]
    except (ValueError, OSError) as error:
        parser.error(str(error))
    if args.inputs:
        result["byte_measurement"] = ("Canonical UTF-8 {id,content} JSONL bytes routed away from review; "
                                      "excludes rubric, summary, decision metadata and agent reasoning. "
                                      "Not end-to-end savings or billed tokens.")
    passed = result["failed"] == 0
    if args.max_review_fraction is not None:
        passed &= result["review_fraction"] <= args.max_review_fraction
    if args.max_accepted_error_rate is not None:
        passed &= result["accepted_error_rate"] is not None and result["accepted_error_rate"] <= args.max_accepted_error_rate
    has_limits = args.max_review_fraction is not None or args.max_accepted_error_rate is not None
    result["limits_met"] = passed if has_limits else None
    result["limits"] = {"max_review_fraction": args.max_review_fraction,
                        "max_accepted_error_rate": args.max_accepted_error_rate}
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

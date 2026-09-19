"""Reproducible synthetic throughput/routing check, offline unless --live is set."""

import argparse
import asyncio
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import httpx2 as httpx
from mcp import Client

import decide as app

LOGS = [
    ("normal", "INFO healthcheck passed HTTP 200 latency=12ms"),
    ("normal", "INFO backup completed successfully; all checksums verified"),
    ("normal", "INFO job processed successfully; queue empty"),
    ("investigate", "WARN query took 4s; request completed; latency above normal"),
    ("investigate", "WARN cache misses increased; performance degraded; service available"),
    ("investigate", "WARN background job failed; queued for retry; other workers healthy"),
    ("urgent", "CRITICAL all API instances down; every customer request fails"),
    ("urgent", "CRITICAL database disk full; all writes failing; immediate action required"),
    ("urgent", "CRITICAL checksum mismatch confirms unrecoverable customer data loss"),
    (None, "worker ended; status unknown"),
]
FILES = [
    ("test", "import unittest\n\nclass TestAddition(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(1 + 1, 2)\n"),
    ("configuration", 'SERVICE_NAME = "worker"\nPORT = 8080\nLOG_LEVEL = "INFO"\n'),
    ("implementation", "def total_price(items):\n    return sum(item['price'] * item['quantity'] for item in items)\n"),
]


def metrics(result, records, gold, inline_bytes, call_bytes, review_records=None):
    labeled = [row for row in records if gold[row["id"]] is not None]
    accepted = [row for row in labeled if row["status"] == "accepted"]
    correct = lambda rows: sum(row.get("choice") == gold[row["id"]] for row in rows)
    returned_bytes = len(app.encode(result).encode())
    review_bytes = (sum(len(app.encode(row).encode()) + 1 for row in review_records)
                    if review_records is not None else None)
    return {
        "items": result["total"], "completed": result["completed"],
        "accepted": result["accepted"], "review_count": result["review_count"],
        "review_fraction": result["review_fraction"], "failed": result["failed"],
        "elapsed_seconds": result["elapsed_seconds"],
        "items_per_second": round(result["total"] / max(result["elapsed_seconds"], 0.001), 2),
        "requests_made": result["requests_made"], "retries": result["retries"],
        "models": dict(Counter(row.get("model", "unavailable") for row in records)),
        "provider_usage": result["usage"], "labeled_items": len(labeled),
        "correct_labeled_items": correct(labeled),
        "label_accuracy": correct(labeled) / len(labeled) if labeled else None,
        "accepted_labeled_items": len(accepted),
        "accepted_label_accuracy": correct(accepted) / len(accepted) if accepted else None,
        "accepted_unlabeled_items": sum(row["status"] == "accepted" and gold[row["id"]] is None for row in records),
        "inline_input_bytes": inline_bytes,
        "source_call_and_result_bytes": call_bytes + returned_bytes,
        "context_bytes_reduction": 1 - (call_bytes + returned_bytes) / inline_bytes,
        "all_review_records_bytes": review_bytes,
        "context_bytes_reduction_with_all_reviews": (
            1 - (call_bytes + returned_bytes + review_bytes) / inline_bytes
            if review_bytes is not None else None),
    }


async def run(kind, count, live, concurrency, threshold):
    with tempfile.TemporaryDirectory(prefix="decide-bench-") as temp:
        root = Path(temp)
        gold, inputs = {}, []
        if kind == "lines":
            for index in range(count):
                label, content = LOGS[index % len(LOGS)]
                row = {"id": f"app.log:{index + 1}", "content": f"event={index:06d} {content}"}
                inputs.append(row)
                gold[row["id"]] = label
            (root / "app.log").write_text("\n".join(row["content"] for row in inputs), encoding="utf-8")
            source = {"kind": "lines", "paths": ["app.log"]}
            criteria = {"normal": "Routine successful operation", "investigate": "Noncritical warning or failure needing investigation",
                        "urgent": "Outage or data loss requiring immediate intervention", "unknown": "Insufficient information to classify"}
            question = "Which operational category fits this log entry?"
        else:
            folder = root / "src"
            folder.mkdir()
            for index in range(count):
                label, content = FILES[index % len(FILES)]
                path = str(Path("src") / f"module_{index:04d}.py")
                content = f"# Module {index}\n" + content
                (root / path).write_text(content, encoding="utf-8")
                inputs.append({"id": path, "content": content})
                gold[path] = label
            source = {"kind": "files", "paths": ["src/*.py"]}
            criteria = {"test": "Automated tests and assertions", "configuration": "Application settings and constants",
                        "implementation": "Application business logic", "unknown": "Insufficient information to classify"}
            question = "What is the primary purpose of this Python file?"
        arguments = {"question": question, "criteria": criteria, "source": source,
                     "concurrency": concurrency, "confidence_threshold": threshold, "review_labels": ["unknown"]}
        factory = httpx.AsyncClient

        def mock_response(request):
            item = json.loads(request.content)["state"]["item"]
            label = gold[item["id"]] or "unknown"
            return httpx.Response(200, json={"model": "mock-not-jev", "answers": {"decision": {
                "type": "choice", "choice": label, "confidence": 0.95,
                "probabilities": {key: float(key == label) for key in criteria},
            }}, "usage": {"input_tokens": 0, "output_tokens": 0}})

        provider = nullcontext() if live else patch.object(app.httpx, "AsyncClient", side_effect=lambda **kw:
            factory(**kw, transport=httpx.MockTransport(mock_response)))
        environment = {"DECIDE_ROOT": str(root)}
        if not live:
            environment["TYPESAFE_API_KEY"] = "offline-mock"
        with patch.dict(os.environ, environment), provider:
            async with Client(app.mcp, read_timeout_seconds=3600) as client:
                call = await client.call_tool("decide", arguments)
                if call.is_error:
                    raise RuntimeError(str(call.content))
                result = call.structured_content
        records = [json.loads(line) for line in Path(result["results_path"]).read_text(encoding="utf-8").split("\n") if line.strip()]
        reviews = [json.loads(line) for line in Path(result["review_path"]).read_text(encoding="utf-8").split("\n") if line.strip()]
        inline_arguments = {**arguments, "items": inputs}
        del inline_arguments["source"]
        return {"schema_version": 2, "mode": "live" if live else "mock",
                "kind": kind, "created_at": datetime.now(timezone.utc).isoformat(),
                "concurrency": concurrency, "confidence_threshold": threshold,
                "dataset": "Deterministic synthetic templates; not representative real-world accuracy",
                "measurement": "Serialized JSON bytes, not tokens; full-review metric counts every review row including already-previewed rows; excludes MCP framing and host-specific duplication",
                **metrics(result, records, gold, len(app.encode(inline_arguments).encode()),
                          len(app.encode(arguments).encode()), reviews)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Send synthetic data to the paid Jev API")
    parser.add_argument("--kind", choices=["lines", "files"], default="lines")
    parser.add_argument("--items", type=int, default=2000)
    parser.add_argument("--concurrency", type=int, choices=range(1, 17), default=4)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.items <= app.MAX_ITEMS:
        parser.error("--items must be 1..10000")
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be 0..1")
    if args.live and not os.environ.get("TYPESAFE_API_KEY"):
        os.environ["TYPESAFE_API_KEY"] = getpass.getpass("TypeSafe API key: ")
    report = asyncio.run(run(args.kind, args.items, args.live, args.concurrency, args.threshold))
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

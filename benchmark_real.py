"""Evaluate a labeled JSONL batch through the real MCP stdio server (paid Jev calls)."""

import argparse
import asyncio
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys

from mcp import Client, StdioServerParameters

import benchmark
import decide
from evaluate import risk_coverage, unique_rows


async def run(root, rubric_path, labels_path):
    arguments = json.loads(rubric_path.read_text(encoding="utf-8"))
    source = decide.Source.model_validate(arguments.get("source"))
    if source.kind != "jsonl" or "items" in arguments:
        raise ValueError("Real-data benchmark requires a JSONL source, not inline items")
    inputs = {row.id: row.model_dump() for row in decide.load_items(None, source, root)}
    labels = unique_rows(labels_path)
    if inputs.keys() != labels.keys() or any(not isinstance(row.get("expected"), str)
                                          or not row["expected"] for row in labels.values()):
        raise ValueError("Valid labels must exactly match input IDs before paid inference")
    if any(row["expected"] not in arguments["criteria"] for row in labels.values()):
        raise ValueError("Reference labels must be present in criteria")
    server_hash = hashlib.sha256(Path(decide.__file__).read_bytes()).hexdigest()
    environment = {**os.environ, "DECIDE_ROOT": str(root)}
    if not environment.get("TYPESAFE_API_KEY"):
        environment["TYPESAFE_API_KEY"] = getpass.getpass("TypeSafe API key: ")
    server = StdioServerParameters(command=sys.executable, args=[str(Path(decide.__file__).resolve())],
                                   env=environment)
    async with Client(server, read_timeout_seconds=3600) as client:
        call = await client.call_tool("decide", arguments)
        if call.is_error:
            raise RuntimeError(str(call.content))
        summary = call.structured_content
    records = unique_rows(Path(summary["results_path"]))
    reviews = [json.loads(line) for line in Path(summary["review_path"]).read_text(encoding="utf-8").split("\n") if line.strip()]
    inline = {**arguments, "items": list(inputs.values())}
    del inline["source"]
    measured = benchmark.metrics(summary, list(records.values()), {key: row["expected"] for key, row in labels.items()},
                                 len(decide.encode(inline).encode()), len(decide.encode(arguments).encode()), reviews)
    input_bytes = "".join(decide.encode(row) + "\n" for row in inputs.values()).encode()
    report = {"schema_version": 2, "mode": "live", "transport": "MCP stdio subprocess", "server_source_sha256": server_hash,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "input_jsonl_sha256": hashlib.sha256(input_bytes).hexdigest(),
              "rubric_sha256": hashlib.sha256(rubric_path.read_bytes()).hexdigest(),
              "rubric": arguments, "results_path": summary["results_path"],
              "measurement": "UTF-8 JSON bytes, not billed tokens. Full-review metric includes every full review row, even already-previewed rows. Excludes MCP framing, host duplication and agent reasoning.",
              **measured,
              "threshold_sweep": [risk_coverage(records, labels, threshold, inputs)
                                  for threshold in [0, 0.5, 0.8, 0.9, 0.95, 0.99, 1]]}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Directory containing input JSONL")
    parser.add_argument("--rubric", type=Path, required=True, help="Tool arguments JSON, including source")
    parser.add_argument("--labels", type=Path, required=True, help="Reference {id, expected} JSONL; never sent to Jev")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(run(args.root.resolve(), args.rubric, args.labels))
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["items", "accepted", "review_count", "failed",
        "elapsed_seconds", "context_bytes_reduction_with_all_reviews", "results_path"]}, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

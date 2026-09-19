# Reproduce the benchmarks

These are **synthetic integration benchmarks**, not representative accuracy
evaluations. They test the actual batching, routing, error accounting and compact
result contract. The live runs use Jev; offline runs replace only the HTTP endpoint.

## Recorded live results

Jev 1.13.0, 2026-09-19, concurrency 4, confidence threshold 0.8:

| Measurement | 2,000 log lines | 300 Python files |
| --- | ---: | ---: |
| Elapsed | 153.341 s | 28.544 s |
| Throughput | 13.04 items/s | 10.51 items/s |
| Accepted | 1,800 | 300 |
| Sent to review | 200 | 0 |
| Failed / retries | 0 / 0 | 0 / 0 |
| Provider input tokens | 843,493 | 128,390 |
| Provider output tokens | 98,400 | 13,500 |
| Inline input JSON | 209,304 bytes | 43,901 bytes |
| Source call + compact result | 8,536 bytes | 1,086 bytes |
| Reduction in JSON bytes | 95.92% | 97.53% |

Full machine-readable reports: [logs](live-lines-2000.json),
[files](live-files-300.json). Token counts are provider-reported usage; there is
no verified invoice or dollar cost estimate here.

## Run locally

From the repository root, after `uv sync --locked`:

```sh
# Free: deterministic mocked provider, real MCP SDK and file handling.
uv run --locked python benchmark.py --items 2000
uv run --locked python benchmark.py --kind files --items 300

# Paid: synthetic content is sent to TypeSafe Jev.
# Reads TYPESAFE_API_KEY, or prompts without echoing it.
uv run --locked python benchmark.py --live --items 2000 --output /tmp/live-lines.json
uv run --locked python benchmark.py --live --kind files --items 300 --output /tmp/live-files.json
```

Use `--concurrency 1..16` and `--threshold 0..1` to compare throughput and review
rates. Set `DECIDE_MODEL` to a pinned model for reproducibility. Reports identify
whether the endpoint was `live` or `mock`, and name models returned by the provider.
Temporary input files and raw decisions are cleaned up; `--output` retains only
the aggregate report. The script exits with a nonzero code if any item failed.

## What the numbers mean

The log generator cycles through nine clear templates and one ambiguous template.
The 200 ambiguous records are **unlabeled**, and are excluded from classification
accuracy. The 1,800 labeled examples all matched their synthetic labels; the file
generator similarly repeats three simple templates. Template repetition is easy
for a classifier. Those results do not imply 100% accuracy on production logs,
large repositories, adversarial inputs or unfamiliar taxonomies.

`label_accuracy` includes failed labeled items in the denominator.
`accepted_label_accuracy` only describes accepted labeled items;
`accepted_unlabeled_items` separately exposes accepted inputs without ground truth.
A subset with no labels reports `null`, never a fabricated 100%.

The context comparison measures serialized **JSON bytes**, not model tokens. It
compares passing all inline items with passing paths plus the compact structured
result. It excludes MCP framing, host-specific text/structured-output duplication,
tool schema overhead, and later reads of omitted reviews. If the orchestrator
reads every omitted review, include those reads in your own end-to-end measurement.
The scripts use the in-process MCP client; the test suite separately verifies a
real stdio subprocess. Elapsed time covers provider processing and result writes,
not package startup or initial source loading.

Before selecting a production threshold, evaluate a representative held-out,
labeled dataset, including wrong-but-confident cases. These two runs demonstrate
integration and scale, not the aspirational 95% automation or ten-cent budget.

# Measure context savings and decision quality

Start with the [UX and developer workflows](workflows/README.md): four feedback
extraction tasks on 500 app reviews, plus issue triage across five projects.
The protocol freezes 3,500 decisions before inference; results include accepted
mistakes, missed UX signals, review volume, local baselines and known costs.

The [10-task, 5,570-record evaluation](multitask/README.md) measures decision
accuracy, errors among accepted results, trained local baselines, costs and 70
threshold comparisons. It includes both useful and poor results, and quantifies
how compact review records improve context savings.

The [2,770-record follow-up](multitask/followup/RESULTS.md) uses new records with
thresholds and inputs committed before inference. It reports live quality and
context results for three tasks, retaining every failed response.

The [provider-response investigation](multitask/rejection-diagnostics/README.md)
explains 23 reproduced validation failures and measures the errors that relaxing
validation would admit.

The [GPT-4.1 mini comparison](cascade/gpt-4.1-mini/README.md) measures final
quality and actual token-based costs for the full-model baseline versus Jev plus
paid review. It includes losing scenarios and rejected output batches.

Then read the [threshold-selection validation](multitask/threshold-validation/README.md):
60 retrospective checks separate threshold selection from scoring and show
when an observed error rate fails to transfer to the held-out partition.

Earlier exploratory runs: [500 VS Code issues](vscode-500/README.md) and
[400 AG News articles](ag-news-400/README.md).

The log/file runs below are **synthetic integration benchmarks**, not representative accuracy
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
| Initial reduction in JSON bytes | 95.92% | 97.53% |

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

## Benchmark your own labeled data

`benchmark_real.py` runs the actual MCP server as a stdio subprocess. Unlike the
synthetic script, it always calls the paid Jev endpoint. Prepare three files:

- Input JSONL: `{"id":"ticket-1","content":"..."}` in the source directory.
- Label JSONL: `{"id":"ticket-1","expected":"bug"}` for every input ID.
- Rubric JSON: the `decide` tool arguments, including a JSONL `source` and criteria.

```sh
uv run --locked python benchmark_real.py \
  --root /absolute/path/to/data --rubric rubric.json --labels labels.jsonl \
  --output report.json
```

Labels are checked locally and never sent to Jev. The key comes from
`TYPESAFE_API_KEY` or a hidden prompt. The report records hashes, provider usage,
classification quality, the initial JSON reduction and the reduction including
**every full review record**. Full decisions remain at the reported `results_path`.

For offline threshold comparisons, add `--inputs items.jsonl` to `evaluate.py`.
`input_bytes_kept_out_of_review_fraction` weights records by their serialized
UTF-8 size; it is **input-only**, not the full-review metric. Use both the errors
and bytes to choose a useful threshold, then evaluate it on separate data.

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

Context comparisons measure serialized **JSON bytes**, not model tokens. New
reports (`schema_version: 2`) compare the full inline call, including the rubric,
with the path-based call plus the compact result. They also report
`all_review_records_bytes` and `context_bytes_reduction_with_all_reviews`, which
include reading every full review row, even rows already previewed. Savings can
be negative when the review overhead exceeds the inline input.

The recorded synthetic live reports above use version 1: their baseline includes
only inline items and their reduction covers only the initial call and result.
They have no full-review measurement and should not be read as end-to-end savings.
All versions exclude MCP framing, host-specific text/structured-output duplication,
tool schema overhead and the agent's reasoning.
The scripts use the in-process MCP client; the test suite separately verifies a
real stdio subprocess. Elapsed time covers provider processing and result writes,
not package startup or initial source loading.

Before selecting a production threshold, evaluate a representative held-out,
labeled dataset, including wrong-but-confident cases. These two runs demonstrate
integration and scale. Optimize context savings subject to your quality needs;
there is no fixed percentage of cases that must be reviewed.

<div align="center">

# decide

### Your agent reasons. Jev sorts.

One MCP tool for bulk decisions over files, logs and JSONL.

[Get started](#get-started) · [Benchmarks](benchmarks/README.md) · [Tool reference](docs/usage.md) · [MIT](LICENSE)

</div>

Give your agent a path and a rubric. `decide` sends each record to
[Jev](https://docs.typesafe.ai/introduction), writes decisions locally, and returns
counts and paths. Your agent reviews the exceptions and processes the rest with code.

```text
Files + rubric → Jev → accepted decisions + review queue → your agent
```

**Keep bulk input out of the expensive agent's context.** Tune review to the
quality your task needs; there is no universal “review 5%” setting.

## Get started

You need [uv](https://docs.astral.sh/uv/) and a
[TypeSafe key](https://console.typesafe.ai). No clone or Git required: this
command installs the small release wheel, without the benchmark archive.

```sh
uvx --python 3.11 --from https://github.com/alsoleg89/decide/releases/download/v0.1.1/decide_mcp-0.1.1-py3-none-any.whl decide-mcp
```

Use it as your MCP client's launch command. Set `TYPESAFE_API_KEY` and
**`DECIDE_ROOT` to an absolute data-directory path** in the server environment.
Missing or relative roots are rejected before any files are read.
[Codex setup](docs/usage.md#codex) · [Claude setup](docs/usage.md#claude-code--claude-desktop) · [Verify the wheel](docs/usage.md#verify-the-downloaded-wheel)

Then ask your agent:

> Use decide on feedback.jsonl to find feature requests. Pass the path without
> reading the full file first. Use yes/no criteria, a global cutoff of 0 and a
> cutoff of 0.9 for no. Review every queued case, save one final label per ID,
> and verify complete coverage.

```json
{
  "question": "Does this review request a new or changed capability?",
  "criteria": {"yes": "Requests a new or changed capability", "no": "Does not"},
  "source": {"kind": "jsonl", "paths": ["feedback.jsonl"]},
  "confidence_threshold": 0,
  "confidence_thresholds": {"no": 0.9}
}
```

Each JSONL row is `{"id":"review-1","content":"Please add CSV export."}`.
The example uses the UX study's routing. Validate the rubric and cutoffs on your
own labeled sample; a confidence score is not a probability of correctness.

## What we measured

Real UX feedback and developer issue triage, with complete output files and
all model turns counted. Cost includes Jev, agent reading, tools, retained
history, writing and the final answer. These are guided API loops with
**25-record batches**, not native Codex/Claude sessions or optimized baselines;
larger standalone-model batches have not been compared.

| Task and reviewer | Total cost reduction | Accuracy: reviewer alone → decide + reviewer | Quality tradeoff |
| --- | ---: | ---: | --- |
| [1,000 new UX reviews / GPT-4.1 mini](benchmarks/agent/ux-recall/README.md) | **48.9%** | 84.2% → **90.2%** | Accuracy, macro-F1, feature precision and recall all improved |
| [300 OpenCV issues / GPT-4.1 mini](benchmarks/agent/gpt-4.1-mini/required-completion/README.md) | **77.3%** | 68.0% → **74.7%** | Observed feature recall −5 p.p.; 95% interval −11.01 to +0.89 |
| [Same UX reviews / Luna](benchmarks/agent/gpt-5.6-luna/README.md) | **32.8%** | 87.8% → **90.1%** | Feature recall fell by one correct request |
| [Same OpenCV issues / Luna](benchmarks/agent/gpt-5.6-luna/README.md) | **70.4%** | 74.7% → 74.7% | Bug and feature recall fell |

Luna used reasoning `none`. Both Luna policies failed the frozen all-metrics
quality gate. The mini UX accuracy gain has a paired 95% interval of +4 to +8
percentage points; [statistics and limitations](benchmarks/agent/ux-recall/statistics.json)
are published alongside every prediction, mistake and cost calculation.

**Review buys a different error tradeoff.** In the mini UX study it raised
Jev-only feature recall from 67.5% to 84.7%, while lowering accuracy from 91.4%
to 90.2%. More review is not automatically better.
[Review effect](benchmarks/agent/ux-recall/review-effect.json) ·
[Losing tasks and baselines](benchmarks/cascade/gpt-4.1-mini/README.md)

The broader [workflow study](benchmarks/workflows/README.md) includes four UX
labels and issues from five projects. Results vary by task; sorting labels is
not UX synthesis, prioritization or incident diagnosis.

## Full audit trail

- `results.jsonl`: every decision, confidence, probabilities, usage and error.
- `review.jsonl`: complete original records needing review, including provider failures.
- `request.json` and `summary.json`: rubric, routing settings and run totals.

Files live in `DECIDE_ROOT/.decide/<run-id>/`. The default tool response has no
input previews. Oversized items go intact to review; corrupt provider responses
do not cancel the other records. [`decide.py`](decide.py) is the entire server.

Selected content is sent to TypeSafe. Scope your input paths accordingly.
[Limits, timeouts and retry costs](docs/usage.md#settings-and-limits)

## Try your own workload

Label a sample, run the [evaluator](benchmarks/README.md#benchmark-your-own-labeled-data),
and compare errors, recall and complete cost. Share a small, reproducible issue
when a task works well or fails; both belong in the benchmark suite.

[Download v0.1.1](https://github.com/alsoleg89/decide/releases/tag/v0.1.1) ·
[Local verification](docs/release-check.md) · [Development](docs/usage.md#development)

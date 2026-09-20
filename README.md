<div align="center">

# decide

### Your agent reasons. Jev sorts.

Bulk decisions for Claude and Codex. Keep the pile out of your agent’s context.

[Get started](#get-started) · [Workflows & benchmarks](benchmarks/workflows/README.md) · [Tool reference](docs/usage.md) · [All evaluations](benchmarks/README.md)

</div>

---

A backlog of issues. Hundreds of product reviews. A wall of logs.
Your agent needs to decide what matters before it can do useful work.

**Give it a path and a rubric.** `decide` sends each record to
[Jev](https://docs.typesafe.ai/introduction), saves the decisions locally, and
returns a compact summary plus a review queue. Your agent can inspect the
exceptions and use scripts to act on the rest.

```text
You: “Find feature requests in these 500 app reviews.”
                           │
Claude / Codex defines the criteria and passes the file path
                           │
                    decide → Jev
                           │
          ┌────────────────┴────────────────┐
     Accepted decisions              Needs a closer look
     results.jsonl                   review.jsonl
     Process with code               Review with your agent
```

**One MCP tool. One server file. Your rubric, your data.**
Works with UTF-8 files, log lines, JSONL records, or inline items.

## Put it to work

| You are… | Give decide this job | What you get |
| --- | --- | --- |
| **A UX researcher** | Extract reports of product failures from app reviews | Candidate friction points and uncertain cases to inspect before deeper research |
| **A product manager** | Separate feature requests, bugs and general feedback | Signals to feed discovery and the backlog; use separate questions for overlapping labels |
| **A developer** | Sort incoming issues into bugs, features and questions | Structured labels for automation and a queue for ambiguous reports |
| **In support** | Route customer messages into your team's intent taxonomy | A routing file and messages requiring judgment |
| **On call** | Categorize log events and always escalate urgent labels | An investigation queue; group multiline events first |

These are sorting jobs. UX synthesis, prioritization, incident diagnosis and code
changes still need judgment. `decide` produces labels; it never executes them.

## Benchmarks that look like work

**500 app reviews → 403 automatic feature-request decisions, 97 to review, $0.0090 in Jev inference.**
Twelve accepted decisions were wrong (3.0%).

New live benchmarks: **UX / product feedback and developer issue triage**.
2,000 source records, 3,500 decisions, nine tasks. Inputs and thresholds were
[committed before inference](benchmarks/workflows/protocol.json).

| Job | Items | Accepted / needs review | Wrong among accepted | Full-review JSON saved | Jev cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Find bug reports in app reviews | 500 | 399 / 101 | 10 (2.5%) | 73.4% | $0.0092 |
| Find feature requests in app reviews | 500 | 403 / 97 | 12 (3.0%) | 74.2% | $0.0090 |
| Triage issues across five projects | 1,500 | 1006 / 494 | 169 (16.8%) | 60.7% | ≥ $0.0749 |

Fixed threshold: 0.95. JSON savings include reading **every full review input**;
they are not billed agent tokens. Jev cost excludes the orchestrator. Final
reviewer accuracy and total-dollar savings [have not been measured](benchmarks/cascade/README.md).

**Some tasks fail.** The UX usage-experience label had 59.7% errors among accepted
decisions. Asking all four UX questions left 497 of 500 reviews needing at least
one check. Developer triage also retained too many wrong labels for unattended
use. Focused bug and feature extraction performed substantially better, but
feature extraction still wrongly dismissed 11 real requests.

[See every task, mistake rate and baseline →](benchmarks/workflows/README.md)

The earlier [10-task study and frozen-threshold follow-up](benchmarks/multitask/README.md)
cover another 8,340 records. Banking support illustrates the tradeoff: 401 of
770 messages accepted at threshold 0.99, with 14 wrong labels among those 401;
45.5% less full-review JSON. An explicit Apache log-level parser matched Jev
at 100% on 300 records—use the parser when a rule already solves the job.

**Maximize useful savings, not a review percentage.** Choose a threshold on
labeled examples, check it on separate data, and audit accepted decisions.
Higher confidence can still be wrong. There is no universal “only review 5%”
setting. [How we test threshold selection →](benchmarks/multitask/threshold-validation/README.md)

## Get started

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/) and a
[TypeSafe API key](https://console.typesafe.ai).

```sh
git clone https://github.com/alsoleg89/decide.git
cd decide
uv sync --locked
```

Connect it to **[Codex](docs/usage.md#codex)** or
**[Claude Code / Desktop](docs/usage.md#claude-code--claude-desktop)**.
Set `TYPESAFE_API_KEY` in the server environment and `DECIDE_ROOT` to the
folder containing your data.

Then ask your agent:

> Use decide on feedback.jsonl to find feature requests. Pass the file path
> directly without reading the whole file first. Use yes/no criteria, start
> at confidence 0.95, and read the review queue before making recommendations.

Each JSONL row needs an ID and content:

```jsonl
{"id":"review-1","content":"Please let me export my workout history as CSV."}
{"id":"review-2","content":"The app closes every time I open the activity screen."}
```

<details>
<summary><strong>The actual tool call</strong></summary>

```json
{
  "question": "Does this app review request a new or changed capability?",
  "criteria": {
    "yes": "Requests a new or changed function, content, interface, or capability",
    "no": "Does not request a new or changed capability"
  },
  "source": {"kind": "jsonl", "paths": ["feedback.jsonl"]},
  "confidence_threshold": 0.95
}
```

The threshold is an example operating point, not a promised accuracy level.

</details>

## Small context. Full audit trail.

The default response contains counts and file paths, with no input previews.
Every decision, confidence, probability distribution and provider error stays
in `results.jsonl`. Every case needing review keeps its **full original input**
in `review.jsonl`. Both live under `DECIDE_ROOT/.decide/<run-id>/`.

- **Read from disk:** files and globs, individual log lines, or JSONL records.
- **Control escalation:** confidence threshold plus labels that always need review.
- **Keep failures visible:** invalid responses and oversized items enter the review queue.
- **Stay inspectable:** [`decide.py`](decide.py) is the entire production server.

Input content is sent to TypeSafe. Scope source paths accordingly. A confidence
score is not a probability of correctness. [Limits, retries and data handling →](docs/usage.md#settings-and-limits)

## Try your own workload

The best benchmark is the job you want to delegate. Label a sample and run the
[real-data evaluator](benchmarks/README.md#benchmark-your-own-labeled-data),
then compare accepted errors against the bytes and review work saved.

Found a task that works beautifully—or fails badly? Open an issue with the
rubric and a small, shareable example. Both belong in the benchmark suite.

[Setup & reference](docs/usage.md) · [Reproduce the benchmarks](benchmarks/workflows/README.md#sources-and-reproducibility) · [Development](docs/usage.md#development)

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

## Measured against GPT-4.1 mini

**51–77% lower classification cost, with higher accuracy on 1,300 new records.**
The policy was fixed before the runs: let Jev classify, and use mini only for
records Jev cannot process. These samples had no confidence-based review.

| Job | New records | GPT-4.1 mini alone | Jev with error fallback | Cost reduction |
| --- | ---: | --- | --- | ---: |
| Find feature requests in app reviews | 1,000 | 86.4% accuracy · $0.03745 | **90.9% · $0.01817** | **51.5%** |
| Triage OpenCV issues | 300 | 67.0% accuracy · $0.14630 | **75.7% · $0.03351** | **77.1%** |

Macro-F1 also increased on both tasks. The OpenCV price includes a real mini
call for one oversized record; it was kept whole. Every other valid Jev decision
was used directly. Costs include both providers at published rates, not just
JSON-byte estimates.

[Fresh-record protocol, paired mistakes, tokens and results →](benchmarks/cascade/gpt-4.1-mini/followup/README.md)

**A reviewer must earn its cost.** The earlier [nine-task comparison](benchmarks/cascade/gpt-4.1-mini/README.md)
found jobs where Jev helped, jobs where mini alone preserved quality better,
and jobs where adding review made results worse and more expensive. It motivated
this follow-up; it did not justify a universal routing rule.

These are selected tasks from the same public corpora, with exact prior texts
excluded. Results establish an observed cost-quality advantage on these samples,
not a guarantee for your data. Classification prices exclude autonomous-agent
planning, MCP overhead and conversation history. A global minimum cost remains
unproven.

The [workflow study](benchmarks/workflows/README.md) covers 3,500 Jev decisions
on UX feedback and issues from five projects. The [earlier evaluations](benchmarks/multitask/README.md)
cover another 8,340 records across ten tasks. Predictions, failures, baselines
and reproduction instructions are published throughout.

Choose the greatest savings your task's quality allows. Review rate is an
outcome, not a quota: there is no universal “only review 5%” setting.
[Threshold-selection checks →](benchmarks/multitask/threshold-validation/README.md)

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

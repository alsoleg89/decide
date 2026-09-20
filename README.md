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

**Cut the bill while protecting the quality your task needs.**
On 1,000 new UX reviews, the selected policy improved all four frozen quality
metrics and reduced total inference cost by **48.9%**.

| UX feature-request extraction | mini alone | decide + mini |
| --- | ---: | ---: |
| Accuracy | 84.2% | **90.2%** |
| Macro-F1 | 0.7803 | **0.8577** |
| Precision | 58.4% | **72.0%** |
| Recall | 76.8% | **84.7%** |
| Complete tool-loop cost | $0.04993 | **$0.02551** |
| Mini input tokens across all turns | 92,167 | **14,228** |

Jev handled the whole file. Mini checked 123 uncertain negative answers;
valid positive answers stayed with Jev. The cutoff was selected on older data
and committed before these 1,000 exact-disjoint reviews were sent to either model.
Both agents wrote complete output files and verified every input ID.

[New UX records, frozen policy, all mistakes and reproduction →](benchmarks/agent/ux-recall/README.md)

The cost includes reading data, real MCP, retained history, writing results and
the final answer, plus both providers. Both arms discard completed batches.
This is a guided workflow with host-enforced completion, not a native Codex/Claude
session. Results are observed sample comparisons, not a future quality guarantee
or proof of the globally cheapest policy.

**Developer workflow:** on 300 OpenCV issues, an error-only fallback policy cut
tool-loop cost **77.3%** and raised accuracy from **68.0% to 74.7%**, with higher
macro-F1. Feature-label recall fell, so that policy suits a different quality
tradeoff. [Developer results and class metrics →](benchmarks/agent/gpt-4.1-mini/required-completion/README.md)

**Also measured against GPT-5.6 Luna:** on the same 1,000 UX reviews and
300 OpenCV issues, decide reduced complete tool-loop cost **32.8%** and
**70.4%** respectively. UX accuracy rose **87.8% → 90.1%**; developer accuracy
stayed **74.7%**. Both tasks failed the frozen all-metrics quality gate:
UX feature recall fell **87.68% → 87.19%** (one fewer true request), and developer
bug/feature recall also fell. Luna used reasoning `none`; these are reused
records, not a new holdout. [128 actual Luna responses, class metrics and costs →](benchmarks/agent/gpt-5.6-luna/README.md)

**Less review is not the goal.** The earlier UX policy was cheaper but missed more
feature requests. The new policy spends more on review and recovers that recall.
The [nine-task comparison](benchmarks/cascade/gpt-4.1-mini/README.md) also includes
jobs where mini preserves quality better and where review makes results worse.
[An agent stopping before the job was done](benchmarks/agent/gpt-4.1-mini/README.md#first-run-a-real-completion-failure)
remains published too.

The [workflow study](benchmarks/workflows/README.md) covers 3,500 Jev decisions
on UX feedback and issues from five projects. The [earlier evaluations](benchmarks/multitask/README.md)
cover another 8,340 records across ten tasks. Reference labels, predictions,
failures and baselines are published throughout.

Review rate is an outcome, not a quota. Choose the greatest savings your task's
quality allows; there is no universal “only review 5%” setting.

## Get started

You need [uv](https://docs.astral.sh/uv/), Git and a
[TypeSafe API key](https://console.typesafe.ai). **No clone required.**

Connect **[Codex](docs/usage.md#codex)** or
**[Claude Code / Desktop](docs/usage.md#claude-code--claude-desktop)** with this
MCP launch command:

```sh
uvx --python 3.11 --from git+https://github.com/alsoleg89/decide@v0.1.0 decide-mcp
```

Set `TYPESAFE_API_KEY` in the server environment and `DECIDE_ROOT` to the
folder containing your data. The client launches the stdio server; the first
launch installs dependencies, then `uvx` reuses its cache.
[Local checkout and installation check →](docs/usage.md#install)

Then ask your agent:

> Use decide on feedback.jsonl to find feature requests. Pass the file path
> directly without reading the whole file first. Use yes/no criteria with a
> global confidence threshold of 0 and a threshold of 0.9 for no. Read every
> case in the review queue and save one final decision per input ID. Verify
> complete coverage before reporting success.

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
  "confidence_threshold": 0,
  "confidence_thresholds": {"no": 0.9}
}
```

This reproduces the routing from the new UX validation: accept valid positive
answers, review uncertain negatives and errors. Validate it on your own labeled
sample; a confidence cutoff does not guarantee accuracy.

</details>

## Small context. Full audit trail.

The default response contains counts and file paths, with no input previews.
Every decision, confidence, probability distribution and provider error stays
in `results.jsonl`. Every case needing review keeps its **full original input**
in `review.jsonl`. Both live under `DECIDE_ROOT/.decide/<run-id>/`.

- **Read from disk:** files and globs, individual log lines, or JSONL records.
- **Control escalation:** global and per-label confidence cutoffs, plus labels that always need review.
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

[MIT license](LICENSE) · [Download v0.1.0](https://github.com/alsoleg89/decide/releases/tag/v0.1.0) · [Local release checks](docs/release-check.md)

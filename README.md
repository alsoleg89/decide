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

**Pay less to finish the sorting job — including the tool loop.**
We measured reading data, calling real MCP, writing a complete decisions file and
giving the final answer. Both arms discard completed batches from history.

| Job | Records | mini alone: accuracy · total cost | decide + mini: accuracy · total cost | Cost reduction |
| --- | ---: | --- | --- | ---: |
| Find feature requests in app reviews | 1,000 | 84.5% · $0.04808 | **91.0% · $0.01876** | **61.0%** |
| Triage OpenCV issues | 300 | 68.0% · $0.15129 | **74.7% · $0.03429** | **77.3%** |

Macro-F1 also improves on both tasks. Jev handles valid decisions; mini sees only
errors, including one oversized issue kept whole. Prices include both providers.
There is no confidence-based review in this measured policy.

[Full workflow costs, tokens, errors and reproduction →](benchmarks/agent/gpt-4.1-mini/required-completion/README.md)

**Know the tradeoff.** On UX, decide produces fewer false positives, but feature-request
recall falls from 75.1% to 64.8%. Higher accuracy and macro-F1 do not mean every
metric improves. Choose the metric your job actually needs.

This is a guided tool loop with completion enforced by the host, not a native
Codex/Claude session. It reuses the 1,300 records from our
[fresh-record validation](benchmarks/cascade/gpt-4.1-mini/followup/README.md); it is
not another independent quality sample. An earlier agent run stopped too soon:
[that failure remains published](benchmarks/agent/gpt-4.1-mini/README.md#first-run-a-real-completion-failure).

**A reviewer must earn its cost.** The [nine-task comparison](benchmarks/cascade/gpt-4.1-mini/README.md)
includes jobs where Jev helps, jobs where mini preserves quality better, and jobs
where adding review makes the result worse and more expensive. These two successful
workloads are selected public-data tasks, not a universal rule or a global cost minimum.

The [workflow study](benchmarks/workflows/README.md) covers 3,500 Jev decisions
on UX feedback and issues from five projects. The [earlier evaluations](benchmarks/multitask/README.md)
cover another 8,340 records across ten tasks. Predictions, failures and baselines
are published throughout.

Review rate is an outcome, not a quota: there is no universal “only review 5%” setting.
[Choose a policy on your own labeled sample →](benchmarks/multitask/threshold-validation/README.md)

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
> at confidence 0, read every error case in the review queue, and save one final
> decision per input ID. Verify complete coverage before reporting success.

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
  "confidence_threshold": 0
}
```

This reproduces the measured policy: accept every valid answer and review errors.
Evaluate it on your own labeled sample; confidence 0 does not guarantee quality.

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

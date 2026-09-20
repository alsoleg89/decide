# GPT-4.1 mini: the cost of completing the workflow

Original protocol: [`0af79d4`](https://github.com/alsoleg89/decide/commit/0af79d4), frozen before paid calls. Two workflows reuse all 1,000 UX feature-request reviews and 300 OpenCV issues from the [fresh-record study](../../cascade/gpt-4.1-mini/followup/). These are **not another 1,300 independent examples**. The question here is whether savings survive reading, tool schemas, history, disk writes, and a final answer.

Both arms must produce `decisions.jsonl` with exactly one valid label for every input ID, verify coverage, and report label counts. The same GPT-4.1 mini snapshot drives real function calls. The baseline reads batches of 25 and supplies labels; the decide arm calls a live local stdio MCP server, imports accepted decisions programmatically, and reads/classifies only exceptions. Threshold 0 and unchanged rubrics were selected and validated in the previous study. No confidence target.

The host exposes only the next valid operation and binds the MCP arguments to the frozen rubric. This is a **guided tool loop**, not a free-form Codex/Claude session, a tool-discovery test, or evidence that mini independently chooses an optimal policy. A minimal application adapter exposes `decide`, `import_decide`, `read_next`, `write_decisions`, and `finish`; it is benchmark code, not an additional production API.

After a successful write/import, both arms drop processed source text and retain only the last tool call/receipt. No paid compaction model, no quadratic accumulation of old batches. Full token usage on every request includes instructions, current tools, progress, and retained history. Every API request is saved before execution; no automatic OpenAI retries or resume. Jev's built-in retries are charged or flagged as unknown. Cost is list-price inference cost, excluding host CPU, networking, and engineering time.

Order: UX baseline then decide; OpenCV decide then baseline. One run per arm; latency is descriptive, not a repeated timing experiment. Maximum 150 mini calls per arm, 8,192 output tokens per call. Model: `gpt-4.1-mini-2025-04-14`; Jev: `jev-1.13.0`. Both quality measures (accuracy and macro-F1), complete artifact, and lower complete cost must pass. Failures and regressions stay in the results.

To reproduce this original protocol, use commit `0af79d4`. Current `prepare` creates the required-completion protocol instead. Run with the datasets prepared by the linked study, and `OPENAI_API_KEY` / `TYPESAFE_API_KEY` in the environment:

```sh
python benchmark_agent.py prepare --root /tmp/data/ux-feature_request --directory /tmp/agent/ux-feature_request
python benchmark_agent.py run --root /tmp/data/ux-feature_request --directory /tmp/agent/ux-feature_request --arm baseline
python benchmark_agent.py run --root /tmp/data/ux-feature_request --directory /tmp/agent/ux-feature_request --arm decide
python benchmark_agent.py score --directory /tmp/agent/ux-feature_request --arm decide
```

Reference labels are used only by the offline scorer. Published artifacts omit source text, credentials, and full request bodies; request hashes and actual model responses preserve accounting and predictions. The source corpus checksums and reconstruction instructions live in the linked study.

## First run: a real completion failure

UX completed in both arms: baseline 84.5% accuracy / 0.7774 macro-F1 / $0.0504208;
decide 90.9% / 0.8391 / $0.01879681 (62.7% lower total inference cost).

**OpenCV failed to deliver the required output.** After calling MCP, mini returned
“Classification completed and saved” with the 299 accepted-label counts. It
ignored the remaining oversized issue and never called `import_decide` or
`finish`. No `decisions.jsonl` was created. The raw MCP results remain available,
but they are not the requested complete deliverable. Its $0.018650378 cost is
retained; it is **not a successful savings result**. The baseline completed all
300 records at 68.0% accuracy / 0.6718 macro-F1 / $0.1515864.

The failed arm's scorer records zero delivered labels, not zero Jev predictive
accuracy. [Raw final answer](dev-opencv/decide/final.json),
[tool trace](dev-opencv/decide/trace.jsonl), [all four reports](summary.json).
All 114 paid mini responses and 1,299 actual Jev requests remain archived.

The follow-up fixes the application completion contract: while unfinished,
`tool_choice: required`; only after the exact-ID output passes `finish` can the
model give a final answer. This applies equally to both arms. All four arms are
repeated under the changed protocol, not just the failed one. This tests a
host-enforced workflow, not autonomous stopping judgment.

[Required-completion repeat →](required-completion/README.md)

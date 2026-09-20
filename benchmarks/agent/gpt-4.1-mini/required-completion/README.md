# Real MCP, complete files, measured tool-loop cost

Protocol frozen in [`6ed7d5b`](https://github.com/alsoleg89/decide/commit/6ed7d5b) before paid calls. The selected policy accepts valid Jev answers and sends only errors to mini. Same 1,300 records as the [fresh-record study](../../../cascade/gpt-4.1-mini/followup/README.md); this measures workflow overhead, not a new independent quality sample.

Both arms use **GPT-4.1 mini**, write every decision to disk, verify exact ID coverage, and give a final answer. The decide arm invokes the actual stdio MCP server and imports accepted choices without loading their source text into mini. Total cost includes all mini input/output/cache usage, every tool round and final response, plus the live Jev calls.

| Task | Records | mini accuracy / macro-F1 | decide + mini accuracy / macro-F1 | mini total | decide total | Lower cost |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| UX: feature requests | 1,000 | 84.5% / 0.7760 | **91.0% / 0.8405** | $0.04808000 | $0.01876121 | **61.0%** |
| Developer: OpenCV issue triage | 300 | 68.0% / 0.6714 | **74.7% / 0.7453** | $0.15129360 | $0.03429278 | **77.3%** |

All four output artifacts are complete. Accuracy and macro-F1 improve on both tasks, with complete lower cost. This is an observed comparison of these two implementations, not a proof of the global cheapest policy or statistical noninferiority.

## Every model turn counts

| Task / arm | mini calls | mini input tokens | Cached input subset | mini output tokens | Wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| UX: feature requests / baseline | 82 | 90,944 | 4,736 | 8,202 | 122.7 |
| UX: feature requests / decide | 4 | 1,354 | 0 | 34 | 79.4 |
| Developer: OpenCV issue triage / baseline | 26 | 363,394 | 0 | 3,710 | 56.6 |
| Developer: OpenCV issue triage / decide | 6 | 39,937 | 0 | 56 | 30.8 |

Both arms compact completed batches after each successful write/import. Previous source text is removed; only the last call and receipt remain. There is no paid summarizer or quadratic accumulation of old records. Cached tokens receive the discounted rate; reasoning and cache-write tokens were zero. Timing is one sequential run per arm, not a latency distribution.

- **UX: feature requests:** Jev made 1,000 requests, 0 retries; 432,505 input and 31,000 output tokens. 0 record(s) went to mini. Mini input tokens across all turns fell 98.5%.
- **Developer: OpenCV issue triage:** Jev made 299 requests, 0 retries; 434,009 input and 11,362 output tokens. 1 record(s) went to mini. Mini input tokens across all turns fell 89.0%.

The OpenCV exception is the same 140,017-byte issue: skipped locally by Jev and read in full by mini. The classifier failure and fallback remain in the final quality score. Costs use the [mini price snapshot](../../../cascade/gpt-4.1-mini/prices.json) and Jev $0.042/M input tokens. They are list-price estimates, not invoices.

## Which quality improved — and which did not

Overall accuracy and macro-F1 do not mean every class metric improves. For UX feature extraction, decide makes far fewer false positive suggestions but misses more genuine requests. If finding every feature request is your priority, its lower recall is a regression despite the aggregate win.

| Task / label | mini precision | decide precision | mini recall | decide recall |
| --- | ---: | ---: | ---: | ---: |
| UX: feature requests / yes | 57.5% | 85.0% | 75.1% | 64.8% |
| UX: feature requests / no | 93.6% | 92.0% | 86.7% | 97.3% |
| Developer: OpenCV issue triage / bug | 56.0% | 60.4% | 75.0% | 90.0% |
| Developer: OpenCV issue triage / feature | 75.9% | 88.9% | 85.0% | 80.0% |
| Developer: OpenCV issue triage / question | 81.5% | 88.5% | 44.0% | 54.0% |

| Task | Both correct | Only mini correct | Only decide correct | Both wrong |
| --- | ---: | ---: | ---: | ---: |
| UX: feature requests | 813 | 32 | 97 | 58 |
| Developer: OpenCV issue triage | 192 | 12 | 32 | 64 |

Every disputed ID and both decisions are retained in [UX paired errors](ux-feature_request/paired-errors.jsonl) and [OpenCV paired errors](dev-opencv/paired-errors.jsonl). Full per-class confusion matrices are in the reports.

## Completion is an application contract

The [first experiment](../README.md#first-run-a-real-completion-failure) failed on the OpenCV decide arm: mini said it was done immediately after MCP, leaving one issue unresolved and no final decisions file. That failed run and its costs remain published.

The one protocol change here is `tool_choice: required` on unfinished steps; a final answer is allowed only after `finish` verifies complete output. All four arms were repeated under that rule. The host exposes the next legal operation and binds the decide arguments to the frozen rubric. This is a **guided, host-enforced tool loop**, not a test of autonomous policy selection or stopping judgment. It includes the adapter tool schemas, not the full tool catalog and UI overhead of a native Codex/Claude session. Host CPU, network charges and engineering time are excluded.

## Reproduce and audit

Use the unchanged source reconstruction instructions from the [fresh-record study](../../../cascade/gpt-4.1-mini/followup/README.md). Original inputs stay local; reference labels are never sent to either model. The protocols pin input/label/code hashes. Fresh paid runs require environment keys, and each output directory must be new. No automatic OpenAI retry or resume.

```sh
python benchmark_agent.py prepare --root /tmp/data/ux-feature_request --directory /tmp/agent/ux-feature_request
python benchmark_agent.py run --root /tmp/data/ux-feature_request --directory /tmp/agent/ux-feature_request --arm baseline
python benchmark_agent.py run --root /tmp/data/ux-feature_request --directory /tmp/agent/ux-feature_request --arm decide

# Free: recompute published results from saved usage and final labels
python benchmark_agent.py score --directory benchmarks/agent/gpt-4.1-mini/required-completion/ux-feature_request --arm decide
```

For OpenCV the paid order was decide then baseline; UX used baseline then decide. Each task directory contains its protocol, reference labels, paired errors and two arm directories. Each arm retains `decisions.jsonl`, `report.json`, `state.json`, `final.json`, the tool trace, and every actual response under `turns/`. Raw source-bearing tool outputs are replaced by IDs, hashes and byte counts; full request bodies and secrets are omitted. The decide arm also retains its fresh Jev predictions and summary.

[All machine-readable results](summary.json) · [Original failed run](../summary.json)

This repeat used 118 paid mini responses and cost $0.25242759 across both arms and both providers. Including the original experiment ($0.23945439), the two tool-loop experiments cost $0.49188198. These are experiment totals; per-deployment costs are the separate arm columns above.

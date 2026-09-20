# Luna: the same job, with and without decide

Measured on 2026-09-20 using `gpt-5.6-luna`, reasoning `none`. Each task has a
full-Luna baseline and a fresh Jev + Luna tool loop. These are **1,300 reused
records**, not new holdouts: 1,000 French app reviews and 300 OpenCV issues.
The [protocol commit](https://github.com/alsoleg89/decide/commit/7932ebfdafc901b8b9e328f47f3e309dbc19b4d0)
preceded every paid call. Policies were copied unchanged from the mini studies.

## Results

| Task / metric | Luna alone | decide + Luna |
| --- | ---: | ---: |
| **UX: feature requests** | | |
| Accuracy | 87.8% | 90.1% |
| Macro-F1 | 0.8323 | 0.8587 |
| Total inference cost | $0.03433380 | $0.02306605 |
| Model input tokens, all turns | 98,967 | 15,087 |
| Model output tokens, all turns | 9,184 | 1,144 |
| Model calls | 82 | 14 |
| Wall time, one run | 172.1s | 103.0s |
| **Developer: OpenCV issues** | | |
| Accuracy | 74.7% | 74.7% |
| Macro-F1 | 0.7383 | 0.7450 |
| Total inference cost | $0.09570035 | $0.02836203 |
| Model input tokens, all turns | 365,490 | 40,373 |
| Model output tokens, all turns | 4,032 | 121 |
| Model calls | 26 | 6 |
| Wall time, one run | 61.9s | 38.0s |

## Did the frozen quality-and-cost gate pass?

Success requires complete exact-ID files and complete lower inference cost, plus
accuracy, macro-F1 and precision/recall for every frozen quality label at least
as high as Luna alone. UX protects `yes`; developer triage protects all classes.

- **ux-feature_request: FAIL.** Cost reduction: 32.8%. Quality regressions: yes_recall. Reviewed 118/1000 records.
- **dev-opencv: FAIL.** Cost reduction: 70.4%. Quality regressions: bug_precision, bug_recall, feature_recall, question_precision. Reviewed 1/300 records.

| Task / label | Luna precision | decide precision | Luna recall | decide recall |
| --- | ---: | ---: | ---: | ---: |
| ux-feature_request / yes | 64.7% | 70.8% | 87.7% | 87.2% |
| ux-feature_request / no | 96.6% | 96.5% | 87.8% | 90.8% |
| dev-opencv / bug | 60.9% | 60.0% | 92.0% | 90.0% |
| dev-opencv / feature | 88.5% | 90.0% | 85.0% | 81.0% |
| dev-opencv / question | 88.7% | 88.3% | 47.0% | 53.0% |

The UX recall difference is **177 versus 178** correctly found feature requests
out of 203. This small observed regression fails the exact frozen gate; it is
not evidence of a statistically established population-level difference.

Review rate is measured, never a fixed 5% quota. The threshold was not retuned
after seeing Luna results. One run per arm does not establish future quality,
a latency distribution or the globally cheapest configuration. Reasoning `none`
is the tested configuration, not Luna’s default `medium`. Jev was rerun live:
its UX queue contained 118 records here versus 123 in the older mini study, so
cross-study differences cannot all be attributed to the reviewer model.

## Where the money went

| Task / component | Luna alone | decide + Luna |
| --- | ---: | ---: |
| ux-feature_request / Model USD | $0.03433380 | $0.00488060 |
| ux-feature_request / Jev USD | $0.00000000 | $0.01818545 |
| ux-feature_request / Cached input tokens | 0 | 0 |
| ux-feature_request / Cache-write tokens | 70,392 | 9,808 |
| ux-feature_request / Reasoning tokens | 0 | 0 |
| dev-opencv / Model USD | $0.09570035 | $0.01013365 |
| dev-opencv / Jev USD | $0.00000000 | $0.01822838 |
| dev-opencv / Cached input tokens | 0 | 0 |
| dev-opencv / Cache-write tokens | 355,279 | 38,277 |
| dev-opencv / Reasoning tokens | 0 | 0 |

Luna reports cache writes separately. They are charged at $0.25/M, cached reads
at $0.02/M, ordinary input at $0.20/M and output at $1.20/M. All requests stayed
below the long-context boundary. Jev input costs $0.042/M. The [price snapshot](prices.json)
comes from [official API pricing](https://developers.openai.com/api/docs/pricing).
Costs are list-price estimates from actual usage, not verified invoices.
Reading, tools, retained history, writing and the final answer are all counted.
Host CPU, engineering time and native Codex/Claude UI overhead are excluded.
Both arms use identical compaction; no paid summarizer.

## What review changed

**ux-feature_request:** 1000 Jev requests; 118 records reviewed. Review changed 92 labels, corrected 40 Jev errors and introduced 52 errors. It left 56 errors in reviewed records and 43 errors among accepted records. Local skips count as missing Jev decisions in this diagnostic.

Both arms correct: 857; only Luna correct: 21; only decide correct: 44; both wrong: 78. [Paired errors](ux-feature_request/paired-errors.jsonl) · [Review effect](ux-feature_request/review-effect.json)

**dev-opencv:** 299 Jev requests. The one reviewed record was a 140,017-byte issue, skipped locally because it exceeds the Jev content limit. Luna read it in full and classified it incorrectly; another 75 errors remained among accepted records. The skipped decision counts as missing in the Jev-before-review diagnostic.

Both arms correct: 210; only Luna correct: 14; only decide correct: 14; both wrong: 62. [Paired errors](dev-opencv/paired-errors.jsonl) · [Review effect](dev-opencv/review-effect.json)

## Audit and reproduction

All four artifacts contain exactly the reference IDs. Every model response,
final answer, tool trace, prediction and reported token count is archived.
An independent calculation reconstructed outputs from tool calls and verified
accuracy, per-class precision/recall, macro-F1 and the separate cache charges.
Source-bearing reads are replaced by IDs, hashes and byte counts; full request
bodies and credentials are not published. Labels are used only by the scorer.

[All results](summary.json) · [UX protocol](ux-feature_request/protocol.json) · [Developer protocol](dev-opencv/protocol.json)

Recompute reports without paid calls:

```sh
python benchmark_agent.py score --directory benchmarks/agent/gpt-5.6-luna/ux-feature_request --arm baseline
python benchmark_agent.py score --directory benchmarks/agent/gpt-5.6-luna/ux-feature_request --arm decide
python benchmark_agent.py score --directory benchmarks/agent/gpt-5.6-luna/dev-opencv --arm baseline
python benchmark_agent.py score --directory benchmarks/agent/gpt-5.6-luna/dev-opencv --arm decide
```

For a fresh paid run, use the protocol commit and reconstruct inputs via the
[UX study](../ux-recall/README.md) and [OpenCV follow-up](../../cascade/gpt-4.1-mini/followup/README.md). Then:

```sh
python benchmarks/agent/gpt-5.6-luna/prepare.py --destination /tmp/luna \
  --ux-source /tmp/ux-recall/inputs --dev-source /tmp/decide-mini-followup/dev-opencv
# Set OPENAI_API_KEY and TYPESAFE_API_KEY in the environment.
python benchmark_agent.py run --root /tmp/luna/ux-feature_request/inputs --directory /tmp/luna/ux-feature_request/run --arm baseline
python benchmark_agent.py run --root /tmp/luna/ux-feature_request/inputs --directory /tmp/luna/ux-feature_request/run --arm decide
python benchmark_agent.py run --root /tmp/luna/dev-opencv/inputs --directory /tmp/luna/dev-opencv/run --arm decide
python benchmark_agent.py run --root /tmp/luna/dev-opencv/inputs --directory /tmp/luna/dev-opencv/run --arm baseline
```

Preparation was independently reproduced byte for byte. Existing arm folders
are never resumed or overwritten. UX order: baseline then decide. Developer
order: decide then baseline. No GitHub Actions was used.

Experiment total: **128 Luna calls**, **$0.18146223** for all four arms combined.

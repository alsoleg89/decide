# UX: preserve recall while reducing cost

Protocol frozen before new paid calls. Previous tool-loop results reduced cost
and improved accuracy/F1 but lost feature-request recall. This experiment makes
the quality gate stricter: **accuracy, macro-F1, feature precision AND feature
recall must all be at least GPT-4.1 mini, with complete lower total inference
cost and complete output files.** A gain on averages cannot conceal lower recall.

## Frozen policy

Accept valid Jev `yes` decisions. Send Jev `no` decisions with confidence below
**0.9** to mini, along with all provider/local errors. This uses the real tool's
new optional `confidence_thresholds` override:

```json
{"confidence_threshold": 0, "confidence_thresholds": {"no": 0.9}}
```

Other settings match the previous guided loop: mini snapshot
`gpt-4.1-mini-2025-04-14`, Jev `jev-1.13.0`, 25-record batches, exact-ID writes,
compaction after writes/imports, host-enforced completion. Baseline then decide;
one run each. No confidence or cost tuning after these new results.

## Selection and independent records

[The protocol](protocol.json) contains all candidate results on the earlier
500 and 1,000 UX reviews. The smallest cutoff in `[0, .8, .9, .95, .99, 1]` that
passed all four metrics on both old cohorts was 0.9. These nested review sets
minimize review count within this grid; they do not prove a global cost minimum.
The retrospective calculation substitutes existing mini baseline answers for
review. Only the new live loop measures actual review decisions and their cost.

The new sample contains **1,000 uniformly sampled reviews**, seed 20260925, from
3,708 remaining unique reviews in the same public French fitness-app corpus.
It has zero exact ID/text overlap with either earlier inference cohort. Same
unchanged question/criteria; reference labels are never sent to either model.
This is not a distribution-shift or pretraining-contamination-free evaluation.

Reconstruct the earlier input datasets via the [previous study](../../cascade/gpt-4.1-mini/followup/README.md), then:

```sh
python benchmarks/agent/ux-recall/prepare.py \
  --root /tmp/ux-recall --ux-source /path/to/APIA2022-French-user-reviews-classification-dataset \
  --previous /tmp/decide-workflows --followup /tmp/decide-mini-followup
python benchmark_agent.py run --root /tmp/ux-recall/inputs --directory /tmp/ux-recall/run --arm baseline
python benchmark_agent.py run --root /tmp/ux-recall/inputs --directory /tmp/ux-recall/run --arm decide
```

Fresh runs require `OPENAI_API_KEY` and `TYPESAFE_API_KEY`. Existing output folders
are never resumed or overwritten. Results, failures and all billable responses
will be retained regardless of whether the stronger gate passes.

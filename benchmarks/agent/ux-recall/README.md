# UX: preserve recall while reducing cost

Protocol frozen before new paid calls. Previous tool-loop results reduced cost
and improved accuracy/F1 but lost feature-request recall. This experiment makes
the quality gate stricter: **accuracy, macro-F1, feature precision AND feature
recall must all be at least GPT-4.1 mini, with complete lower total inference
cost and complete output files.** A gain on averages cannot conceal lower recall.

## Measured result

**Stronger gate: PASS.** Both files contain exactly 1,000 decisions. This verdict includes actual mini review answers, not the retrospective substitutions used for selection.

| Metric | GPT-4.1 mini alone | decide + mini |
| --- | ---: | ---: |
| Accuracy | 84.2% | 90.2% |
| Macro-F1 | 0.7803 | 0.8577 |
| Feature-request precision | 58.4% | 72.0% |
| Feature-request recall | 76.8% | 84.7% |
| Total inference cost | $0.04992760 | $0.02551185 |
| Mini input tokens, all turns | 92,167 | 14,228 |
| Mini output tokens, all turns | 8,163 | 1,022 |
| Mini API calls | 82 | 14 |
| Wall time, one run | 133.4s | 98.0s |

Cost fell **48.9%**; mini input tokens fell **84.6%**. Jev sent 123/1000 records to mini (12.3%); this fraction was an outcome, not a target. Jev made 1000 requests and 0 retries; its cost was $0.01818545. Mini orchestration/review cost $0.00732640. Both arms have complete cost accounting.

The quality gate is the frozen four-metric comparison, not a universal quality claim. One new sample and one run per arm do not prove future noninferiority or the global cheapest policy. This is a guided, host-enforced workflow with a small adapter tool catalog; native Codex/Claude UI, tool-discovery overhead, host CPU and engineering time are excluded. All model calls and provider usage are included.

### What changed in the mistakes

- `yes` (support 203): precision 58.4% → 72.0%; recall 76.8% → 84.7%.
- `no` (support 797): precision 93.6% → 95.9%; recall 86.1% → 91.6%.

Both correct: 818; only mini correct: 24; only decide correct: 84; both wrong: 74. [Every disputed ID](paired-errors.jsonl) includes both decisions and the reference label. Per-class confusion matrices, including all misses and false alarms, remain in each report.

### Why this combination helped

On these same records, Jev before review was more conservative: 87.3% feature
precision but 67.5% recall, versus mini's 58.4% precision and 76.8% recall.
Review changed 82 negative decisions to positive: **35 recovered real requests
and 47 introduced false positives**. It left 15 reviewed requests missed; another
16 misses were already accepted by Jev and never reached mini.

Consequently, review lowered Jev-only accuracy from 91.4% to 90.2%, while raising
recall from 67.5% to 84.7% and macro-F1 from 0.8543 to 0.8577. It earned its extra
cost against the frozen recall requirement, not by improving every Jev-only
metric. The combined result still beats the full-mini baseline on all four
required metrics. This [post-hoc review-effect diagnostic](review-effect.json)
uses the actual stored outputs; it is not another paid arm or independent sample,
and assigns no hypothetical agent cost to a no-review run.

### Audit and reproduction

The protocol was committed in [`67ef0c3`](https://github.com/alsoleg89/decide/commit/67ef0c3) before paid calls. The preparation script independently reconstructed byte-identical inputs, labels, rubric and protocol. A separate calculation verified the real tool traces, exact-ID artifact, label-specific routing, classification scores and every paid response.

[Baseline output](baseline/decisions.jsonl) · [decide output](decide/decisions.jsonl) · [Baseline report](baseline/report.json) · [decide report](decide/report.json) · [Comparison JSON](summary.json)

Both arm folders include `trace.jsonl`, `final.json`, `state.json` and actual API responses under `turns/`. The decide folder also includes fresh Jev predictions and its summary. Source-bearing read outputs are replaced by IDs, hashes and byte counts; no source text, full request bodies or credentials are published. Reference labels are used only for scoring.

The scorer verifies the numbered response count against run state and checks the
saved final answer. Missing responses invalidate complete cost accounting;
missing or inconsistent completion evidence prevents a complete-artifact verdict.

Recompute the public reports without API calls:

```sh
python benchmark_agent.py score --directory benchmarks/agent/ux-recall --arm baseline
python benchmark_agent.py score --directory benchmarks/agent/ux-recall --arm decide
```

The whole experiment used 96 mini responses and 1000 Jev requests. Combined cost of both arms: $0.07543945, estimated from provider-reported tokens and the pinned price snapshot.

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
are retained regardless of whether the stronger gate passes.

## Price provenance and statistical uncertainty

The [dated Jev price snapshot](../../jev-prices.json) confirms $0.042/M input
and free output from TypeSafe's public documentation. It was added after these
runs to document their existing assumption; historical protocols and costs
remain unchanged. New agent protocols embed the snapshot before inference.

Both arms used **25-record batches**. Larger standalone-model batches were not
benchmarked, so the cost comparison is against this fixed harness, not an
optimized lower bound. Review can raise recall while lowering accuracy versus
Jev alone; the published review-effect diagnostics separate those effects.

The [post-hoc paired analysis](statistics.json), using 10,000 record-bootstrap
samples, estimates an accuracy gain of 6.0 percentage points (95% percentile
interval: **+4.0 to +8.0 points**). Exact two-sided McNemar on 24 baseline-only
and 84 cascade-only correct records gives **p = 5.49e-9**. This tests accuracy,
not all four quality metrics jointly. Intervals for macro-F1 and per-class
precision/recall are in the same file.

These are exploratory, unadjusted intervals conditional on the saved runs and
reference labels. They exclude model-run variation and distribution shift.
An interval spanning zero does not prove equivalence or noninferiority. Frozen
point-estimate gates stay unchanged. Reproduce with
`python benchmarks/paired_statistics.py PATH_TO_TASK_DIRECTORY`.
The [calculator](../../paired_statistics.py) uses paired resampling and an exact
binomial McNemar test; [method reference](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html).

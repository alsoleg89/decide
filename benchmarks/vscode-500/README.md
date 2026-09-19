# Real-data evaluation: the five-percent review target is not established

Live run on 2026-09-19 through the current `decide` stdio server and Jev 1.13.0,
using one predefined [rubric](rubric.json). All 500 requests succeeded without
retries in 39.525 seconds.

Successful responses reported 483,376 input tokens and 19,000 output tokens.
At the [published Jev 1.13 price](https://docs.typesafe.ai/models) of $0.042 per
million input tokens, with free output tokens, estimated inference cost is
**$0.020302**. This excludes orchestrator processing and review, and is not an invoice.

| Confidence threshold | Accepted | Needs review | Disagreements among accepted | Accepted error rate |
| --- | ---: | ---: | ---: | ---: |
| 0.5 | 410 | 90 (18.0%) | 95 | 23.2% |
| 0.8 | 296 | 204 (40.8%) | 46 | 15.5% |
| 0.9 | 258 | 242 (48.4%) | 32 | 12.4% |
| 0.95 | 216 | 284 (56.8%) | 24 | 11.1% |
| 0.99 | 145 | 355 (71.0%) | 12 | 8.3% |
| 1.0 | 91 | 409 (81.8%) | 4 | 4.4% |

High confidence does not remove all wrong decisions. On this sample, even
reviewing 81.8% leaves four disagreements among the remaining 91 items.
Low total cost and safe 95% automation remain unverified.

## Recompute and enforce your own limits

The evaluator is offline. It checks errors among **accepted** records rather than
counting routing correctness or using overall accuracy as a substitute.

```sh
uv run --locked python evaluate.py \
  --labels benchmarks/vscode-500/labels.jsonl \
  --results benchmarks/vscode-500/predictions.jsonl \
  --threshold 0.8 \
  --max-review-fraction 0.05 \
  --max-accepted-error-rate 0.05
```

This command deliberately exits **1**, because these illustrative limits are
not met. Choose your own acceptable error rate; it is not inferred from a model's
confidence. With neither limit specified, `limits_met` is `null`. Empty or mismatched
ID sets and duplicate IDs are rejected; a zero-coverage subset reports no error
rate rather than a fabricated perfect score. Failed provider requests always
remain in review, and explicit `review_label` routing is preserved during sweeps.

The [report](report.json) contains the full threshold sweep and disagreeing IDs.
[Predictions](predictions.jsonl) retain IDs, confidence, probabilities and usage;
[labels](labels.jsonl) are the reference dispositions. Issue IDs can be inspected
at `https://github.com/microsoft/vscode/issues/<id>`.

## Dataset limitations

The source is a pre-existing local snapshot of 500 public, closed VS Code issues
created in 2024, balanced as 167 bug, 167 feature and 166 question. The exact source
snapshot hash is in the report. Reference labels were excluded from model inputs.
Only title and body were sent; reference dispositions may rely on maintainer
context absent from that text. These are measured disagreements with repository
labels, not adjudicated findings about each issue.

The snapshot was evaluated before in a separate benchmark. This is an exploratory
reuse, **not a fresh held-out test**, and the sweep must not be used to claim
out-of-sample calibration. Raw issue bodies are not republished here. Stored
predictions make the evaluation reproducible; reproducing inference exactly also
requires the original input snapshot. No separate analysis of the orchestrator's
review quality was performed.

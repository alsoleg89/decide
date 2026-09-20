# Benchmarks for the work you actually do

Two workflows, nine classification tasks, **2,000 source records / 3,500 decisions**.
Live calls use Jev 1.13.0 through the real MCP stdio server.
The [protocol](protocol.json) was [committed before inference](https://github.com/alsoleg89/decide/commit/3cbdacc).

| Role | Job | Data | Decisions |
| --- | --- | --- | ---: |
| UX / product | Extract bug reports, feature requests, concrete usage experiences and general evaluations from app feedback | 500 original French reviews, sampled from three apps | 2,000: four binary questions per review |
| Developer | Sort an issue backlog into bug, feature and question | Full NLBSE'24 test split: React, TensorFlow, VS Code, Bitcoin, OpenCV | 1,500 |

The UX source has **multiple labels per review**. We preserve them with four
independent yes/no calls; forcing a single label would change the research task.
The review text is sent unchanged in French. Star scores and reference labels
are excluded. This evaluates feedback sorting, not visual design or usability
testing. The developer task evaluates backlog triage, not code correctness or
the quality of a proposed fix. Original issue templates and title prefixes are
retained because those are available during real triage.

All nine tasks use **threshold 0.95**, fixed before any result is observed.
This is an operating point, not a calibrated error guarantee. We report accepted
errors, review volume, accuracy, macro-F1, per-class confusion, descriptive 95%
Wilson intervals, full-review JSON bytes, latency, failed calls and known Jev
cost. A local Naive Bayes baseline uses disjoint labeled training texts; Jev
receives no training examples. The unequal training regimes are explicit.

For UX, we additionally measure missed signals (accepted false negatives),
false alarms, per-app results and exact agreement on all four labels together.
Four independent requests cost more than one; per-axis context savings cannot
be advertised as savings for the entire four-pass workflow.

## Live results

**3,500 decisions completed. Known Jev cost: at least $0.111413.** One rejected
VS Code response has incomplete usage accounting; all nine runs had zero retries.
Costs below cover Jev classification only, using reported input tokens at
[$0.042 per million](https://docs.typesafe.ai/models). They exclude agent review.

| Job | Items | Automatically accepted | Wrong among accepted | Needs review | Full-review JSON saved | Jev USD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [UX: bug reports](results/ux-bug_report/report.json) | 500 | 399 | 10 (2.5%) | 101 (20.2%) | 73.4% | $0.00918 |
| [UX: feature requests](results/ux-feature_request/report.json) | 500 | 403 | 12 (3.0%) | 97 (19.4%) | 74.2% | $0.00905 |
| [UX: usage experiences](results/ux-user_experience/report.json) | 500 | 181 | 108 (59.7%) | 319 (63.8%) | 47.7% | $0.00909 |
| [UX: general evaluations](results/ux-rating/report.json) | 500 | 27 | 2 (7.4%) | 473 (94.6%) | 5.9% | $0.00918 |
| [Developer: Bitcoin](results/dev-bitcoin/report.json) | 300 | 205 | 36 (17.6%) | 95 (31.7%) | 61.5% | $0.01570 |
| [Developer: React](results/dev-react/report.json) | 300 | 231 | 35 (15.2%) | 69 (23.0%) | 78.6% | $0.01070 |
| [Developer: VS Code](results/dev-vscode/report.json) | 300 | 209 | 50 (23.9%) | 91 (30.3%) | 61.3% | ≥ $0.01287 |
| [Developer: OpenCV](results/dev-opencv/report.json) | 300 | 181 | 26 (14.4%) | 119 (39.7%) | 69.0% | $0.01536 |
| [Developer: TensorFlow](results/dev-tensorflow/report.json) | 300 | 180 | 22 (12.2%) | 120 (40.0%) | 46.9% | $0.02029 |

The JSON measure includes the source call, actual compact response and **all full
review inputs**. It excludes MCP framing, host history and agent reasoning.
It is not billed tokens or total-dollar savings. The threshold sweep in each
report is exploratory; the table above retains the precommitted 0.95 threshold.

### What a UX researcher can actually delegate

- **Bug extraction:** 399 of 500 decisions accepted, with 10 false alarms and no accepted false negatives. This is promising for an initial bug-signal pass; zero observed misses does not guarantee zero future misses.
- **Feature extraction:** 403 accepted, but 11 actual requests were dismissed and one non-request was flagged. Small overall error can still hide meaningful missed signals.
- **Usage-experience extraction failed:** 108 of 181 accepted decisions disagreed with the annotations. Of these, 107 were false positives. A high confidence threshold did not make this rubric reliable.
- **General evaluation extraction saved little work:** 473 of 500 decisions still needed review.

**The complete four-label UX workflow did not deliver useful automation in this run.**
All four predictions matched for only 29.2% of reviews. Only three reviews had all four decisions accepted;
two of those three contained an error. **497 / 500 reviews still needed at least
one check.** The four passes cost $0.036491. Per-axis savings of 73–74% must not
be presented as savings for that combined workflow.

A small inspection of accepted mistakes suggests that task definitions and
annotation boundaries deserve attention: `Samsung Health:1087` is a privacy
complaint labeled as a feature request but predicted as no; `Garmin Connect:1122`
asks to restore a removed function, labeled as no but predicted as yes.
`Samsung Health:1697` describes a step-counting failure, labeled as not a usage
experience but predicted as one. These are illustrative disagreements, not
an adjudication or a proven explanation for every error. Inputs, labels and
rubrics were not rewritten after this inspection.

### What a developer can actually delegate

Across five projects, 1006 / 1,500 issues were accepted, with 169 wrong labels
(16.8%). 494 issues needed review. The pooled full-review JSON reduction
was 60.7%. This is measurable context reduction with **too many label
disagreements to call it reliable unattended triage**.

Even at confidence exactly 1.0, React retained 21 disagreements among 174
accepted issues; VS Code retained 24 among 140. Raising the threshold alone
did not solve the problem. Keep proposals reviewable, evaluate your own
taxonomy, and do not automatically close issues based on these labels.

### Quality, uncertainty and the cheap local baseline

| Job | All-item accuracy | Macro-F1 | Trained NB accuracy | Accepted-error 95% interval | Live seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| UX: bug reports | 92.0% | 0.917 | 88.6% | 1.4%–4.6% | 39.8 |
| UX: feature requests | 90.6% | 0.840 | 89.6% | 1.7%–5.1% | 43.4 |
| UX: usage experiences | 40.6% | 0.404 | 82.8% | 52.4%–66.5% | 38.9 |
| UX: general evaluations | 79.4% | 0.789 | 80.2% | 2.1%–23.4% | 40.9 |
| Developer: Bitcoin | 78.3% | 0.775 | 62.7% | 13.0%–23.4% | 23.8 |
| Developer: React | 78.0% | 0.775 | 76.3% | 11.1%–20.3% | 24.6 |
| Developer: VS Code | 67.0% | 0.627 | 64.0% | 18.6%–30.1% | 25.2 |
| Developer: OpenCV | 78.7% | 0.789 | 56.7% | 10.0%–20.2% | 25.0 |
| Developer: TensorFlow | 80.3% | 0.803 | 60.7% | 8.2%–17.8% | 27.5 |

All-item accuracy and F1 count failed responses as incorrect. Intervals are
descriptive Wilson intervals, not simultaneous bounds or calibrated future
guarantees. The Naive Bayes baseline has labeled training data; Jev is zero-shot.
NB outperformed Jev on usage experiences and general evaluations. We do not
claim superiority over trained classifiers or the published competition systems.

[Machine-readable summary](summary.json) includes per-app routing, accepted
confusion matrices, missed UX signals, combined four-label checks and pooled
developer results. Per-task reports include full class precision/recall/F1,
confusion matrices and threshold sweeps. Labels and every prediction, including
the failed response, are archived beside those reports.

## Sources and reproducibility

- [Wei et al., APIA 2022](https://github.com/Jl-wei/APIA2022-French-user-reviews-classification-dataset): 6,000 manually annotated French app reviews. Pinned commit `c8fd015f526d9c93d4726122ae845296d46fb5a8`.
- [Kallis et al., NLBSE 2024](https://github.com/nlbse2024/issue-report-classification): official train/test split of issue reports from five projects. Pinned commit `2927bc67eb42db8affd16eaf3e5a6d74f3063961`.

The [protocol](protocol.json) records source and input hashes, IDs, groups,
sampling seed, model and server hash. UX samples are uniform after removing
empty/duplicate texts across apps. Each UX training set uses the remaining
reviews. Developer evaluation retains the entire official test split; any exact
test-text duplicates in training are removed. Public data may have appeared in
model training. Repository labels and research annotations are references, not
infallible ground truth; there is no separate human adjudication in this run.

Clone the two source repositories, check out the pinned commits, then:

```sh
uv run --locked python benchmarks/workflows/workflows.py prepare \
  --ux-source /path/to/APIA2022-French-user-reviews-classification-dataset \
  --dev-source /path/to/issue-report-classification \
  --root /tmp/decide-workflows \
  --protocol /tmp/workflow-protocol.json

# Paid: requests the TypeSafe key through a hidden prompt if absent from the environment.
uv run --locked python benchmarks/workflows/workflows.py run \
  --root /tmp/decide-workflows --protocol /tmp/workflow-protocol.json \
  --output /tmp/workflow-results/results

# Free: recompute from archived predictions; no model calls.
uv run --locked python benchmarks/workflows/workflows.py report

# Free: after regenerating the pinned inputs, also recompute full byte accounting.
uv run --locked python benchmarks/workflows/workflows.py report \
  --verify-inputs --root /tmp/decide-workflows
```

The live path uses the existing real MCP stdio runner. Completed runs are reused;
unfinished runs require inspection, and failed decisions remain in the results.
Raw source texts and credentials are kept outside Git. Archived labels,
predictions and rubrics permit offline quality verification. Full byte
reproduction additionally requires the original inputs and saved live response.
JSON bytes are not billed agent tokens. The subsequent
[GPT-4.1 mini study](../cascade/gpt-4.1-mini/README.md) measures actual reviewer
accuracy and classification costs; full autonomous-agent costs remain unmeasured.

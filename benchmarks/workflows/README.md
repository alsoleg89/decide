# Benchmarks for the work you actually do

Two workflows, nine classification tasks, **2,000 source records / 3,500 decisions**.
This protocol is frozen before inference. Results will be added after the live runs.

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
```

The live path uses the existing real MCP stdio runner. Completed runs are reused;
unfinished runs require inspection, and failed decisions remain in the results.
Raw source texts and credentials are kept outside Git. Archived labels,
predictions and rubrics permit offline quality verification. Full byte
reproduction additionally requires the original inputs and saved live response.
JSON bytes are not billed agent tokens; total orchestrator dollars and final
reviewer accuracy remain unmeasured.

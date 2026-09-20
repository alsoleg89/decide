# Does decide beat GPT-4.1 mini on cost without losing quality?

**Measured with `gpt-4.1-mini-2025-04-14`, not Astra.** Nine work tasks: four UX/product
questions on 500 French app reviews, and triage of 1,500 issues from five projects.

**The answer depends on the task.** The frozen Jev → mini cascade passed the
observed accuracy, macro-F1 and cost checks on feature extraction and OpenCV.
A retrospective no-review comparison found that **Jev alone was cheaper and
better than that cascade on both tasks**. A reviewer is a cost that must earn its place.

## Frozen routing: Jev plus actual mini review

Threshold 0.95, chosen before these GPT comparisons. Same rubric, model and batch
size (25) in both arms. The reviewer receives original inputs without Jev guesses
or reference labels. All final errors and reported tokens are counted.

| Task | Mini accuracy | Jev + mini accuracy | Mini macro-F1 | Jev + mini macro-F1 | Mini USD | Jev + mini USD | Sample gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| [UX: bug reports](results/ux-bug_report/report.json) | 93.0% | 92.8% | 0.9256 | 0.9247 | $0.01851 | $0.01337 | Fail |
| [UX: feature requests](results/ux-feature_request/report.json) | 87.4% | 90.4% | 0.8039 | 0.8543 | $0.01846 | $0.01302 | Pass |
| [UX: general evaluations](results/ux-rating/report.json) | 66.2% | 62.4% | 0.6218 | 0.5636 | $0.01850 | $0.02659 | Fail |
| [UX: usage experiences](results/ux-user_experience/report.json) | 44.6% | 43.4% | 0.4376 | 0.4280 | $0.01847 | $0.02001 | Fail |
| [Developer: Bitcoin](required-id-map/results/dev-bitcoin/report.json) | 73.3% | 72.7% | 0.7181 | 0.7142 | $0.09780 | $0.05424 | Fail |
| [Developer: OpenCV](required-id-map/results/dev-opencv/report.json) | 70.7% | 74.0% | 0.7011 | 0.7368 | $0.10318 | $0.04599 | Pass |
| [Developer: React](required-id-map/results/dev-react/report.json) | 78.7% | 78.7% | 0.7831 | 0.7820 | $0.06216 | $0.02393 | Fail |
| [Developer: TensorFlow](required-id-map/results/dev-tensorflow/report.json) | 82.0% | 80.0% | 0.8202 | 0.8007 | $0.14730 | $0.09435 | Fail |
| [Developer: VS Code](required-id-map/results/dev-vscode/report.json) | 65.0% | 64.7% | 0.6175 | 0.5998 | $0.07315 | ≥ $0.04196 | Quality drops; cost incomplete |

- Feature requests: **29.5% cheaper**, with accuracy rising from 87.4% to 90.4%. Of 500 records, the cascade fixed 27 baseline mistakes and introduced 12 different mistakes.
- OpenCV: **55.4% cheaper**, with accuracy rising from 70.7% to 74.0%; 19 improvements and nine regressions.
- React: 78.7% accuracy in both arms, but macro-F1 fell slightly; the strict two-metric quality gate does not pass.
- UX bug reports: cheaper but one fewer correct answer, so the gate fails.
- Usage experiences and general evaluations: the cascade was both worse and more expensive.

## Is review worth buying at all?

The user criterion is minimum cost at quality no worse than mini. To avoid
assuming that a cascade is necessary, this **post-hoc ablation** scores every
recorded Jev top label, including labels below 0.95. It uses the original Jev
inference cost and makes no new model calls. It was not part of the frozen
routing experiment and needs a new holdout test before deployment.

| Task | Jev-only accuracy / macro-F1 | Jev-only USD | Meets mini quality? | Cheapest verified variant among the three |
| --- | ---: | ---: | --- | --- |
| UX: bug reports | 92.0% / 0.9169 | $0.00918 | No | Mini alone |
| UX: feature requests | 90.6% / 0.8401 | $0.00905 | Yes | Jev alone |
| UX: general evaluations | 79.4% / 0.7893 | $0.00918 | Yes | Jev alone |
| UX: usage experiences | 40.6% / 0.4043 | $0.00909 | No | Mini alone |
| Developer: Bitcoin | 78.3% / 0.7753 | $0.01570 | Yes | Jev alone |
| Developer: OpenCV | 78.7% / 0.7888 | $0.01536 | Yes | Jev alone |
| Developer: React | 78.0% / 0.7752 | $0.01070 | No | Mini alone |
| Developer: TensorFlow | 80.3% / 0.8028 | $0.02029 | No | Mini alone |
| Developer: VS Code | 67.0% / 0.6266 | ≥ $0.01287 | Yes | Mini alone; incomplete cost prevents a minimum claim |

On feature extraction, Jev alone costs **51.0% less than mini** and scores
**90.6% versus 87.4% accuracy**. On OpenCV it costs **85.1% less**, with
**78.7% versus 70.7% accuracy**. On bugs, React and TensorFlow, retaining mini
is the quality-preserving choice among these measured variants. These are
dataset-specific observations, not automatic runtime recommendations.

[Machine-readable three-variant comparison](variants.json). The runtime still
uses its configured confidence threshold; no defaults were changed from this ablation.

## A measurement failure we fixed, not a model win

The first experiment used an array of `{id, choice}` objects. The model could
satisfy that JSON shape while omitting or duplicating IDs. Sixteen developer
batches failed validation, affecting 400 item slots across the two arms. Whole
failed batches count as incorrect, and **all five original developer comparisons
are excluded from success claims**. Their responses and costs remain in the
[original results](results/) and [summary](summary.json).

We then required each exact input ID as a JSON object property and repeated
**all five developer tasks**, with identical revised contracts in both arms.
That [protocol](required-id-map/protocol.json) was committed at
[80f5382](https://github.com/alsoleg89/decide/commit/80f5382) before the repeats.
**Zero batches failed in the corrected comparisons.** The table above uses
those developer results and the original, valid UX results. No Jev outputs or
labels were replaced. The first nine-task protocol was committed at
[8d72e5d](https://github.com/alsoleg89/decide/commit/8d72e5d).

## Costs and limits

Each cascade price includes the original Jev classification plus actual mini
review, even though replaying Jev locally adds no new bill. One original Jev
response on VS Code lacks complete usage, so its cascade cost is a lower bound
and no percentage saving is claimed. Failed mini responses retain their costs.

The full experiment made **283 paid mini requests**, with **$1.445132** in total
reported OpenAI usage at the saved rates, including the discarded-contract
experiment and all repeats. This experiment bill is separate from the per-task
deployment costs above. The earlier Jev calls are not charged twice in that bill.

Standard mini rates: $0.40/M input, $0.10/M cached input and $1.60/M output;
[official pricing](https://developers.openai.com/api/docs/pricing), checked 2026-09-20,
saved in [prices.json](prices.json). These are list-price estimates, not invoices.
Usage, cache buckets, actual model IDs and paired correct/incorrect outcomes
are included in each report. No missing prices are imputed.

This is a **controlled stateless classifier comparison**, not an autonomous
Codex/Claude session. It excludes planning, MCP tool schemas, file-reading tool
calls and conversation history. The observed sample gate checks accuracy and
macro-F1, not statistical noninferiority or globally minimum cost. No fresh
holdout validates the retrospective no-review policy yet. Public corpora may
have appeared in training; labels are not independently adjudicated.

## Reproduce without paying again

Archived plans omit source request bodies but keep IDs and request hashes.
Responses retain the fields used for scoring; credentials and input texts are
not published. From the repository root:

```sh
uv run --locked python benchmark_cascade.py score \
  --directory benchmarks/cascade/gpt-4.1-mini/results/ux-feature_request \
  --archive benchmarks/workflows/results/ux-feature_request \
  --prices benchmarks/cascade/gpt-4.1-mini/prices.json

uv run --locked python benchmark_cascade.py score \
  --directory benchmarks/cascade/gpt-4.1-mini/required-id-map/results/dev-opencv \
  --archive benchmarks/workflows/results/dev-opencv \
  --prices benchmarks/cascade/gpt-4.1-mini/prices.json
```

For new paid runs, regenerate the [workflow inputs](../../workflows/README.md),
then use the [shared runner](../README.md). Rebuilding the original array
request hashes requires commit `8d72e5d`; current preparation uses required IDs.
Frozen inputs, rubrics, batching and model snapshots stay explicit.

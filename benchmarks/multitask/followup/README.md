# New-record follow-up: frozen before inference

This protocol is committed before any follow-up Jev calls. It tests the thresholds
selected in the [retrospective calibration experiment](../threshold-validation/README.md)
on previously unqueried records from the same public test corpora.

| Task | New records | Frozen threshold | Accepted-error budget |
| --- | ---: | ---: | ---: |
| IMDb movie reviews | 1,000 | 0.95 | 5% |
| AG News topics | 1,000 | 0.99 | 10% |
| Banking77 support intents | 770 | 0.99 | 10% |

The three tasks were chosen because the earlier bounded selection could support
these error budgets. This is a follow-up of promising cases, not an unbiased
estimate over arbitrary tasks. No claim is made that 5% or 10% is appropriate for
every use case; these are error budgets, not target review fractions.

The [protocol](protocol.json) freezes exact IDs, input/label/rubric hashes, source
hashes, model, server code and previous selection-report hash. Seed: `20260921`.
All prior evaluated IDs and their exact contents are excluded, including the
earlier 400 AG News records. Eligible texts are deduplicated before sampling.
IMDb and news use uniform samples; Banking77 uses ten records per intent.
Rubric wording is unchanged. Model: `jev-1.13.0`, concurrency 4, no review preview.

Primary outcomes: errors among accepted decisions at the frozen threshold,
review fraction, overall accuracy (provider failures count as incorrect),
macro-F1, Jev usage/cost and live full-review JSON bytes. Report sampling intervals
and both observed-budget comparisons and uncertainty. Do not tune thresholds or
replace failed predictions after seeing follow-up results. Source train labels
are available only to the local Naive Bayes baseline and are never sent to Jev.

These are new inference records from old public corpora, not a temporal or domain
shift test. The corpora may be present in model pretraining. Full-review JSON
bytes do not measure billed agent tokens or actual expensive-agent review quality.

Preparation is offline after the [parent datasets](../README.md) are downloaded:

```sh
uv run --locked python benchmarks/multitask/followup/prepare.py \
  --previous /tmp/decide-multitask --root /tmp/decide-followup \
  --protocol /tmp/followup-protocol.json
```

The preparation script refuses to overwrite an existing protocol or paid-run
inputs. The committed protocol is the reference; a newly generated protocol must
match it before new inference. The following command makes **paid** calls:

```sh
uv run --locked python benchmarks/multitask/run.py \
  --root /tmp/decide-followup --output /tmp/followup-results \
  --tasks imdb ag-news banking77
```

The runner retains completed inference and refuses to silently restart an
interrupted run. Estimated new Jev inference is approximately $0.11 from the
previous per-task usage; final cost must use the actual returned usage.

# Why some Jev responses were rejected

We repeated all **63 previously rejected cases** from the initial and follow-up
studies once, using the same pinned model, rubric and input. These are diagnostic
repeats, not new evaluation records and not replacements for failed predictions.
The previous parser and the corresponding provider response were recorded together.

| Diagnostic result | Cases |
| --- | ---: |
| Accepted by the response parser on repeat | 40 |
| Rejected again | 23 |
| Rejected with probability sum 0.99 | **23** |
| Missing/extra categories, invalid schema or wrong maximum in those 23 | 0 |

The [API contract](https://docs.typesafe.ai/api) says the probabilities sum to 1.
All 23 reproduced failures instead sum to 0.99, within floating-point noise; all
were Banking77 cases. This is a **one-percentage-point discrepancy**, not ordinary
floating-point roundoff. The numerical cause of rejection is established; the
provider-side cause of the discrepancy is unknown. The other 40 repeats were
valid, so their original failures cannot be diagnosed from these new responses.

## Would accepting the incomplete distributions help?

We replayed the saved responses against the reference labels, hypothetically
removing only the sum check. Confidence and predicted categories were unchanged.

| Confidence threshold | Additional decisions accepted | Additional wrong decisions |
| --- | ---: | ---: |
| 0.8 | 7 | **2** |
| 0.95 | 0 | 0 |
| 0.99 | 0 | 0 |

At 0.8, two of the seven additional decisions would be wrong. At the frozen
follow-up thresholds, relaxing validation would not reduce review at all.
This cohort was selected because of previous failures, so these proportions
must not be generalized to arbitrary batches.

The server therefore keeps the same strict acceptance rule. It now records
`validation_error: "probability_sum"` and the observed `probability_sum` alongside
`error: "invalid_provider_response"`. The record still requires review. These
diagnostics stay in the audit results; the default review queue contains only
the original inputs. No probabilities are normalized or silently repaired.

An offline replay through the updated parser verified that **all 63 diagnostic
decisions remain identical**, apart from the new error details. The original
8,340-record reports remain unchanged.

## Cost and evidence

All 63 diagnostic calls returned HTTP 200, without retries. Captured usage totals
**106,015 input tokens**, corresponding to **$0.00445263** at Jev 1.13.0 list prices.
This is separate from the primary evaluation costs and is not an invoice.
Unlike the original rejected records, these diagnostic responses retain usage.

[Paired provider responses and parser results](responses.jsonl) contain no API
key, request headers or original source text. [Verified summary](summary.json)
includes the reproduced cases, confidence values, label errors and response hash.
Payload hashes identify the exact requests without publishing the source texts.

Reproduce the analysis **offline**, with no API key or downloaded corpus needed:

```sh
uv run --locked python benchmarks/multitask/diagnose_rejections.py \
  --verify --output benchmarks/multitask/rejection-diagnostics/responses.jsonl
```

To make another **paid** diagnostic run, supply the prepared directories from
the two parent studies and a new output path. The command refuses to overwrite
an existing output and stops on authentication or long-cooldown errors:

```sh
uv run --locked python benchmarks/multitask/diagnose_rejections.py \
  --previous /tmp/decide-multitask --followup /tmp/decide-followup \
  --output /tmp/new-rejection-diagnostics.jsonl
```

# Fresh-record validation: can the cheaper policy keep its advantage?

**Yes on both of these selected tasks.** The policy was committed before any
new model calls: accept valid Jev decisions regardless of confidence, and use
GPT-4.1 mini only when Jev cannot process a record. No routing threshold or rubric
was changed after observing this follow-up.

| New task | Records | Mini accuracy / macro-F1 | Selected policy accuracy / macro-F1 | Mini USD | Selected policy USD | Lower cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [Feature requests in app reviews](results/ux-feature_request/report.json) | 1000 | 86.4% / 0.7979 | **90.9% / 0.8391** | $0.03745 | **$0.01817** | **51.5%** |
| [OpenCV issue triage](results/dev-opencv/report.json) | 300 | 67.0% / 0.6618 | **75.7% / 0.7552** | $0.14630 | **$0.03351** | **77.1%** |

Costs include the Jev pass and actual mini fallback. Both costs are complete
under the recorded usage; prices are estimates using the
[saved standard rates](../prices.json), not invoices. Models are pinned to
`jev-1.13.0` and `gpt-4.1-mini-2025-04-14`.

- **1,000 app reviews:** zero fallback calls. Compared with mini, the policy corrected 79 mistakes and introduced 34 others; 830 records were correct in both arms and 57 wrong in both.
- **300 OpenCV issues:** one full oversized record required mini fallback. Compared with mini, the policy corrected 38 mistakes and introduced 12 others; 189 were correct in both arms and 61 wrong in both.
- All mini batches passed the required-ID output contract. Jev made 1,299 provider requests with zero retries; the oversized record was skipped locally and never truncated.

**The selected policy met the preregistered sample gate on both tasks:** final
accuracy and macro-F1 at least the baseline, with lower complete classification
cost. This is stronger evidence than selecting a winning threshold after looking
at the same results. It is not a guarantee for an unseen product or taxonomy.

## What was frozen, and when

The [input/policy protocol](protocol.json) was committed at
[c829031](https://github.com/alsoleg89/decide/commit/c829031) before Jev inference.
The [exact mini request hashes](mini-protocol.json) were committed at
[8966a3d](https://github.com/alsoleg89/decide/commit/8966a3d) before mini inference.
The fallback membership depends only on the frozen policy and Jev results.

- UX: uniform 1,000 from 4,708 remaining unique nonempty French reviews, seed `20260924`; all 500 previously evaluated texts excluded.
- OpenCV: all 300 records in the official NLBSE training partition for that project. Exact content overlap with previously evaluated issues is zero.
- These are new inference records from the **same public corpora**. The two tasks were chosen after earlier promising results. This is not a test of distribution shift or absence from model pretraining.
- The old evaluation records train a supplementary local Naive Bayes baseline. No training examples or reference labels are sent to Jev or mini. NB scored 85.4% on UX and 66.0% on OpenCV, below mini on these samples.
- Reference annotations are not independently adjudicated; both false positives and false negatives remain in the metrics.

## Actual tokens and experiment cost

| Task / arm | Input tokens | Output tokens |
| --- | ---: | ---: |
| ux-feature_request / Jev | 432,505 | 31,000 |
| ux-feature_request / Mini baseline | 61,277 | 8,085 |
| ux-feature_request / Mini fallback | 0 | 0 |
| dev-opencv / Jev | 434,009 | 11,362 |
| dev-opencv / Mini baseline | 351,118 | 3,660 |
| dev-opencv / Mini fallback | 38,144 | 17 |

No mini input tokens were cached. The new experiment used 53 mini calls, costing
**$0.199035** for the baseline and fallback together; new Jev calls cost
**$0.036394**. Total experiment usage estimate: **$0.235428**. This includes both
comparison arms and is separate from the deployment cost of either arm alone.

The accounting fix in the protocol commit recognizes that an item skipped
before any HTTP request adds zero provider cost. Provider errors or retries still
make accounting incomplete when usage is unknown. The skipped item stays in
the review file in full, and its actual mini fallback cost is included above.

## Reproduce

From the repository root, regenerate inputs from the pinned source repositories
and the original workflow inputs:

```sh
uv run --locked python benchmarks/cascade/gpt-4.1-mini/followup/prepare.py \
  --root /tmp/decide-followup-check --previous /tmp/decide-workflows \
  --ux-source /path/to/APIA2022-French-user-reviews-classification-dataset \
  --dev-source /path/to/issue-report-classification \
  --protocol /tmp/decide-followup-protocol.json

# Free: score the archived model responses, including actual fallback.
uv run --locked python benchmark_cascade.py score \
  --directory benchmarks/cascade/gpt-4.1-mini/followup/results/dev-opencv \
  --archive benchmarks/cascade/gpt-4.1-mini/followup/jev/dev-opencv \
  --prices benchmarks/cascade/gpt-4.1-mini/prices.json
```

Source hashes, IDs and labels permit regeneration; published response plans omit
the raw input texts but preserve their frozen request hashes. The
[summary](summary.json) and per-task reports contain confusion matrices,
paired mistakes, actual usage and complete cost calculations.

## What remains unproven

The experiment measures stateless classification and fallback. It excludes agent
planning, MCP tool-schema tokens, tool-driven file reads and conversation history.
The chosen policy was the cheapest verified option in the earlier three-variant
comparison; this follow-up does not prove a global minimum over every model or
routing policy. Production distribution drift and full autonomous-agent cost
still need direct validation.

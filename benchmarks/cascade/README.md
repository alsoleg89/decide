# Compare full classification against Jev plus paid review

**Status: prepared and checked offline; no expensive-model results yet.**
An `OPENAI_API_KEY` is needed for the live experiment. An OpenAI API comparison
is not a measurement of an autonomous Codex or Claude session.

The [`benchmark_cascade.py`](../../benchmark_cascade.py) experiment uses the
[2,770-record follow-up](../multitask/followup/RESULTS.md). It compares:

- **Baseline:** the expensive model classifies every record.
- **Cascade:** keep Jev's accepted decisions and ask the same expensive model to
  classify only the review queue. The reviewer receives neither reference labels
  nor Jev's proposed answers. No assumption of perfect review is made.

Both arms use the same question, criteria, system instruction, output schema and
batch size. Records have a fixed hash order. The original Jev cost is charged to
the cascade even though replaying those decisions costs nothing now. Reference
labels enter scoring only, not the request bodies. Requests are stateless, with
no tools, conversation history or MCP orchestration included.

## A quality limit already established by the existing decisions

Even a perfect reviewer cannot correct a wrong answer that was never sent to
review. These are **theoretical accuracy ceilings**, not measured reviewer results:

| Task | Records | Already accepted errors | Accuracy ceiling with perfect review | Baseline / review API requests at batch size 25 |
| --- | ---: | ---: | ---: | ---: |
| IMDb | 1,000 | 10 | 99.0% | 40 / 4 |
| AG News | 1,000 | 53 | 94.7% | 40 / 11 |
| Banking77 | 770 | 14 | 98.18% | 31 / 15 |

A reviewer can introduce further errors. If a full-model baseline exceeds the
ceiling, matching its quality requires changing the routing policy, not simply
buying a better reviewer. The frozen thresholds stay unchanged in this comparison.

## Prepare without making API calls

Prepare the [follow-up inputs](../multitask/followup/README.md). For IMDb:

```sh
uv run --locked python benchmark_cascade.py prepare \
  --root /tmp/decide-followup/imdb \
  --archive benchmarks/multitask/followup/results/imdb \
  --model gpt-6-astra --directory /tmp/cascade-imdb
```

The plan contains the complete paid request bodies and hashes. Keep it outside
the repository because it includes source texts. Inspect it before running;
changing model or batch size requires a new plan. The example model is supported
by the [Responses API and Structured Outputs](https://developers.openai.com/api/docs/models/gpt-6-astra).
Account access has not been verified. The script adds no SDK dependency.
[Preparation manifest](preparation.json) records the three local plan hashes
and zero live calls; it contains no source texts.

## Run paid classification, then score offline

Set `OPENAI_API_KEY` locally in the launching environment, then:

```sh
# PAID: 44 requests for the complete IMDb comparison at batch size 25.
uv run --locked python benchmark_cascade.py run --directory /tmp/cascade-imdb

# Free: grade actual model answers, including failed/refused/incomplete outputs.
uv run --locked python benchmark_cascade.py score \
  --directory /tmp/cascade-imdb \
  --archive benchmarks/multitask/followup/results/imdb \
  --prices benchmarks/cascade/gpt-6-astra-prices.json
```

The runner uses the global standard-processing endpoint, `store: false`, no
automatic retries, and an 8,192-token output cap per request, including reasoning.
This cap is not a dollar budget: input, cache writes and output all cost money.
The maximum **output-only** cost of 44 full-cap short-context Astra responses is
$18.02 at the saved rates; actual token use is unknown until inference. Check
current pricing and choose a model/budget before launching the paid command.

A failed HTTP request stops the run after saving its status and body hash;
error text is omitted because authentication errors may echo credentials. Existing output
is never silently overwritten or resumed; inspect interrupted calls before any
new paid run. A completed API response with invalid decisions counts every item
in that batch as failed. Duplicate/missing/unknown IDs are rejected. An incomplete
run cannot be published by `score` as a complete comparison.

## What the report measures

- Final baseline and cascade accuracy, macro-F1 and confusion matrices.
- Actual input, cached-input, cache-write, output and reasoning token counts.
  Reasoning is already included in output tokens and is never charged twice.
- Measured API time for each arm, separate from the earlier Jev elapsed time.
- A list-price estimate, using the supplied model price snapshot and the actual
  returned model, processing tier and per-request context length.

The saved [price snapshot](gpt-6-astra-prices.json) is from
[official pricing](https://developers.openai.com/api/docs/pricing), checked
2026-09-20. Cache read/write accounting follows the
[official calculation](https://developers.openai.com/api/docs/guides/prompt-caching#how-to-optimize-prompt-caching).
Any missing usage, unsupported model/tier, or incomplete original Jev accounting
suppresses a point estimate of dollar savings. Cache effects remain visible;
alternating arm order does not prove identical cold-cache conditions.

This controlled classifier comparison excludes autonomous planning, tool-schema
tokens, file-reading calls and agent conversation history. Those require a later
end-to-end agent experiment. Offline tests validate the measurement code only;
their mocked answers are never reported as model quality or cost evidence.

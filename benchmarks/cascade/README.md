# Compare Jev against GPT-4.1 mini

**[Live UX and developer results →](gpt-4.1-mini/README.md)**

The user-selected criterion is **quality no worse than the comparison model,
at minimum total cost**. The experiment checks observed final accuracy and
macro-F1, plus complete classification costs. It distinguishes observed sample
results from proof of future quality or a minimum across all routing policies.

`benchmark_cascade.py` compares the same model on every input against archived
Jev decisions plus actual model review. Original Jev costs count toward the
cascade. Reference labels and Jev guesses are never sent to the reviewer.

The current output schema requires every input ID as a property, preventing the
missing/duplicate IDs that invalidated the first developer comparison. Scoring
also supports the original array responses so the historical failures remain
reproducible. No failed request is retried or silently overwritten.

## Prepare and run

First prepare the [workflow inputs](../workflows/README.md). For feature requests:

```sh
uv run --locked python benchmark_cascade.py prepare \
  --root /tmp/decide-workflows/ux-feature_request \
  --archive benchmarks/workflows/results/ux-feature_request \
  --model gpt-4.1-mini-2025-04-14 --directory /tmp/cascade-features

# PAID: requires OPENAI_API_KEY in the launching environment.
uv run --locked python benchmark_cascade.py run --directory /tmp/cascade-features

# Free: score the actual model responses.
uv run --locked python benchmark_cascade.py score \
  --directory /tmp/cascade-features \
  --archive benchmarks/workflows/results/ux-feature_request \
  --prices benchmarks/cascade/gpt-4.1-mini/prices.json
```

Plans contain source texts and belong outside Git. Published result plans omit
those request bodies while retaining IDs and hashes. Model or batch-size changes
require new plans. The default batch has 25 items and an 8,192-token output cap.
This token cap is not a spending limit. Interrupted runs retain completed
responses and a pending-request marker where applicable; inspect them before
starting any new paid run.

## What counts

Both arms use the same rubric, instructions, schema and batch size. API calls
alternate arms where both have work. Actual model IDs, cached/input/output
usage, failures, elapsed API time and paired mistakes are recorded. Pricing
requires complete usage and the expected returned model and processing tier.
Missing Jev usage suppresses a dollar-savings estimate.

`controlled_sample_comparison` reports whether accuracy and macro-F1 are both
at least the baseline, and whether total classification cost is lower. Invalid
responses prevent a clean quality-comparison verdict. This check does not
establish statistical noninferiority or a globally cheapest policy.

The experiment is a stateless API classifier comparison. It excludes agent
planning, MCP tool definitions, file-reading calls and conversation history.
A full agent-loop experiment and fresh validation of the selected policy remain
necessary for the broader goal.

Earlier [IMDb/news/banking plans](preparation.json) and their saved price example
were prepared before the user selected GPT-4.1 mini. **They were never run.**

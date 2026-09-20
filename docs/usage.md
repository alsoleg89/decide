# Setup and reference

[← Back to decide](../README.md)

## Install

The simplest setup uses [uv](https://docs.astral.sh/uv/) to run a pinned GitHub
revision without a local checkout. `uvx` manages the Python environment and
caches the installation. Git is needed to fetch the source.

The MCP launch command is:

```sh
uvx --python 3.11 --from git+https://github.com/alsoleg89/decide@f6771e5beaf4ec58398f261b62ee59e316f4e61e decide-mcp
```

This starts a stdio server for an MCP client; it is not an interactive CLI.
Configure it in the client below. The revision includes per-label confidence
cutoffs and has been checked from a fresh cache. No PyPI publication is assumed.
Update the pinned revision deliberately when adopting a newer version.

For benchmark reproduction or development, clone the repository instead:

```sh
git clone https://github.com/alsoleg89/decide.git
cd decide
uv sync --locked
```

Get a key from the [TypeSafe console](https://console.typesafe.ai). Configure
`TYPESAFE_API_KEY` in the server's environment, not in tool arguments or source
control. `DECIDE_ROOT` is the directory containing the data to classify; it can
be different from the directory where this package is installed.

### Codex

Add to your Codex `config.toml`, replacing the data directory:

```toml
[mcp_servers.decide]
command = "uvx"
args = ["--python", "3.11", "--from", "git+https://github.com/alsoleg89/decide@f6771e5beaf4ec58398f261b62ee59e316f4e61e", "decide-mcp"]
env_vars = ["TYPESAFE_API_KEY"]
startup_timeout_sec = 120
tool_timeout_sec = 1800

[mcp_servers.decide.env]
DECIDE_ROOT = "/absolute/path/to/your/project"
```

The key must be present in the environment of the Codex process. See
[Codex MCP configuration](https://developers.openai.com/codex/mcp).
Large batches can exceed the default tool timeout; split the source or increase
the host's timeout to suit your batch size and API latency.

### Claude Code / Claude Desktop

Use this `mcpServers` entry in Claude Code's project `.mcp.json` or your Claude
Desktop configuration. Replace the data directory and key locally:

```json
{
  "mcpServers": {
    "decide": {
      "command": "uvx",
      "args": ["--python", "3.11", "--from", "git+https://github.com/alsoleg89/decide@f6771e5beaf4ec58398f261b62ee59e316f4e61e", "decide-mcp"],
      "env": {
        "TYPESAFE_API_KEY": "YOUR_KEY",
        "DECIDE_ROOT": "/absolute/path/to/your/project"
      }
    }
  }
}
```

Keep configurations containing a real key out of Git. Restart the client after
configuration. See [Claude Code MCP](https://code.claude.com/docs/en/mcp).

If a desktop client cannot find `uvx`, use its absolute executable path (`which
uvx` on macOS/Linux, `where uvx` on Windows). The first launch downloads the
runtime/dependencies; subsequent launches use the cache. For an existing local
checkout, use `command = "uv"` and arguments
`["run", "--locked", "--directory", "/absolute/path/to/decide", "decide-mcp"]`.

### Check an installation without a key

From a checkout with dependencies installed:

```sh
uv run --locked python smoke_install.py
```

Or test a separately installed command:

```sh
python smoke_install.py /absolute/path/to/decide-mcp
```

The check starts the command from an unrelated temporary directory, performs the
MCP handshake, discovers `decide`, reads a deliberately oversized record and
verifies its intact review artifact and per-label settings. It uses a dummy key
and makes zero provider requests. This verifies installation/protocol wiring,
not model quality. Live quality evidence is in the [benchmarks](../benchmarks/README.md).

## Use

Ask your agent:

> Use decide to classify logs/app.log into normal, investigate, and urgent.
> Pass the path directly; don't read the log into your context first.
> Always bring urgent cases to me, and review anything below 0.8 confidence.

The agent calls the single tool `decide`:

```json
{
  "question": "Which operational category best fits this log entry?",
  "criteria": {
    "normal": "Routine successful operation with no intervention needed",
    "investigate": "A warning or failure that needs investigation",
    "urgent": "An outage, data loss, or immediate service interruption"
  },
  "source": {"kind": "lines", "paths": ["logs/app.log"]},
  "confidence_threshold": 0.8,
  "review_labels": ["urgent"]
}
```

Use exactly one input mode:

| Input | Example | One decision per |
| --- | --- | --- |
| Log lines | `"source": {"kind":"lines","paths":["logs/app.log"]}` | Nonblank line; ID includes path and original line number |
| Files | `"source": {"kind":"files","paths":["src/**/*.py"]}` | Entire UTF-8 file; ID is its relative path |
| JSONL | `"source": {"kind":"jsonl","paths":["tickets.jsonl"]}` | Record with unique `id` and `content` fields |
| Inline | `"items": [{"id":"t-1","content":"Login fails"}]` | Item; content can be any JSON value |

JSONL example:

```jsonl
{"id":"t-1","content":{"title":"Login fails","body":"A 500 response after submitting credentials"}}
{"id":"t-2","content":{"title":"Dark mode","body":"Please add a dark theme"}}
```

For multiline stack traces, group each event into a JSONL record first. `lines`
intentionally treats each line independently. `context` adds shared domain
guidance to each item; it is sent and billed on every request.

### What comes back

The tool returns:

- `total`, `completed`, `accepted`, `accepted_by_label`, `review_count`,
  `review_fraction`, `failed`, and `review_reasons`.
- `review`: empty by default. Set `review_limit` to opt into previews, bounded
  to about 20 KB in total. Each preview contains an ID, proposed label, confidence, probabilities, reason
  and up to 1,000 characters of serialized content. A preview is not the full input.
- `results_path`: every decision, including errors, with its original ID and index.
- `review_path`: **all** cases requiring review as `{id, content}`, with full
  original content. Probabilities, reasons and usage stay in `results_path`; join
  by ID when you need the audit details.
- `review_omitted`: cases in the review file that were not included in the preview.
- `usage`: token counts from validated successful responses. `complete: false`
  means provider failures or retries prevented complete accounting. Oversized
  items skipped before any request add no unknown provider cost. `requests_made` and
  `retries` show the request overhead. This is not an invoice or spending limit.

Outputs live in `DECIDE_ROOT/.decide/<run-id>/`. Each run also stores
`request.json` (rubric/settings) and `summary.json`. JSONL rows are appended and
flushed as requests finish; their order is completion order, and `index` restores
input order. If interrupted, finished rows remain on disk; absent `summary.json`
means the run did not finish. There is no automatic resume or cache: calling the
tool again sends the inputs again and can incur charges.

The default `review_limit: 0` returns counts and artifact paths, so the agent
reads only the records needed for its next step. Use `review_limit: 20` if
previews help triage. This changes the preview, not which decisions require review.

Read `review.jsonl` in small slices **starting at line 1**. Previews are truncated
and may not form a prefix of the file; their count is not a safe offset. Track
which IDs you have actually reviewed. Process
`results.jsonl` with a script instead of dumping all decisions into agent context:

```sh
jq -c 'select(.status == "accepted") | {id, choice}' /path/to/results.jsonl
sed -n '1,20p' /path/to/review.jsonl
```

`completed` counts processed records, including those sent to review. It does
not mean the final task is done. Before reporting completion, combine accepted
choices with resolved review choices and verify exactly one decision per input ID.
A [live mini run](../benchmarks/agent/gpt-4.1-mini/README.md#first-run-a-real-completion-failure)
otherwise stopped after MCP and left one issue unresolved. Applications can enforce
this completion check before allowing a final answer.

This tool classifies; it never runs commands, deletes files, or applies decisions.

### Different cutoffs for different labels

`confidence_thresholds` optionally overrides the global `confidence_threshold`
for named labels. For example, `confidence_threshold: 0` with
`confidence_thresholds: {"no": 0.9}` accepts valid positive answers and reviews
negative answers below 0.9. Unspecified labels use the global cutoff; equality
is accepted. `review_labels` and provider/input errors still force review.
Overrides must use existing criteria labels and finite numeric values in 0..1.
Both the request artifact and summary record the overrides.

The [new UX validation](../benchmarks/agent/ux-recall/README.md) measures this
policy on 1,000 new reviews, including actual mini review and its cost.
This is useful when false negatives and false positives have different costs.
It is a routing control, not an accuracy guarantee. The standalone evaluator's
threshold sweep tests alternative global cutoffs; it does not reproduce per-label
overrides. Use the actual accepted/review records or a live workflow comparison
when evaluating an asymmetric policy.

### Tune for bytes saved, not a review quota

Run the offline evaluator on a labeled sample, adding the original inputs:

```sh
uv run --locked python evaluate.py --labels labels.jsonl --results results.jsonl --inputs items.jsonl
```

The threshold sweep shows accepted-label errors and how much input JSON stays
out of review. A few long records can dominate context, so item counts alone
are insufficient. This input-only metric excludes response metadata; use
[`benchmark_real.py`](../benchmarks/README.md#benchmark-your-own-labeled-data) for
an actual call's savings including its summary and all full review records.
Choose a threshold on calibration data, then check it on a separate sample.
Neither a confidence score nor an in-sample sweep guarantees future accuracy.

## Settings and limits

| Setting | Default | Meaning |
| --- | --- | --- |
| `TYPESAFE_API_KEY` (environment) | Required | TypeSafe authentication |
| `DECIDE_ROOT` (environment) | Process working directory | Allowed input/output directory |
| `DECIDE_MODEL` (environment) | `jev-latest` | Use a pinned Jev model for repeatability |
| `confidence_threshold` (tool) | `0.8` | Review when Jev confidence is **below** this value |
| `confidence_thresholds` (tool) | `{}` | Per-label cutoff overrides; omitted labels use the global cutoff |
| `review_labels` (tool) | `[]` | Always review these labels, regardless of confidence |
| `concurrency` (tool) | `4` | Concurrent requests per invocation, 1–16 |
| `review_limit` (tool) | `0` | Preview count, 0–100; never drops records from the review file |

Jev's [`confidence`](https://docs.typesafe.ai/confidence) describes the shape of
the probability distribution. It is not `max(probabilities)` and a threshold of
0.8 does not promise 80% accuracy. Validate on labeled data and sample accepted
decisions before relying on a threshold. Add an `other` label to incomplete
taxonomies, and include it in `review_labels` when it should always escalate.

Up to 10,000 items and 32 MB of serialized input per call. Items over 128 KB of
serialized content are escalated without sending a truncated version to Jev.
Inputs must be regular UTF-8 files within `DECIDE_ROOT`; parent traversal and
symlinks escaping the root are rejected. File globs skip dotfiles, hidden
directories, `node_modules`, `vendor`, and `__pycache__`. These exclusions are
not a secret scanner or a `.gitignore` implementation: scope your paths to data
you intend to send to TypeSafe. Logs and JSONL paths are explicit.

HTTP 408, 429, 5xx and transport failures get up to three attempts with bounded
backoff. Permanent failures, invalid probability distributions and malformed
responses go to review. Authentication failure or a requested cooldown over 30
seconds stops new requests for the rest of the batch. Retry headers support
seconds, HTTP dates and `retry-after-ms`. Error response bodies are not exposed. Provider requests use the
[TypeSafe API contract](https://docs.typesafe.ai/api) and do not follow redirects.

## Development

```sh
uv sync --locked
uv run --locked python -m coverage run -m unittest -v
uv run --locked python -m coverage report
uv build
```

Tests use the real MCP SDK, including a stdio subprocess, with a mocked paid HTTP
endpoint. The 257 tests cover 2,000 log lines, 300 files, Unicode and byte limits,
threshold routing, forced review, 100 seeded probability distributions and their
incorrect winners, source validation, symlink boundaries, cancellation, disk
failure, concurrent runs, HTTP/transport failures, retry headers, authentication,
full local artifacts, legacy MCP and benchmark accounting. Instructions embedded
in input are checked for separation from the rubric; this does not establish
Jev's resistance to prompt injection. The synthetic 95%/5% test verifies routing,
not real-world classification accuracy.

Local checks passed on Python 3.11, 3.12, 3.13 and 3.14. CI is configured for Python
3.11–3.14 on Linux, macOS and Windows, with a 95% minimum coverage gate on Linux.
**GitHub Actions is currently blocked by the account's billing lock; the hosted
matrix has not run.** No API key is required by CI.

Live smoke check on 2026-09-19: the installed stdio command processed 12 synthetic
log entries through Jev 1.13.0 in 2.386 seconds. Seven were accepted, two escalated
for low confidence, and three escalated by the `urgent` label override. Zero final
errors; two requests needed a retry. Successful responses reported 4,761 input
and 507 output tokens. This is an integration check, not an accuracy benchmark
or a measurement of total agent cost.

# Luna: the same job, with and without decide

Pre-inference protocol. Two existing datasets: 1,000 French app reviews for UX
feature extraction and 300 OpenCV issues for developer triage. These are reused
records, not a new independent sample. One run per arm; no result-based tuning.

Model: `gpt-5.6-luna`, reasoning `none`, standard processing. Jev: `jev-1.13.0`.
The existing guided tool loop keeps 25-record batches, exact-ID output checks,
real stdio MCP and identical compaction in both arms. UX uses global cutoff 0
and `no: 0.9`; developer triage uses error-only fallback. Jev is called afresh.

Success requires complete artifacts, lower complete inference cost, and no
regression in accuracy, macro-F1, or precision/recall for the frozen quality
labels (`yes` for UX; all three classes for developer triage). Report failures
and every billable response too. Time is one observation, not a latency distribution.

[UX protocol](ux-feature_request/protocol.json) · [Developer protocol](dev-opencv/protocol.json) · [Official price snapshot](prices.json)

Input reconstruction follows the [UX study](../ux-recall/README.md) and the
[OpenCV follow-up](../../cascade/gpt-4.1-mini/followup/README.md). Then:

```sh
python benchmarks/agent/gpt-5.6-luna/prepare.py --destination /tmp/luna \
  --ux-source /tmp/ux-recall/inputs --dev-source /tmp/decide-mini-followup/dev-opencv
# Set OPENAI_API_KEY; also set TYPESAFE_API_KEY for the decide arm.
python benchmark_agent.py run --root /tmp/luna/ux-feature_request/inputs --directory /tmp/luna/ux-feature_request/run --arm baseline
python benchmark_agent.py run --root /tmp/luna/ux-feature_request/inputs --directory /tmp/luna/ux-feature_request/run --arm decide
python benchmark_agent.py run --root /tmp/luna/dev-opencv/inputs --directory /tmp/luna/dev-opencv/run --arm decide
python benchmark_agent.py run --root /tmp/luna/dev-opencv/inputs --directory /tmp/luna/dev-opencv/run --arm baseline
```

Existing output directories are never resumed or overwritten. Labels are used
only by the scorer. Source-bearing read traces are published as IDs and hashes;
raw source text and keys stay out of the public archive.

# Repeat with host-enforced completion

Frozen before paid calls. Same datasets, rubrics, batch size, history compaction,
prices, arm order, output contract and limits as the [original experiment](../README.md).
The one change: every unfinished step sends `tool_choice: required`; only a
successful `finish` enables a final answer. Both arms repeat in full. This
prevents the premature completion observed in the first OpenCV decide arm.

This is a guided, host-enforced workflow using actual GPT-4.1 mini tool calls and
a real stdio MCP server. It does not test autonomous policy selection, native
Codex/Claude overhead, or an unseen quality sample. No source records or reference
labels changed after results. All costs include both providers and every model turn.

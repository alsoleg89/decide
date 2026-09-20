# Installation and release check

## v0.1.1 — current release

261 offline tests passed on macOS arm64/Python 3.11 and Linux arm64/Python 3.12,
with 97% server coverage. Regression checks include a real corrupt gzip body,
another HTTP exception, and missing/relative data roots: unaffected records
complete and invalid roots cannot read files or make requests. Cancellation
and disk-failure checks still pass.

The wheel and sdist include MIT and match the source. The wheel was built from
the sdist. A clean installed-command MCP check passed on both platforms with
zero provider calls. A fresh-cache installation from the published wheel URL
was also verified; Git and the benchmark archive are no longer needed.

[Download v0.1.1](https://github.com/alsoleg89/decide/releases/tag/v0.1.1): wheel,
sdist and SHA256SUMS. No PyPI upload or GitHub Actions. Windows is unverified.

All 14 historical agent-arm reports recompute without changed costs or quality
scores. The Jev price snapshot documents the old assumption after the fact; new
protocols embed it before inference. Statistical diagnostics are post-hoc and
do not rewrite any frozen gate.

## v0.1.0 — historical release verification

Checked on 2026-09-20: macOS arm64 / Python 3.11.15 (suite and Git installation),
Python 3.13.14 (fresh wheel installation), and an isolated Linux arm64 Alpine
container / Python 3.12.14 (wheel installation and suite).

- Built both wheel and sdist; the wheel was built from the sdist.
- Installed the wheel into a new virtual environment, outside the checkout.
- Verified the installed module and packaged source match `decide.py` exactly.
- Passed `smoke_install.py`: stdio handshake, tool discovery, JSONL source paths,
  per-label cutoffs and an intact oversized review record, with zero provider requests.
- Independently passed the same check through `uvx` with a fresh cache and the
  `v0.1.0` GitHub release used by that version’s setup guide; no local clone was used by the server.
- Linux also passed installation of the exact release wheel, the installed-command
  smoke check, and the 257-check suite, with 97% server coverage.
  The container used read-only source/artifact mounts and was removed afterward.
- At v0.1.0, the macOS suite had 257 checks passed, 97% server coverage. Paid model-quality results
  are separate: [new UX validation](../benchmarks/agent/ux-recall/README.md).

The fresh installation resolved `mcp 2.2.0`, `httpx2 2.13.0` and
`pydantic 2.13.5`. Package metadata links to documentation, issues and benchmarks.
The wheel contains the single server module and distribution metadata; benchmark
archives and tests are not bundled into the runtime package.

Release checks run locally, without GitHub Actions. Windows and the full
OS/Python matrix remain unverified. The tested Linux image was
`python:3.12-alpine`, digest
`sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a`.

The project is released under [MIT](../LICENSE). Both wheel and sdist include
`LICENSE`, and package metadata declares the MIT license. The
[v0.1.0 GitHub release](https://github.com/alsoleg89/decide/releases/tag/v0.1.0)
provides a wheel, sdist and `SHA256SUMS`. No package has been uploaded to PyPI;
use the versioned GitHub installation command or the downloadable wheel.

## Public-result integrity

All ten published agent-arm reports were recomputed from their archived model
responses and final labels, with exactly unchanged results. The scorer now
requires every numbered response recorded in the run state. A deliberately
removed response correctly marks cost and completion as incomplete instead of
quietly lowering the bill. A missing/mismatched final answer also invalidates
completion. The regression is covered by the offline agent test.

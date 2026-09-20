# Installation and release check

Checked on 2026-09-20: macOS arm64 / Python 3.11.15 and an isolated
Linux arm64 Alpine container / Python 3.12.14.

- Built both wheel and sdist; the wheel was built from the sdist.
- Installed the wheel into a new virtual environment, outside the checkout.
- Verified the installed module and packaged source match `decide.py` exactly.
- Passed `smoke_install.py`: stdio handshake, tool discovery, JSONL source paths,
  per-label cutoffs and an intact oversized review record, with zero provider requests.
- Independently passed the same check through `uvx` with a fresh cache and the
  pinned GitHub revision in the setup guide; no local clone was used by the server.
- Linux also passed installation of the exact release wheel, the installed-command
  smoke check, and the 257-check suite at `7ebd33c`, with 97% server coverage.
  The container used read-only source/artifact mounts and was removed afterward.
- Current macOS suite: 257 checks passed, 97% server coverage. Paid model-quality results
  are separate: [new UX validation](../benchmarks/agent/ux-recall/README.md).

The fresh installation resolved `mcp 2.2.0`, `httpx2 2.13.0` and
`pydantic 2.13.5`. Package metadata links to documentation, issues and benchmarks.
The wheel contains the single server module and distribution metadata; benchmark
archives and tests are not bundled into the runtime package.

The CI workflow now also checks the installed command. **The hosted platform
matrix remains unverified:** [the inspected run](https://github.com/alsoleg89/decide/actions/runs/35492885308)
did not start because GitHub reported an account billing lock. The local Linux
container check does not cover Windows or the full hosted OS/Python matrix.
The tested image was `python:3.12-alpine`, digest
`sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a`.

Release publication still needs a license decision from the repository owner.
No license grant has been added by assumption. No package has been uploaded to PyPI.
The release candidate uses GitHub source installation and downloadable artifacts.

## Public-result integrity

All ten published agent-arm reports were recomputed from their archived model
responses and final labels, with exactly unchanged results. The scorer now
requires every numbered response recorded in the run state. A deliberately
removed response correctly marks cost and completion as incomplete instead of
quietly lowering the bill. A missing/mismatched final answer also invalidates
completion. The regression is covered by the offline agent test.

# Installation and release check

Checked locally on macOS arm64, Python 3.11.15, 2026-09-20.

- Built both wheel and sdist; the wheel was built from the sdist.
- Installed the wheel into a new virtual environment, outside the checkout.
- Verified the installed module and packaged source match `decide.py` exactly.
- Passed `smoke_install.py`: stdio handshake, tool discovery, JSONL source paths,
  per-label cutoffs and an intact oversized review record, with zero provider requests.
- Independently passed the same check through `uvx` with a fresh cache and the
  pinned GitHub revision in the setup guide; no local clone was used by the server.
- Local suite: 257 checks passed, 97% server coverage. Paid model-quality results
  are separate: [new UX validation](../benchmarks/agent/ux-recall/README.md).

The fresh installation resolved `mcp 2.2.0`, `httpx2 2.13.0` and
`pydantic 2.13.5`. Package metadata links to documentation, issues and benchmarks.
The wheel contains the single server module and distribution metadata; benchmark
archives and tests are not bundled into the runtime package.

The CI workflow now also checks the installed command. **The hosted platform
matrix remains unverified:** [the inspected run](https://github.com/alsoleg89/decide/actions/runs/35492885308)
did not start because GitHub reported an account billing lock. Local checks do
not establish Windows or Linux installation success.

Release publication still needs a license decision from the repository owner.
No license grant has been added by assumption. No package has been uploaded to PyPI.
The release candidate uses GitHub source installation and downloadable artifacts.

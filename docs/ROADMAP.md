# Remaining work

These are proposals, not implemented guarantees or promises of a release date.

- Assess additional unit conversions/dimensional algebra only against concrete domain needs; current linear lengths deliberately exclude them.
- Assess long-chain rotation drift and whether explicit reconditioning is needed.
- Investigate reused-transform validation amortization with matched caller/codegen
  controls; immutable preparation is one design option, not an approved API.
  [Host characterization](performance.md) retains the initial evidence and limits.
- Extend performance characterization only for concrete target/workload needs;
  current host results are not universal timing guarantees.
- Expand domain examples and populate diagrams where they explain a concrete workflow.
- Validate execution and timing on real embedded hardware; CI cross-compilation alone is insufficient.
- Define release/versioning and compatibility policy before the next published release.

Current behavior is specified in [requirements](requirements/requirements.md).
Completed work belongs in the [changelog](../CHANGELOG.md), not a stale checklist here.

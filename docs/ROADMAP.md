# Remaining work

These are proposals, not implemented guarantees or promises of a release date.

- Assess additional unit conversions/dimensional algebra only against concrete domain needs; current linear lengths deliberately exclude them.
- Assess long-chain rotation drift and whether explicit reconditioning is needed.
- Review the [borrowed-validation prototype](borrowed_validation.md): caller-local
  hoisting is competitive, so a public borrowed capability needs an ergonomic
  case and explicit preparation-error decision. General batch semantics remain
  unapproved. [Initial host characterization](performance.md) is retained.
- Extend performance characterization only for concrete target/workload needs;
  current host results are not universal timing guarantees.
- Expand domain examples and populate diagrams where they explain a concrete workflow.
- Validate execution and timing on real embedded hardware; CI cross-compilation alone is insufficient.
- Define release/versioning and compatibility policy before the next published release.

Current behavior is specified in [requirements](requirements/requirements.md).
Completed work belongs in the [changelog](../CHANGELOG.md), not a stale checklist here.

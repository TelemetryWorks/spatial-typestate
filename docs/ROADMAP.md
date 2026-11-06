# Remaining work

These are proposals, not implemented guarantees or promises of a release date.

- Complete the [blocked Sonar restoration](security_analysis.md) after owner
  project/access setup, using a hardened new workflow and actual server-side
  findings, coverage and quality-gate evidence. CodeQL restoration is independent.

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
- Extend the [Python batch binding](PYTHON-GUIDE.md) only for concrete needs;
  custom units, broader platforms/free-threaded Python and public wheel publication
  are not yet supported. Preserve explicit runtime checks, copies and lost-guarantee
  documentation. [Host observations](python/2026-11-03/README.md) are not native parity.
- Satisfy [release-policy gates](RELEASING.md) before any separately authorized
  publication: exact artifact versions/signoff and registry/ownership rechecks
  remain future work. [Readiness tooling](package_readiness.md) now implements
  embedded source/build provenance and narrow Linux baseline/container gates;
  these are not publication approval or universal-platform guarantees.
- Ground further lab workflows in real licensed data/calibration when available;
  the [current lab walkthrough](python_lab_workflow.md) is synthetic offline telemetry.

Current behavior is specified in [requirements](requirements/requirements.md).
Completed work belongs in the [changelog](../CHANGELOG.md), not a stale checklist here.

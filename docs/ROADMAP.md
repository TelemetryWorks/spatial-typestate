# Remaining work

These are proposals, not implemented guarantees or promises of a release date.

- Preserve the restored [security analysis](security_analysis.md) and review new
  findings. The [historical triage](evals/2026-11-07-sonar-main-triage.md) and
  [owner-approved dispositions](evals/2026-11-08-sonar-dispositions.md) distinguish
  a sanitised filter finding from two accepted operator risks. Those accepted
  risks remain explicit. No broad rule, gate, threshold or exclusion change follows.

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
  custom units and broader platforms/free-threaded Python are not yet supported.
  Published 0.1.0 wheels have the narrow [documented scope](PYTHON-GUIDE.md).
  Preserve explicit runtime checks, copies and lost-guarantee documentation. [Host observations](python/2026-11-03/README.md) are not native parity.
- Complete **Trusted Publishing migration for both registries**, under the owner
  policy of 2026-11-13: future uploads use OIDC from a reviewed GitHub Actions
  workflow, never a stored registry token or local publisher. This is setup work
  still to do, not evidence that a publisher/environment has been configured.
  - **Agent steps (future reviewed PRs):** prepare a tag-only Rust release workflow
    with separate verification and `crates-io` publishing jobs; bind `vX.Y.Z` to
    the manifest version and reviewed source on main, pin
    `rust-lang/crates-io-auth-action` by full SHA, and grant OIDC only to the
    publishing job. Prepare a separate qualified-artifact PyPI publisher bound to
    `pypi`, with per-file PEP 740 attestations and public verification. Preserve
    this crate's MSRV/pin and independent Rust/Python versions; do not copy the
    example's toolchain or feature matrix. Build the independent approver checklist
    and immutable-published-text review into release preparation.
  - **Owner steps (settings, separately authorized):** create protected `crates-io`
    and `pypi` environments with explicit owner approval and no administrator
    bypass; restrict Rust deployment to tags `v*`, no branches. Configure the exact
    registry Trusted Publisher identities. Enable crates.io **Trusted Publishing
    only**, delete any stored `CARGO_REGISTRY_TOKEN` and `PYPI_API_TOKEN` secrets,
    and revoke superseded long-lived credentials at their issuers. Deletion is not
    revocation; first inventory secret names without reading values. No fallback
    upload is allowed while setup or verification is incomplete.
  - Follow the detailed [owner/agent setup and approver gates](RELEASING.md#trusted-publishing-migration-owner-and-agent-steps).
    The [irig106-types reference](https://github.com/TelemetryWorks/irig106-types/blob/fef4233b1e4deca170e881fc34438555b09e15d8/docs/RELEASING.md)
    and its [reviewed workflow](https://github.com/TelemetryWorks/irig106-types/blob/fef4233b1e4deca170e881fc34438555b09e15d8/.github/workflows/release.yml)
    are the model, not a drop-in publisher. Its 0.1.0 publication on 2026-11-15 has
    [registry `trustpub_data`](https://crates.io/api/v1/crates/irig106-types/0.1.0).
    Spatial-typestate Rust 0.1.0 used a stored Cargo credential; Python 0.1.0 used a
    token without public attestations. Those historical bytes/tags stay unchanged.
    [Readiness tooling](package_readiness.md) and exact artifact signoff remain
    required; neither grants publication approval or universal-platform support.

- Start a **Verus feasibility study**, before any proof-code or CI implementation.
  [Verus](https://github.com/verus-lang/verus) verifies a subset of Rust against
  explicit specifications; using it does not make this crate formally verified.
  Produce a bounded go/no-go report mapping current requirements to candidate
  lemmas, unsupported operations, assumptions, maintenance cost and review needs.

  | Candidate property | Study scope and boundary |
  | --- | --- |
  | Frame-tag/type-state soundness | Check that modeled point/vector mapping and composition preserve their source/target/unit parameters and reject mismatches. Keep existing Rust compiler-rejection tests. Rust's type checker remains trusted; this is not a proof of Rust soundness, physical frame identity or caller calibration. |
  | Quaternion normalization/invariants | Model nonzero-input scaling and ideal unit length over exact reals; rational models can cover algebra on already-unit rational quaternions, not general square-root normalization. Separately assess finite `f64`, subnormal/signed-zero behavior, rounding bounds, native sqrt and the eight-step no_std helper. Do not assert exact norm one for floating-point results. |
  | Composition/associativity and inverse | Prove affine algebra in exact rational/real models with proper-rotation/orthogonality premises. `f64` composition is not generally associative or bit-identical; tolerance-accepted inverses are approximate. Exact-model results need a separately justified refinement/error argument before saying anything about executable math. |
  | Unit consistency | Model preservation of explicit length/vector tags and translation-only scaling. Marker/scale metadata remain caller-trusted; neither type checking nor a model verifies actual dimensions/calibration or all-extreme-ratio conversion. |
  | Absence of panics/overflow | Start with fixed-array index bounds and bounded integer control arithmetic. Integer overflow proofs do not establish absence of `f64` infinity/NaN: checked math intentionally returns errors on some finite inputs. Any later finite-output/error-order proof must cover the real guards and participating-entry rules. |

  **Compatibility investigation:** the [feature matrix][verus-features] and
  [trait contracts][verus-traits] support generic types/user traits, but const
  functions/constants, some standard traits and mixed verified/unverified crates
  remain partial; `Debug` is listed unsupported. Inventory this crate's
  `PhantomData`, marker bounds, manual value traits, arrays and std/no_std paths
  against one pinned Verus release, not an assumption that existing source verifies.

  **Floating-point limit:** support is partial, not nonexistent. The inspected
  [float regression tests][verus-floats] include bit/IEEE-style examples and casts,
  but also explicitly failing default `f64` determinism proofs and unsupported
  floating negation. Default specifications may be weaker/nondeterministic;
  stronger prover modes and equality notions need separate investigation. No
  end-to-end proof of this crate's sqrt, rounding, bit identity, overflow handling
  or numerical accuracy has been demonstrated. Use exact models for algebra first;
  list every assumed library contract/refinement gap rather than treating a model
  proof as a proof of production `f64` execution.

  **Placement and CI plan:** prefer a standalone, non-published
  `verification/verus/` proof crate/specification model with its own dependency
  lock and tooling. It must not add runtime dependencies or enter crate/wheel
  payloads. A later alternative is reviewed `cfg(verus_only)` annotations, only
  after checking erasure, warning-denial, packaging and std/no_std compatibility;
  no production cfg/feature is approved now. A separate read-only Linux x86_64 CI
  job could run a checksum-pinned Verus release and matching rustc/Z3, record all
  versions, resource limits, verified items and errors, and fail on proof errors.
  It must not replace existing tests or change MSRV 1.85, development pin 1.91.1
  or runtime/UI compiler 1.99.0. [Install][verus-install]/[build][verus-build]
  requirements vary by release: the inspected upstream toolchain is 1.99.1 and
  build guide names Z3 4.16.0, not requirements imposed on crate consumers.
  Platform/package availability and solver performance remain untested here.

  **First small target, if the study is approved:** a three-coordinate,
  frame/unit-tagged affine-identity kernel over bounded integers, with exact spec
  coordinates, index bounds and no-overflow obligations; deliberately exclude
  normalization/inverse/float math. Record correspondence to current API and
  detect drift against the production source. A copied model proves only itself.
  Review all [trusted assumptions][verus-tcb] (`assume`, external bodies, toolchain
  and solver) and preserve adversarial tests; do not assume the property to prove it.
  The [integer-overflow tutorial][verus-overflow] and [Cargo/project guide][verus-cargo]
  provide starting points. Deliver a source-linked feasibility report and an
  explicit decision before installing tools, adding a proof crate, CI or public
  verification claims. No Verus run or proof is claimed by this roadmap entry.

- Ground further lab workflows in real licensed data/calibration when available;
  the [current lab walkthrough](python_lab_workflow.md) is synthetic offline telemetry.

Current behavior is specified in [requirements](requirements/requirements.md).
Completed work belongs in the [changelog](../CHANGELOG.md), not a stale checklist here.

Verus sources actually read for this proposal on 2026-11-15, pinned to upstream
`530783b409bdf326aa190212b3a9fc2d6048215e` (documentation may lag implementation;
recheck against the release chosen for the study):

[verus-features]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/features.md
[verus-traits]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/traits.md
[verus-floats]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/rust_verify_test/tests/float.rs
[verus-install]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/INSTALL.md
[verus-build]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/BUILD.md
[verus-tcb]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/tcb.md
[verus-overflow]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/overflow.md
[verus-cargo]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/cargo_verus.md

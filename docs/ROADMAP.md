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
  - **Owner decision 2026-11-15 (superseding earlier dual-tag choices):** ONE
    `vX.Y.Z` tag releases both packages from the same verified commit, with Rust,
    Python/native versions in lockstep and ONE combined changelog section. Future
    `rust-vX.Y.Z` / `python-vX.Y.Z` routes are retired; historical `rust-v0.1.0`
    and `python-v0.1.0` stay untouched. Both protected `crates-io` and `pypi`
    environments require owner approval, no admin bypass and Tag rule `v*` (no
    branch rule), bound to the corresponding Trusted Publisher.
  - **Agent steps (future reviewed PRs):** prepare one coordinated tag-only release
    workflow verifying both artifact sets before uploads; bind `vX.Y.Z` to all
    version metadata and the same reviewed source on main, pin
    `rust-lang/crates-io-auth-action` by full SHA, and grant OIDC only to the
    registry publish jobs. Prepare its qualified-artifact PyPI job bound to `pypi`,
    with per-file PEP 740 attestations and public verification. Preserve this
    crate's MSRV/pin; do not copy the example's toolchain or feature matrix. Build the independent approver checklist
    and immutable-published-text review into release preparation.
  - **Owner steps (settings, separately authorized):** create protected `crates-io`
    and `pypi` environments with explicit owner approval and no administrator
    bypass; restrict BOTH deployments to shared tags `v*`, no branches. Configure
    the exact registry Trusted Publisher identities. Enable crates.io **Trusted
    Publishing only**, delete any stored `CARGO_REGISTRY_TOKEN` and `PYPI_API_TOKEN` secrets,
    and revoke superseded long-lived credentials at their issuers. Deletion is not
    revocation; first inventory secret names without reading values. No fallback
    upload is allowed while setup or verification is incomplete.
  - **Proposals for review:** classify changes against each last publication and
    choose a jointly unused shared version (e.g. 0.1.1 for compatible fixes or 0.2.0
    if either surface breaks; owner decides). Verify both, then crates.io, then
    PyPI. If one succeeds and the other fails, stop, record the incomplete release
    and inspect public state; no blind rerun, overwritten version or moved tag.
    Owner-authorized recovery of only missing exact bytes, or a new coordinated
    release, needs separate review. See [migration and recovery proposals](RELEASING.md#proposal-coordinated-ordering-and-partial-release-handling).
  - Follow the detailed [owner/agent setup and approver gates](RELEASING.md#trusted-publishing-migration-owner-and-agent-steps).
    The [irig106-types reference](https://github.com/TelemetryWorks/irig106-types/blob/fef4233b1e4deca170e881fc34438555b09e15d8/docs/RELEASING.md)
    and its [reviewed workflow](https://github.com/TelemetryWorks/irig106-types/blob/fef4233b1e4deca170e881fc34438555b09e15d8/.github/workflows/release.yml)
    are the model, not a drop-in publisher. Its 0.1.0 publication on 2026-11-15 has
    [registry `trustpub_data`](https://crates.io/api/v1/crates/irig106-types/0.1.0).
    Spatial-typestate Rust 0.1.0 used a stored Cargo credential; Python 0.1.0 used a
    token without public attestations. Those historical bytes/tags stay unchanged.
    [Readiness tooling](package_readiness.md) and exact artifact signoff remain
    required; neither grants publication approval or universal-platform support.

- Start a **layered Rust-core verification feasibility study** (owner decisions
  2026-11-15), methodically and incrementally, before implementing harnesses or
  verification CI. Scope is the Rust core only: PyO3 bindings retain tests, packaging checks
  and the future-release attestation policy, but are **not formally verified** by
  this plan. Deliver a source-linked comparison, explicit assumptions, costs and
  go/no-go decisions; no tool run or verified property is claimed here.

  | Layer | Proposed role and limits to evaluate |
  | --- | --- |
  | Kani on real Rust `f64` code | Check panic/index/integer-overflow safety, NaN/Inf/error handling and bounded normalization/composition/inverse properties by calling actual core functions. State input domains, loop/unwind bounds, reachable branches and completeness checks. Floating overflow is not a Rust panic: finite inputs can legitimately return `Err`; prove the checked behavior, not universal success. |
  | Verus on EXACT integer/rational models | Seek unbounded proofs of frame/type-state preservation, affine composition associativity/inverse under exact rigidity premises, and unit consistency. Rational models do not cover arbitrary square-root normalization; ideal-real extensions would need explicit assumptions. Compiler rejection tests remain, and physical frames/calibration/custom scale metadata remain caller-trusted. |
  | Creusot versus Verus | Compare the same small exact-model contracts, trait/generic/array support, source correspondence, annotation burden, proof maintenance, solver cost and trust boundaries. Creusot translates Rust into Why3/Coma; evaluate its path to Why3 float theories rather than assuming that connection already proves this crate's `f64` semantics. |
  | Miri, conditional on unsafe | Inspection of current `src/` found no unsafe blocks/functions/impls; `src/lib.rs` has `#![deny(unsafe_code)]`. No unsafe-specific Miri harness is currently needed. Recheck if unsafe is introduced and evaluate Miri then; it detects UB on executions, not universal soundness or numerical accuracy. This check excludes the separate PyO3/native binding. |
  | cargo-mutants | Measure test strength on core code: retain killed/missed, unviable/equivalent candidates and timeouts with reviewed explanations. Improve meaningful tests where mutations survive. Mutation results are neither formal correctness proofs nor a target score to achieve through exclusions. |

  **Kani evidence and caveats:** the [Kani paper, arXiv:2607.01504][kani-paper]
  describes MIR-to-CBMC checking and the distinction between bounded exploration
  and contract-based reasoning. For this layer start with explicitly bounded
  harnesses, not an unbounded claim. The [current limitations][kani-features]
  state that `sqrt` and trig functions are over-approximated: a counterexample
  can be spurious, and precision proofs may be infeasible. Do not replace them
  with an unjustifiably precise stub or assume away failure. Separate std native
  sqrt from the no_std eight-step helper; record every model/contract assumption.
  The core currently uses no trig, but its modeling limit matters to tool choice.

  **Verus compatibility and float boundary:** the [feature page][verus-features]
  lists floating point as **partially supported**, with partial support also for
  const functions/constants and some library traits; inspect this crate's
  `PhantomData`, generic marker bounds, manual value traits and arrays. The
  [float tests][verus-floats] show that support/equality/prover modes vary; do not
  claim production float semantics from the exact-model layer. The sign-of-zero
  spec-equality versus Rust pattern-matching problem in [issue #3194][verus-zero]
  is a concrete caution: it is **closed** as checked on 2026-11-15, by
  [#3195 disabling the affected float-pattern equality path][verus-zero-fix],
  rather than an open issue. Confirm the selected verifier release contains that
  fix and retest relevant semantics. Exact associativity/inverse lemmas do not
  imply `f64` associativity, bit identity or exact inverses of tolerance-accepted
  inputs. Audit [assumptions/external bodies][verus-tcb] instead of assuming the
  intended property. [Trait contracts][verus-traits] are a study aid, not proof
  that the existing crate can be verified without adaptation.

  **Proven worst-case rounding-error bounds are a required study objective, in
  addition to safety and bounded properties.** Evaluate [Gappa][gappa-guide],
  [FPTaylor's rounding/domain models and proof support][fptaylor-reference],
  [Daisy][daisy] and [Why3 IEEE-float theories][why3-floats] via the candidate
  Creusot pipeline. Compare which can produce replayable/checkable proofs or
  certificates, and document the trusted checker/solver stack. Rigorous numerical
  estimates, test tolerances and a printed bound alone are not a checked proof
  about the shipped Rust code. No automated Rust-to-these-tools bridge is assumed.

  For normalization (including scaled norm and both sqrt paths), transform rows,
  composition and inverse, propose explicit input domains and absolute, relative
  or ULP error metrics. Near zero a relative bound may be undefined; inverse
  error depends on conditioning/magnitude and rigidity tolerance. Account for
  branch boundaries, intermediate overflow, subnormals, signed zero, NaN/Inf and
  underflow; classify rejected inputs separately. Prove approximation/truncation
  error of the Newton helper separately from rounding error. Do not promise a
  single useful bound over every input or chain length. Bounded, straight-line
  domains may be feasible; full-range normalization/inverse and platform sqrt
  behavior remain open feasibility questions. The study must say which bounds
  are proved, conditional, infeasible or still unproved.

  Close the **model-to-compiled-code gap** for each claimed bound: identify the
  exact source/MIR expressions, operation/evaluation order, branches/constants,
  binary64 rounding mode, compiler/target/flags, FMA contraction and sqrt/library
  contracts. Explain how models are extracted or independently matched to that
  code, how drift is detected in CI, and which compiler/backend assumptions
  remain trusted. An exact/rational lemma or manually copied expression proves
  only its model until this correspondence is justified; numerical oracles and
  regression tests complement but cannot replace that argument.

  **Study outputs, not decisions made now:** propose where specs/harnesses live
  (for example a separate non-published `verification/` crate/model tree versus
  reviewed `cfg(kani)`/`cfg(verus_only)` annotations), isolation/erasure and source
  drift checks, and a first small target with acceptance criteria and resource
  bounds. Possible starting points include real-code finite/error guards or a
  small exact frame/unit-tagged identity lemma; select only after comparing costs
  and correspondence gaps. Preserve the dependency-free runtime graph, warning
  policy and release payloads. Evaluate Creusot's [guide][creusot-guide] and
  [Why3 translation][creusot-architecture] against Verus, including unsupported
  operations and all trusted specifications; do not decide the winner in advance.

  **CI rollout:** all future verification runs in CI with separately pinned
  verifier/solver/compiler toolchains and retained versions, source identity,
  domains/bounds, proof results and timeouts. Do not change crate MSRV **1.85**,
  development pin **1.91.1** or existing runtime/UI compiler **1.99.0**. Initially
  advisory/non-blocking, with failures and incomplete/unsupported results visible;
  never label a timeout or skipped proof verified. Once each harness has stable,
  reviewed semantics, reproducibility and acceptable cost, make that harness a
  required check through a separately reviewed workflow/settings change. Existing
  tests and release-attestation gates stay in force. No workflow, tool installation,
  new required check or public verification claim is authorized by this docs item.

- Ground further lab workflows in real licensed data/calibration when available;
  the [current lab walkthrough](python_lab_workflow.md) is synthetic offline telemetry.

Current behavior is specified in [requirements](requirements/requirements.md).
Completed work belongs in the [changelog](../CHANGELOG.md), not a stale checklist here.

Primary sources actually read for this proposal on 2026-11-15. Verus files are
pinned to `530783b409bdf326aa190212b3a9fc2d6048215e`; other repository sources are
pinned below. Recheck documentation, open/closed issues, compiler and solver
support against the releases selected by the study.

[verus-features]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/features.md
[verus-traits]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/traits.md
[verus-floats]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/rust_verify_test/tests/float.rs
[verus-tcb]: https://github.com/verus-lang/verus/blob/530783b409bdf326aa190212b3a9fc2d6048215e/source/docs/guide/src/tcb.md
[verus-zero]: https://github.com/verus-lang/verus/issues/3194
[verus-zero-fix]: https://github.com/verus-lang/verus/pull/3195
[kani-paper]: https://arxiv.org/html/2607.01504v1
[kani-features]: https://github.com/model-checking/kani/blob/0aac16ef62da9e9d5645782d458593e5d78143ba/docs/src/rust-feature-support.md#floating-point-operations
[creusot-guide]: https://guide.creusot.rs/
[creusot-architecture]: https://github.com/creusot-rs/creusot/blob/a45192da0a9e210bbb6beb918317e339970c2cf5/ARCHITECTURE.md
[gappa-guide]: https://gappa.gitlabpages.inria.fr/gappa/index.html
[fptaylor-reference]: https://github.com/soarlab/FPTaylor/blob/b5a77cae348400f21f83512210d9f43c4bffb381/REFERENCE.md
[daisy]: https://github.com/malyzajko/daisy/blob/6a6f47abdd231d3009444e9e1b8ce9febc28c27e/README.md
[why3-floats]: https://www.why3.org/stdlib/ieee_float.html

Dynamic-checking/test-strength references read: [Miri's execution/UB limits](https://github.com/rust-lang/miri#readme)
and [cargo-mutants overview](https://mutants.rs/).

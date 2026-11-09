# Changelog

## [Unreleased]

Candidate selection (2026-11-08, step 1 only): Rust 0.1.0 replaces unpublished
0.0.2 metadata; Python/native remain the unpublished 0.1.0 first-release candidate.
This metadata selection alone does not authorize packages, tags, uploads or
artifact signoff. The
[published 0.0.1 migration](docs/migration-0.0.1-to-0.1.0.md) is the consumer guide;
the development history below also includes changes between unpublished commits.

### Packaging

- Require hosted PyPI OIDC Trusted Publishing and verified per-file PEP 740 publish
  attestations for every future wheel and sdist, with no token/local-upload
  fallback. The token-uploaded 0.1.0 release remains historical and unattested;
  the disabled one-time publisher is retired from future reuse.

- Omit agent instructions, development Cargo/toolchain controls, local tooling,
  the repository-only roadmap pointer and unused logo from the Rust crate archive.
  Tests, benches and examples remain packaged; repository files and runtime
  behavior are unchanged. This manifest change supersedes the initial candidate
  source/artifact selection; qualification must use the replacement reviewed commit.

### Fixed

- Validate the main-only Sonar task `branch` field against the expected branch,
  while rejecting it in PR task metadata.
- Run installed-wheel container tests from a fresh private temporary directory,
  with isolated Python startup, instead of shared `/tmp`.
- Reject option-like Criterion filters before preparation or execution. Normal
  regex filters, including `^amortization`, remain unchanged.

### Changed

- Protect `main` with required PRs, strict app-bound Rust/Python/CodeQL/Sonar
  checks, administrator enforcement, and force-push/deletion blocks. Approval
  count remains zero for the sole maintainer; fork/Dependabot Sonar skips are
  not analysis evidence. See the [policy audit](docs/evals/2026-11-08-main-protection.md).

- Split packaging validation and benchmark registration into smaller ordered
  helpers; share repeated artifact names and tighten the endian exception test.
  Numeric APIs, CLI contracts, validation order and measured Rust expressions
  are unchanged. See the [maintainability audit](docs/evals/2026-11-08-maintainability.md)
  for per-issue server verification and the limits of equivalence evidence.
  All 24 original keys were verified FIXED on main `c047c12` (2026-11-08),
  with no replacement keys and the three security dispositions unchanged.

- Record the owner's three issue-specific Sonar decisions with public audit
  comments: false positive for the already-validated Criterion filter, and
  accepted trusted-operator CSV input/benchmark output risks. Numeric APIs and
  CLI behavior are unchanged; maintainability work is recorded separately above.

- Establish the reviewed Sonar new-code-since-deployment baseline using a fixed
  date before the first main analysis. This evaluates subsequent changes; at
  setup, three older vulnerability findings and 24 smells were still OPEN.
  Their later dispositions/fixes are recorded separately. The baseline setup
  was not an overall-clean claim or a rule/threshold/issue-status change.

- Add a pinned Sonar workflow with isolated token-free reports and precedence
  probe, hosted-runner Rust-tool checks and a credential-bearing official scanner
  step. Sonar restoration requires actual server/import/gate evidence; configured
  identifiers alone are not a passing analysis. No runtime/API change.

- Restore CodeQL for Rust, Python and Actions with pinned actions, extended
  security queries and retained extraction evidence. Remove the disabled unsafe
  Sonar workflow and its duplicate SARIF exporter. Sonar findings belong in Sonar,
  not GitHub Security. See [security status and plan](docs/security_analysis.md).

- Python build interface now uses the private PEP 517 backend for readiness
  records. Direct maturin CLI bypasses those gates; editable installs explicitly
  reject with installed-development-wheel/rebuild guidance. Numeric APIs unchanged.

- Corrected current-API README installation to a validated source commit;
  repository 0.0.2 is not available on crates.io at the recorded check date.

- **Breaking:** Point3<F,L:LengthUnit>, Transform<From,To,L:LengthUnit>, and
  Vector3<F,U:Unit> require explicit unit parameters, without defaults. Choose
  actual units for former raw values. Translation/point/composition lengths
  match; inverse retains L, quaternion is dimensionless, and vector mapping
  preserves any U independently of translation. No implicit conversion is added.
- **Breaking:** SpatialError adds InvalidUnitScale and
  UnrepresentableUnitConversion. Add downstream exhaustive match arms; NonFinite
  still reports non-finite numeric inputs/results. See [unit decisions](docs/units.md)
  for metadata-first error policy and raw/custom-declaration limitations.

- **Breaking from published 0.0.1:** `Transform::apply_point` now returns
  `Result<_, SpatialError>` under its existing name. Add `?` or explicit error
  handling. `apply_vector` and `then` also return Result, but they are additions
  relative to 0.0.1; changing their earlier unchecked development forms is
  unpublished history. No parallel unchecked/`try_` alternatives are introduced.
  Participating non-finite inputs and computed overflow/NaN return
  `NonFinite`. Raw bottom rows remain ignored; vector application also ignores
  translation. Finiteness checks do not certify rigidity or calibration.
- Sequential application and composition validate different intermediates and
  can return errors at different stages. Evaluation order is retained without
  compensated arithmetic or clamping. The checks add work to every operation;
  no benchmark timing or zero-overhead claim is made.
- **Breaking:** UnitQuat components are private. Replace q.x/q.y/q.z/q.w reads
  with const x()/y()/z()/w() getters. Replace mutation or removed new_unchecked
  calls with try_from_components and handle its Result, or use const identity().
- **Breaking:** SpatialError adds NonRigidTransform. Add a match arm to downstream
  exhaustive matches. It reports finite raw matrices that fail checked inversion.
- Point3/Vector3/Transform/UnitQuat implement Copy/Clone/Debug/PartialEq without
  marker trait bounds. Debug retains phantom frame information; quaternion
  equality remains component equality, not q/-q rotation equivalence.

### Added

- Private stdlib PEP 517 backend for source-only sdist identity and wheel build
  provenance/resources, frozen input verification, locked dependency notices,
  compiler/std notices and full RECORD/package checks. Path-remapped binding
  builds preserve checkout warning denial; no native/core API change.
- Pinned manylinux_2_28 x86_64 build and glibc 2.28/2.36 container runtime gates,
  ELF requirement/path negative tests and external dry-run artifact hash inventory.
  No version, tag, registry upload or universal Linux compatibility claim.

- Executable synthetic 100 Hz Python sensor-aircraft-world lab analysis and
  installed-wheel tests: explicit feet/meters, runtime frame identities,
  independent all-sample oracle, read-only export and actionable atomic errors.
- Release/versioning policy with verified registry baseline, independent Rust/
  Python versions, migration classification and future artifact provenance/
  publication gates. No version, tag, upload or additional platform support.

- Separate unreleased CPython batch package under python/, with isolated PyO3
  dependencies/lockfile and maturin build tooling. Frozen runtime frame identities,
  closed meter/foot/dimensionless tags, Rust-owned points/vectors, core-backed
  checked quaternion/transform/conversion operations, atomic first-index errors
  and cached immutable bytes views. No Python per-row numeric loop objects or
  runtime NumPy dependency. [Guide](docs/PYTHON-GUIDE.md) records copies, early
  import errors, lost compile-time/generic/lifetime guarantees and concurrency
  limits. Linux/Windows wheel and source-build checks and bounded host evidence
  are separate from unchanged core math/API/normal dependencies. No release.

- Isolated borrowed-validation prototype and matched caller-local hoisting
  controls, with point/vector-specific finite scopes, private immutable borrows,
  lifetime/type rejection and bit/error tests. Separate repeatable host evidence
  and [design decisions](docs/borrowed_validation.md) retain uncertainty and pending
  prepare-time-error/batch choices. No production public API, scalar rewrite,
  six-step normalization or dependency change is promoted.

- Reusable bounded Criterion host characterization for checked operations,
  unit conversions, std/actual no-std quaternion normalization, errors/extremes,
  dependent and batched workflows. Reproducible dated estimates, intervals,
  raw samples, source snapshots and codegen controls document profile dependence,
  retained variance/spikes and rejected hypotheses in [the report](docs/performance.md).
  No production optimization, new API, universal speed/timing claim or dependency
  is introduced. Validation amortization remains a bounded future investigation.

- Meters/international Feet and Dimensionless tags, open custom markers with
  opt-in length-only LinearLengthUnit metadata, and shared checked convert_to
  for Quantity/Point3/length Vector3/Transform. Transform scales translation
  only, preserves linear bits and canonicalizes bottom. Positive finite factor
  policy permits rounding/component underflow but rejects zero/infinite ratios,
  invalid scales and non-finite inputs/output; finite same-unit components keep
  bits. No extreme-ratio rescue, exact roundtrip, dimensional algebra, angles,
  offset units, registry, calibration proof or dependency is introduced.
- Meter/foot equivalent sensor workflow, raw/invalid/extreme conversion tests,
  finite-bit and bounded properties, length mismatch UI and paired incompatible
  conversion doctests. Quantity value traits now support bare custom markers.

- Checked rotation/target-translation construction, typed then composition,
  translation-free apply_vector, and checked try_inverse. Existing raw matrix
  storage/construction remain available; apply_point is checked as described above.
- A complete sensor-aircraft-world example with analytic expected coordinates,
  composition, inverse, and vector verification, also using a no-std library.
- Hand-written Display/core Error, without allocation or dynamic dispatch in math.
- Numbered implemented requirements/evidence and actual design/frame/math docs;
  populated contributor guidance and a single canonical remaining-work roadmap.
- Direct read-only Linux/Windows runtime, lint/docs/release, dependency graph,
  MSRV/pin library, and thumb/MUSL compile-only CI gates. Actions are SHA-pinned;
  redundant old Clippy/Rustfmt workflows are consolidated. Service configs unchanged.

### Fixed

- Extreme quaternion normalization with max-component scaling, including finite
  MAX/subnormals. Reject any non-finite component and signed all-zero inputs.
  Approximate unit length and possible relative underflow are documented.
- No-std quaternion norm via a private eight-step bounded Newton approximation,
  with native sqrt retained for std, dense/native-reference and actual no-std tests.
  No correctly-rounded equivalence or timing guarantee is claimed.
- Matrix docs now specify row storage, column vectors, target-frame translation,
  ignored raw bottom row, checked versus unchecked behavior, and inverse tolerance.
- Translation compatibility assertions now check exact per-axis sums, including
  expected signed overflow; deterministic and sampled regressions were added.
- Existing unused imports, formatting/lint findings, and broken rustdoc links;
  reviewed compile-fail baselines and explicit marker/unit/frame regressions.
- Removed-constructor rejection uses a paired checked-success/compile-fail
  doctest rather than an E0599 wording snapshot, preserving the same contract
  on the pinned compiler and 1.99. Stable rustdoc verifies failure, not error code.

### Removed

- **Breaking:** unused nalgebra/glam features and optional dependency declarations
  (including implicit nalgebra_dep/glam_dep features). Remove those feature names
  from caller manifests/commands; use std or disable defaults for no-std. No
  backend runtime implementation existed to replace, and no backend was integrated.
- Unused direct thiserror/num-traits/typenum dependencies. Every runtime feature
  graph is now empty; dev tools still bring transitive num-traits. The lockfile
  only prunes unused packages/root edges; retained versions were not upgraded.
  No dependency or libm was added.

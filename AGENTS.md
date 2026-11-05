# Spatial Typestate

Canonical shared repository guidance. CLAUDE.md is a thin wrapper. Workspace
coordinator roles belong in the parent workspace, not this repository file.

This evolving Rust library provides frame-tagged points/vectors/quaternions and
a complete numeric rigid-transform workflow with explicit length/vector unit tags.
Physical calibration, verified custom unit declarations, dimensional algebra,
certification and timing guarantees are not implied.
Read [requirements/evidence](docs/requirements/requirements.md) before changing
contracts and [math conventions](docs/math_conventions.md) before changing math.

## Layout

- src/: small fixed-size, dependency-free library; lib.rs re-exports its API.
- python/: separate CPython batch facade/native crate, own PyO3 dependency lock;
  Python runtime/packaging contracts are in docs/PYTHON-GUIDE.md. No core runtime
  dependency is added. Test-only NumPy is isolated from wheel metadata.
- tests/: marker traits, independent math oracles, properties, error and fuzz-helper checks.
- tests/ui/: reviewed frame/unit/private-field compiler-rejection fixtures.
- examples/sensor_alignment.rs: working sensor-aircraft-world workflow.
- Two other examples remain placeholders. benches/spatial.rs provides Criterion
  host characterization; support experiments are not library APIs/optimizations.
- docs/: requirements/evidence, design, frames, coordinate/math/safety notes.
- docs/performance.md and dated data: reproducible host findings, raw samples,
  uncertainty, rejected candidates and bounded future validation-amortization work.
- docs/borrowed_validation.md: isolated borrowed/caller-local prototype, measurements
  and pending API/error/batch decisions; no production API promotion.
- docs/ROADMAP.md: canonical remaining work; root ROADMAP.md points there.
- .github/workflows/ci.yml: direct quality gates; CodeQL/Sonar remain separate.
- Cargo.toml/Cargo.lock: no normal dependencies, dev-only tools; .cargo/config.toml
  denies warnings. rust-toolchain.toml pins development Rust 1.91.1.

## Commands

Edition 2024, declared MSRV 1.85. The pin, MSRV, and explicit runtime/UI test
compiler 1.99.0 are separate policies. Current installed Windows toolchains
1.99.0, 1.91.1 and 1.85.0 are available; do not install/complete tools or targets
implicitly. Use explicit installed selectors. Local target installation needs
permission; the CI runner's explicit thumb/MUSL target install is authorized.

```powershell
$env:CARGO_BUILD_JOBS = '2'
cargo +1.99.0-x86_64-pc-windows-msvc fetch --locked
cargo +1.99.0-x86_64-pc-windows-msvc fmt --all -- --check
cargo +1.99.0-x86_64-pc-windows-msvc test --locked --jobs 2 -- --test-threads=2
cargo +1.99.0-x86_64-pc-windows-msvc test --locked --jobs 2 --no-default-features --features no_std -- --test-threads=2
cargo +1.99.0-x86_64-pc-windows-msvc test --locked --jobs 2 --all-features -- --test-threads=2
cargo +1.99.0-x86_64-pc-windows-msvc clippy --locked --all-targets --all-features --jobs 2 -- -D warnings
cargo +1.99.0-x86_64-pc-windows-msvc clippy --locked --all-targets --no-default-features --features no_std --jobs 2 -- -D warnings
$env:RUSTDOCFLAGS = '-D warnings'
cargo +1.99.0-x86_64-pc-windows-msvc doc --locked --no-deps --all-features --jobs 2
cargo +1.99.0-x86_64-pc-windows-msvc doc --locked --no-deps --no-default-features --features no_std --jobs 2
cargo +1.99.0-x86_64-pc-windows-msvc run --locked --jobs 2 --example sensor_alignment
cargo +1.99.0-x86_64-pc-windows-msvc run --locked --jobs 2 --no-default-features --features no_std --example sensor_alignment
cargo +1.99.0-x86_64-pc-windows-msvc tree --locked --all-features --edges normal --target all
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for compatibility/release/CI commands.
All-features includes std; it is not a substitute for disabling defaults.
The only features are std (default) and no_std (marker). Removed backend names
must not appear as active command suggestions. Runtime graphs are dependency-free;
dev dependencies do not alter that policy. Do not add dependencies/change pin or
MSRV without task authorization. No local system/target installations by inference.

## Architecture

Frame labels are PhantomData, not stored values. Manual value traits preserve
bare-marker usability and same-frame constraints. Debug retains phantom identity.
Point3<F,L:LengthUnit> and Transform<From,To,L:LengthUnit> require explicit L;
Vector3<F,U:Unit> requires U. No default unit exists. Translation, point mapping
and composition share L; inverse retains it. Rotation is dimensionless; vector
mapping preserves any U independently of translation L. Quantity shares checked
linear-length conversion; raw public components and scalar arithmetic remain
unvalidated. Meters/Feet and Dimensionless are first tags; open custom markers
need no derives. LinearLengthUnit is opt-in trusted scale metadata, not a proof
of dimension/calibration. See [unit decisions](docs/units.md) for all limitations.
Conversion validates metadata then a positive finite factor then finite values/
results. InvalidUnitScale and UnrepresentableUnitConversion are distinct errors.
Transform conversion scales only translation, preserves R bits, checks first
three rows, ignores/canonicalizes bottom. Finite same-unit component bits survive;
rounding/underflow are allowed, overflow errors, extreme-ratio rescue is excluded.

UnitQuat uses private Hamilton (x,y,z,w) components, checked max-component
normalization, const identity/getters, and component equality (q != -q).
No public unchecked escape exists. Finite nonzero inputs normalize, including
subnormals/MAX; tiny relative components may round to signed zero. Native sqrt
is retained under std; the no-std helper takes eight fixed Newton steps only
on squared norms in [1,4], with documented convergence/rounding limits.

Transform<From, To, Meters> maps p_To=R*p_From+t_To. The checked constructor uses a
UnitQuat<To> and Vector3<To,L> target translation; the quaternion does not bind From, so the
caller asserts the physical relation. Raw public matrices remain unvalidated.
Storage is row-major/column-vector, with translation in the last column.
Application/composition ignore raw bottom rows; then means next(first(p)), emits
canonical bottom row, and returns Result. apply_point/apply_vector also return
Result under their existing names, rejecting non-finite participating inputs and
results. Raw bottom rows and vector translations remain ignored. This validates
finiteness, not rigidity; no parallel unchecked/try_ operation APIs are added.
Vectors omit translation. try_inverse
validates finiteness, affine row, orthonormality and proper determinant at
absolute 1e-10, returning NonRigidTransform or NonFinite as appropriate. Accepted
near-rigid input implies magnitude/chain-dependent error, not exact roundtrips.

SpatialError is an exhaustive concrete enum with Display/core Error; adding a
variant is an API change. Formatting/boxing is caller-selected, not in successful
math. The library denies unsafe and uses stack values without allocation or I/O.

## Conventions

- Keep source/target direction explicit and preserve compile-time mismatches.
- Distinguish enforced numeric/type properties from physical meaning and goals.
- State numerical tolerances, overflow, degeneracy and unchecked boundaries.
- Do not claim certification, correctly-rounded helper sqrt, unqualified benchmark speed,
  unqualified finite-output guarantees for raw values, or arbitrary absolute roundtrip bounds.
- Reproduce bugs, add independent oracles and meaningful properties. Never bless
  a UI snapshot without reviewing the intended error (not a warning failure).
- Keep implementation small; no speculative abstractions/dependencies or unit redesign.
- Run focused checks, then full relevant suites once after code fixes; repeat
  only for changed code/new failures. One heavy job at a time, two workers.
- Check links, wrapper import, git diff --check, and final scope for docs changes.
  Report local/remote and compile/runtime evidence separately; never invent CI PASS.

## How changes land

Approved work proceeds without another permission gate. Describe unapproved
behavior/API scope before implementing it. Maintain [CHANGELOG.md](CHANGELOG.md)
under Unreleased and [remaining work](docs/ROADMAP.md) when relevant. Update the
explicit requirement-to-test table; no trace generator, hooks or release automation
is implied. Releases/version bumps/tags require an assigned task.

## Reference docs

- [README.md](README.md): user workflow, contracts, feature/migration guidance.
- [CONTRIBUTING.md](CONTRIBUTING.md): commands, actual CI, review workflow.
- [requirements](docs/requirements/requirements.md): current contracts/evidence.
- [design](docs/DESIGN.md), [frames](docs/frames.md),
  [coordinates](docs/coordinate_systems.md), [math](docs/math_conventions.md),
  [safety](docs/SAFETY.md): implemented interpretation and numerical limits.
- [units](docs/units.md): conversion decisions, migration and trust boundaries.
- [structure](docs/PROJECT_STRUCTURE.md): actual file roles.
- [roadmap](docs/ROADMAP.md): remaining proposals, not implemented guarantees.
- [performance](docs/performance.md): measured host study, reproducibility and limits.
- [borrowed prototype](docs/borrowed_validation.md): operation scopes, lifetimes, evidence and pending decisions.
- [changelog](CHANGELOG.md): final unreleased change/migration record.

## Git conventions

Treat main as protected by workflow. Use branches/PRs and merge commits; do not
assume GitHub enforces this. Check status before branch changes; preserve all
existing work. Editing approval does not imply commit/push/PR/merge/release
approval; leave work uncommitted when requested. The coordinator owns publishing
for the current task.

Pull before every push: git pull --rebase for linear unpushed commits, or
--no-rebase when unpushed history contains a merge. On rejection pull again and
retry. Resolve only clear conflicts; ask for intent when ambiguous. Never
force-push, rewrite published history, reset --hard, discard others' edits, or
delete branches you did not create. Never commit .env files/credentials.
Inspect final diff before reporting completion.

No tool attribution anywhere in repository work: no tool Co-Authored-By trailers,
generated-by footers or similar text in code, docs, commits, PRs, issues or releases.

## Python binding

Keep the core math/signatures/pin/MSRV/no_std/runtime graph independent. The
binding has its own Cargo.lock and release profile; use explicit installed 1.99
and two workers for its manifest. Read [Python guide](docs/PYTHON-GUIDE.md) and
[reviewed design](docs/python_design.md) before changing its contracts. Validate
foreign buffers/copy into private Rust Vec while attached; never access them
while detached. The caller excludes external/native writers during import.
Frozen frame identity is process-local, not name equality; no mutable relabeling.
Closed unit dispatch and existing core math stay outside/inside the Rust row loop
respectively. Point/vector ignored-entry scopes, finite errors and first-row
atomic results must remain tested. Empty mapping does not eagerly validate raw
matrix values. Cache safe immutable PyBytes after reattachment; count import
copy, export copy/zero fill and retained Vec+bytes honestly. No unsafe buffer
tricks, borrowed lifetime fabrication, prepared API promotion or Python runtime
NumPy/Arrow/pandas dependency. New binding dependencies require task approval.

Build/install/test the actual wheel; optional NumPy interop tests are dev-only.
CI tests GIL-enabled CPython 3.11/3.14 Linux/Windows and a Linux source rebuild.
Local venv/build requirements are allowed for assigned Python work, never global
system installs. See guide for exact separate-native lint/test/build commands.
No PyPI publishing/wheel release/version changes without an assigned task.

## Performance work

Use existing Criterion dev tooling with explicit installed compiler/two workers.
`cargo +1.99.0-x86_64-pc-windows-msvc bench --locked --jobs 2 --bench spatial -- --test`
smoke-checks the harness. Follow [methodology](docs/performance.md) for timed runs;
coordinate a quiet CPU/I/O window, prebuild, retain independent repeats/spikes,
inspect caller codegen and compare profiles. The optional Python stdlib runner
supports fresh/resumed named studies and source fingerprint guards. No timing
threshold is a CI gate. Prepared maps/shorter Newton replays remain isolated
experiments, not approved public APIs or promoted library changes.

The borrowed followup uses `benches/support/borrowed.rs` and lifetime/type rejection
fixtures. Keep point (12 affine entries) and vector (9 linear entries) validation
scopes distinct. Raw nonrigid acceptance and per-value/result checks remain;
prepare-time errors and a general batch contract require separate approval.
For targeted repeats, use the runner's `--filter '^amortization' --analysis-threads 2`;
prebuild and coordinate a quiet window. Do not edit historical study evidence.

The executable synthetic Python lab example is python/examples/lab_workflow.py;
its installed-wheel tests verify analytic outputs and actionable errors. See
[walkthrough](docs/python_lab_workflow.md) and [release policy](docs/RELEASING.md).
The policy does not authorize publication/version/tag changes. The private PEP517
backend embeds validated source/build provenance; direct maturin CLI bypasses
that gate. See [package readiness](docs/package_readiness.md) before packaging.
Preserve LF source identity, frozen sdist validation, license/metadata/RECORD
parity, binary path scans and narrow manylinux_2_28 x86_64 container evidence.
Never use a dirty/unknown development record as release signoff.

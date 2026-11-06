# Contributing

Use a branch and pull request; merge with a merge commit. Preserve others' work.
Do not publish, bump versions, or release unless assigned. The development pin
is 1.91.1 and the MSRV is 1.85 (edition 2024); do not silently change them.
Full runtime/UI snapshots use Rust 1.99.0 to keep diagnostics reproducible.

## Local checks

Use installed toolchains only; local tool/target installation needs permission.
On this Windows checkout, use the explicit selectors below to avoid accidental
rustup synchronization. Set two workers and run one heavy build/test at a time.

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
```

Run focused checks during fixes, then the full default/no_std/all-features suites
once after relevant edits. Repeat only for a new failure or changed code.
Include release builds and installed target cross-builds for math/no-std changes.
Explicit installed 1.85.0/1.91.1 library checks use cargo +TOOLCHAIN check --lib
--locked --jobs 2 with default, --no-default-features, and --all-features.
Older compiler UI snapshots are not the baseline. Review every trybuild stderr
for the intended error before adding/updating it; do not bless warning failures.

## CI scope

[ci.yml](.github/workflows/ci.yml) runs Linux/Windows full runtime/UI/doc suites
and the real example in default/no_std/all-features modes on 1.99.0. Linux jobs
check formatting, both Clippy/doc configurations with warnings denied, release
builds, and empty normal dependency graphs. Compatibility jobs compile the library
on 1.85.0 and 1.91.1 in three feature modes. A runner installs thumbv7em-none-eabihf
and cross-builds no_std thumb debug/release and MUSL library code; these are compile-only checks, not device runtime validation.
CI target installation is authorized on the runner, not on the local computer.
The redundant old Clippy/Rustfmt files were consolidated. CodeQL has a separate
three-language workflow. Sonar is not restored and has no workflow; owner access
and a hardened successor are pending. No new secrets are configured.
Local PASS does not claim remote CI PASS; wait for the actual GitHub checks.

## Review and maintenance

- Reproduce bugs first and add independent oracles/properties for math changes.
- Keep [requirements/evidence](docs/requirements/requirements.md) accurate.
- Update [CHANGELOG.md](CHANGELOG.md) under Unreleased and the canonical
  [remaining-work roadmap](docs/ROADMAP.md) when relevant; avoid duplicate plans.
- All runtime features are dependency-free. Backend feature names were removed;
  do not reintroduce unused dependency switches or silently change no-std policy.
- Check git diff --check, Markdown links, and final scope. Keep the warning policy.
- Pull before push (rebase linear unpushed commits, no-rebase if they include a
  merge). Never force-push, rewrite published history, or discard others' edits.
- No tool attribution in repository artifacts, commit messages, or PRs. Never
  commit credentials/.env files. There is no installed hook or release automation.

## Unit contract changes

Changes to frame/length/vector-unit contracts must update the numbered evidence
and [unit decisions](docs/units.md), including conversion rounding, invalid
metadata, representable-factor limits and custom/raw trust boundaries. Keep
exact reviewed type-mismatch UI baselines; version-sensitive trait-help text is
covered by strict paired passing/compile-fail public doctests instead. Stable
rustdoc verifies rejection, not a specific diagnostic code. Migrate examples
with explicit actual units, not a silent Meters default. No new runtime unit
conversion dependency or broader dimensional algebra is implied.

## Performance characterization

Use [the benchmark report](docs/performance.md) for methodology, selected commands,
profile differences, source fingerprints and resumable repeats. Criterion uses
existing dev dependencies; optional automation uses Python's standard library.
Prebuild before arranging a quiet timing window. CI compiles benches through
all-target Clippy and runs experimental correctness tests, not timing thresholds.
Host timing is not embedded evidence. Preserve raw independent repeats and
negative results; do not remove safety checks or adopt a candidate from one
favored profile/input case. Benchmark-only controls are not library APIs.

The [borrowed prototype](docs/borrowed_validation.md) is benchmark/test-only.
Target it with `--filter '^amortization' --analysis-threads 2` in a fresh named
study; retain the original evidence. Lifetime/private-state/frame/unit fixtures
must fail for their intended compiler errors on Windows and Linux. Do not infer
an approved API or batch failure policy from the fixture loop protocol.

## Python package

The [Python guide](docs/PYTHON-GUIDE.md) defines the separate crate/lock, local
venv commands, native parity and installed-wheel tests. The core's zero-normal-
dependency requirement does not apply to the isolated binding; it still applies
to all core runtime configurations. Only /python was added to the core package
exclude list; math, features and root lock are unchanged by the binding task.
[python.yml](.github/workflows/python.yml) builds/tests release abi3 wheels on
Linux/Windows with CPython 3.11/3.14, SHA-pinned actions and hash-locked build/test
tools. It tests without optional NumPy first, then with NumPy; Linux 3.11 also
rebuilds/installs the source distribution using the preinstalled build backend.
No upload/release job or new external service is introduced. Review all returned
PR checks, including external status contexts, before merge. Timing is not a gate.

The [synthetic lab walkthrough](docs/python_lab_workflow.md) runs outside the
checkout against the installed wheel; python/tests/test_lab_workflow.py is picked
up by the existing wheel and source-install CI test discovery. CSV decoding is
setup, not a Python per-row numeric loop. Before any assigned publication, follow
[versioning and release gates](docs/RELEASING.md); they do not authorize publishing.

## Readiness artifacts (no publication)

Use pip wheel with the in-tree backend in the Python guide, not direct maturin,
for provenance-bearing artifacts. Build-only control/negative tests:

```powershell
$env:RUSTUP_TOOLCHAIN = '1.99.0-x86_64-pc-windows-msvc'
$env:CARGO_BUILD_JOBS = '2'
python -I -m unittest discover -s python/packaging_tests -v
python python/verify_artifacts.py target/python-wheels
```

SPATIAL_EXPECT_COMMIT in readiness CI requires exact clean checked-out source;
never set it to bless a dirty build. The private backend stages inputs outside
Git, preserves checkout -Dwarnings alongside path remaps, disables implicit Rust
installation and rejects stale/tampered sdist contents. Extracted source archives
omit repository dev pin/config; source builds record the actual selected compiler.
Compiler notices require rust-docs; missing notices are explicitly unready.

Python CI uses digest-pinned manylinux_2_28 build/floor and newer Bookworm runtime
containers, Windows native builds, prepared/rebuilt metadata and complete RECORD
checks, a real too-new-glibc ELF negative, binary path scans and third-party license
inventory gates. Uploaded artifacts/hash inventories are dry-run evidence, not
published releases. Core CI, warnings, pin/MSRV and normal dependency policy stay
unchanged. See [design/limits](docs/package_readiness.md). No local Docker or
system/target install is inferred from those CI commands.

Artifact CI checks out the PR head for exact source identity; core CI still tests
the merge ref. Keep the branch current with main before merge and rerun gates on
any new merge commit. Linux candidates are each tested on both 3.11 and 3.14;
Windows matrix jobs build separate candidates. No upload selects a release.

## Security analysis

CodeQL checks Rust (including python/native), Python and Actions using extended
security queries. Its source-archive inventory and SARIF artifacts must show the
intended files and query results; a green workflow alone is insufficient evidence.
PR analyses are diff-informed (changed-line findings), not whole-source baselines.
Use a manual run on the exact head for full-source review and confirm that SARIF
does not report diff-informed mode; main pushes and schedules also run full scans.
Run `python -m unittest discover -s .github/scripts -p 'test_*.py'` for the
inventory controls. No security issue may be suppressed merely to pass a gate.

Sonar is **not restored**: its disabled legacy workflow is removed because its
token exposure and unpinned tools are unsafe. Do not enable that old workflow or
add its token while the old definition remains on main. Complete the owner setup
and hardened successor in the [security plan](docs/security_analysis.md) first.
Sonar findings will live in Sonar, not a duplicate GitHub SARIF export.

Before claiming current security evidence, verify workflow activation and the
exact commit of the latest analysis. Public scheduled workflows can be disabled
after 60 inactive days; maintainers must re-enable and run a real current scan
after inactivity. Never count skipped or unavailable analyses as passing scans.

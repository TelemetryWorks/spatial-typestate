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
The redundant old Clippy/Rustfmt files were consolidated. Existing CodeQL/Sonar
service configurations are separate; no new secrets/services were enabled.
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

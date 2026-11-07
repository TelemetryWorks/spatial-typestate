# Project structure

- src/: frame/point/vector/quaternion/transform/units/error modules and the frame macro.
- tests/: integration tests, independent analytic oracles, bounded property tests,
  trait-bound regressions, error reporting, and translation compatibility helper.
- tests/ui/: reviewed Rust 1.99 compile-fail fixtures and stderr snapshots.
- examples/sensor_alignment.rs: runnable sensor-aircraft-world workflow.
- examples/basic_usage.rs and examples/aircraft_frames.rs: no-op placeholders.
- benches/spatial.rs: Criterion host characterization and matched controls;
  support/experiments.rs: isolated hypotheses, not public library APIs.
- scripts/performance_study.py: optional stdlib-only resumable study runner.
- docs/performance.md and dated data: methods, raw samples/results/source snapshots,
  codegen evidence and limitations; excluded from crate packaging.
- docs/: requirements/evidence, design, frame/coordinate/math conventions, safety,
  and the canonical remaining-work roadmap. Diagram files are placeholders.
- .github/workflows/ci.yml: direct runtime, lint/docs, compatibility, dependency,
  and bare-metal compilation gates. codeql.yml separately analyzes Rust/Python/Actions.
  sonar-analysis.yml is the hardened successor; Sonar is NOT restored until real
  evidence passes review. See [security status](security_analysis.md).
- Cargo.toml/Cargo.lock: no normal dependencies; dev-only testing/benchmark tools.
- rust-toolchain.toml: development pin 1.91.1. Manifest MSRV is 1.85; full UI tests
  and direct CI use Rust 1.99.0 for stable diagnostics.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for commands and actual CI scope.

- [units.md](units.md): explicit unit/conversion decisions and documented limitations.

- benches/support/borrowed.rs and tests/borrowed_validation.rs: isolated borrowed
  invariants and caller-local comparison; not exported by src/lib.rs.
- [borrowed_validation.md](borrowed_validation.md): design, separate measurements,
  operation-specific scopes and pending production API/batch decisions.

## Python boundary

- python/native/: separate cdylib/core path dependency and own Cargo.lock; PyO3
  is absent from the core graph. lib.rs owns metadata/buffers, kernels.rs calls
  checked core methods in Python-free row loops.
- python/src/spatial_typestate/: thin re-exports, type stubs and py.typed.
- python/tests/: installed-wheel stdlib contracts plus optional NumPy interop.
- python/benchmark.py: bounded release-wheel latency/RSS runner.
- .github/workflows/python.yml: wheel/source-build/import/runtime gates.
- docs/PYTHON-GUIDE.md, python_design.md and python/2026-11-03/: contracts, losses
  and actual host measurement evidence. No public package release is implied.

- python/examples/lab_workflow.py and data/synthetic_sensor_100hz.csv: explicit
  synthetic telemetry batch analysis, tested through the installed wheel.
- [python_lab_workflow.md](python_lab_workflow.md): scenario, oracle and copy/error limits.
- [RELEASING.md](RELEASING.md): independent versioning, observed registry baseline
  and future release signoff/provenance gates, not publishing automation.

- python/build_backend.py: private stdlib PEP 517 staging/provenance wrapper;
  licenses/: exact locked dependency license/notice inventory.
- python/verify_artifacts.py, check_package_metadata.py and package_ci.py:
  artifact/ELF/metadata gates and CI-only pinned-container orchestration.
- python/packaging_tests/: negative/control tests separate from wheel runtime tests.
- [package_readiness.md](package_readiness.md): record schema, baseline and limits.

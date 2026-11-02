# Project structure

- src/: frame/point/vector/quaternion/transform/units/error modules and the frame macro.
- tests/: integration tests, independent analytic oracles, bounded property tests,
  trait-bound regressions, error reporting, and translation compatibility helper.
- tests/ui/: reviewed Rust 1.99 compile-fail fixtures and stderr snapshots.
- examples/sensor_alignment.rs: runnable sensor-aircraft-world workflow.
- examples/basic_usage.rs and examples/aircraft_frames.rs: no-op placeholders.
- benches/: essentially empty placeholders, not performance evidence.
- docs/: requirements/evidence, design, frame/coordinate/math conventions, safety,
  and the canonical remaining-work roadmap. Diagram files are placeholders.
- .github/workflows/ci.yml: direct runtime, lint/docs, compatibility, dependency,
  and bare-metal compilation gates. Existing CodeQL/Sonar configurations are separate.
- Cargo.toml/Cargo.lock: no normal dependencies; dev-only testing/benchmark tools.
- rust-toolchain.toml: development pin 1.91.1. Manifest MSRV is 1.85; full UI tests
  and direct CI use Rust 1.99.0 for stable diagnostics.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for commands and actual CI scope.

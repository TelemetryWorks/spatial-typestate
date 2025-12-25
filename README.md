<p align="center">
  <img src="https://raw.githubusercontent.com/TelemetryWorks/spatial-typestate/main/images/spatial_typestate_logo.png" alt="Spatial Typestate Banner" />
</p>

# Spatial Typestate

|          |                                                                                                    |
|----------|----------------------------------------------------------------------------------------------------|
| License  | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)                  |

`spatial-typestate` is a Rust library for safety-critical 3D coordinate systems.  
  
It uses typestate to encode the frame of reference and physical units in the type system, so that frame mixups and unit errors become compile-time bugs instead of runtime surprises.  

## Development
See `CONTRIBUTING.md` for build, test, and usage.

## Requirements
Requirements are documented in `docs/requirements/requirements.md`.

## Limitations & Alternatives

`Spatial Typestate` is currently under heavy development.  More to come in future versions.  

## License

MIT (See [LICENSE](./LICENSE))

## Project Structure
```
spatial-typestate/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── point.rs
│   ├── vector.rs
│   ├── transform.rs
│   ├── frame.rs
│   ├── units.rs
│   ├── quaternion.rs
│   ├── errors.rs
│   └── macros.rs        (optional – derive(Frame) etc.)
├── examples/
│   ├── basic_usage.rs
│   ├── aircraft_frames.rs
│   ├── sensor_alignment.rs
├── tests/
│   ├── transform_roundtrip.rs
│   ├── invariants.rs
│   ├── fuzz_compat.rs
├── benches/
│   ├── transform_bench.rs
│   ├── point_bench.rs
├── docs/
│   ├── SAFETY.md        (why typestate ensures no frame mixups)
│   ├── DESIGN.md        (formal design notes)
│   ├── ROADMAP.md
│   ├── frames.md        (list of built-in frames)
│   ├── math_conventions.md
│   ├── coordinate_systems.md
│   └── diagrams/
│       ├── axes.svg
│       ├── transform_sequence.puml
│       └── oriented_frames.png
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── lint.yml
│   │   ├── fuzz.yml
│   │   ├── docs.yml
│   └── ISSUE_TEMPLATE.md
├── README.md
└── LICENSE
```
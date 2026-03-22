<!-- docs/PROJECT_STRUCTURE.md -->

# Project Structure

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

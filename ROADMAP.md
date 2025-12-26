cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings
cargo build --all-targets --all-features
cargo test


Some people may assume:
* It’s primarily about type-level patterns, not about practical 3D math.
* Or that it’s an “academic toy crate” rather than production-oriented.

You can counter this with:
* Good docs and examples using aircraft/robot/sensor frames.
* Performance notes.
* CI + tests + fuzzing + “Safety & Correctness” section.

If tests are all green and you’re happy, next natural step is either:
* `README.md` that mirrors the safety story and shows usage examples, or
* starting to integrate a **math backend** (e.g., `nalgebra`) behind feature flags.

## Benchmarking
```
├── benches/ 
│ ├── transform_bench.rs 
│ ├── point_bench.rs
```
Those files are for **benchmarking** — measuring performance — using a crate like **Criterion**, which you already added as a dev-dependency.

🧭 **Why benchmarks exist in this crate**
Because `spatial-typestate` is meant for **real-time robotics / aerospace / control systems**, you may eventually need to answer:
* How many `apply_point()` calls per second can we do?
* Is quaternion normalization fast enough?
* Does switching to nalgebra / glam improve performance?
* How does `no_std` mode change speed?

Benchmarks allow you to **compare implementations** and **track regressions**.

For example — if we start with a naïve matrix multiply, then later introduce SIMD or nalgebra — benchmarks will prove whether it really improved speed.

---

📦 **How Rust Benchmark Layout Works**

Benchmarks live in:
```markdown
benches/
    transform_bench.rs
    point_bench.rs
```

Cargo automatically runs them with:

```bash
cargo bench
```
…but only if you use **Criterion** (recommended).
The built-in Rust unstable `#[bench]` framework is nightly-only — so Criterion is preferred.

---

📐 **Example Benchmark Files**
`benches/transform_bench.rs`
```rust
use criterion::{criterion_group, criterion_main, Criterion};
use spatial_typestate::{spatial_frames, Frame, Point3, Transform};

spatial_frames! { World }

pub fn bench_apply_point(c: &mut Criterion) {
    let t: Transform<World, World> = Transform::from_translation(10.0, 0.0, 0.0);
    let p: Point3<World> = Point3::new(1.0, 2.0, 3.0);

    c.bench_function("apply_point", |b| {
        b.iter(|| {
            let _ = t.apply_point(p);
        })
    });
}

criterion_group!(benches, bench_apply_point);
criterion_main!(benches);
```
`benches/point_bench.rs`
```rust
use criterion::{criterion_group, criterion_main, Criterion};
use spatial_typestate::{spatial_frames, Frame, Point3};

spatial_frames! { World }

pub fn bench_point_new(c: &mut Criterion) {
    c.bench_function("point_new", |b| {
        b.iter(|| {
            let _ = Point3::<World>::new(1.0, 2.0, 3.0);
        })
    });
}

criterion_group!(benches, bench_point_new);
criterion_main!(benches);
```
---
🧪 **Running the Benchmarks**
```bash
cargo bench
```
Criterion will:
* Compile optimized `--release` mode
* Run thousands of iterations
* Produce text output + HTML reports (usually in `target/criterion/report/`)

---

🚦 **Benchmarking in a safety-critical mindset**

Benchmarks here aren’t just about speed — they give you **quantitative evidence** like:
| Operation                  | µs/iter |  ns/iter |                 Hz |
| -------------------------- | ------: | -------: | -----------------: |
| `apply_point` naïve        |   90 ns |  0.09 µs | 11,000,000 ops/sec |
| `apply_point` via nalgebra |   14 ns | 0.014 µs | 71,000,000 ops/sec |

This tells you whether a design change is worth it before taking on implementation risk.

---

📌 **TL;DR — What are those files for?**

✔ They **measure performance**, not correctness
✔ They **inform design choices** (matrix backend, SIMD, etc.)
✔ They are essential for **high-rate real-time systems** (flight dynamics, robotics, sensors)

---

🚀 **Ready to add real benchmarking?**
If you want, I can:
* Fully generate both benchmark files
* Add a benchmark README
* Add a GitHub Action to run Criterion + upload HTML reports

---

## Roadmap

**Phase 0 – MVP:**
* [ ] `Point3<F>`, `Vector3<F>` with phantom frame type.
* [ ] `Transform<From, To>` with `apply(Point3<From>) -> Point3<To>`.
* [ ] No `unsafe`, `no_std` compatible.
* [ ] Right-handed coord system + units clearly documented.

**Phase 1 – Safety hardening:**
* [ ] Newtypes for units (`Meters`, `Radians`, etc.).
* [ ] `UnitQuat<F>` with smart constructors.
* [ ] Property-based tests for transform invariants.
* [ ] `clippy` + zero warnings in CI.

**Phase 2 – Safety-critical posture:**
* [ ] Fuzz tests for transforms & composition.
* [ ] Optional NaN/Inf checks in debug builds.
* [ ] "Safety and Correctness" design doc in `docs/`.
* [ ] Map crate practices to generic safety-critical ideas (determinism, invariants, absence of UB).

---

## Goals and Roadmaps

1. What should we call this?
2. How to aim this at safety-critical use
"Safety-critical direction" here means:
* API makes misuse hard or impossible
* Implementation is minimal, predictable, and verifiable
* Process & docs look like something an auditor could respect

Think in three layers:

**A. API design for correctness**
1. Everything is tagged by frame and units
  * `Point3<F>`: position in frame `F`
  * `Vector3<F>`: vector in frame `F`
  * `Transform<From, To>`: rigid transform from `From` to `To`
  * Optional: `Angle<Radians>`, `Angle<Degrees>`, `Length<Meters>`, etc.
No naked `f32/f64` for anything with semantics.

2. No “generic” transforms

Don’t expose a `Transform` that doesn’t know source/target frames. Always:
```rust
struct Transform<From, To> { ... }

impl<From, To> Transform<From, To> {
    fn apply(&self, p: Point3<From>) -> Point3<To> { ... }
}
```
This forbids “oops I passed a World point to a Body transform” at compile time.

3. Invariants encoded in types
Example: rotations must be normalized.
```rust
struct UnitQuat<F> { /* guaranteed unit length */ }

impl<F> UnitQuat<F> {
    // Smart constructor that either normalizes or returns Err if too degenerate
    fn try_new(x: f64, y: f64, z: f64, w: f64) -> Result<Self, QuaternionError>;
}
```
You never expose a raw “maybe-unit” quaternion to the public API.

4. Typestate for lifecycle / validity
If you later add, say, calibration or alignment:

```rust
struct Sensor;
struct Uncalibrated;
struct Calibrated;

struct SensorFrame<State> { ... }

type UncalibratedSensorFrame = SensorFrame<Uncalibrated>;
type CalibratedSensorFrame = SensorFrame<Calibrated>;

impl SensorFrame<Uncalibrated> {
    fn calibrate(self, data: CalibrationData) -> SensorFrame<Calibrated> { ... }
}
```
Now you can’t accidentally use an uncalibrated frame where a calibrated one is required.

5. Deliberately “no convenience foot-guns”
* No automatic `From<Point3<World>> for Point3<Body>`.
* No implicit unit conversions.
* Conversions always go through explicit APIs like `.to_frame(...)` or `.convert_units(...)`.

---

**B. Implementation discipline (safety-critical flavor)**
1. No `unsafe` in the public crate (or isolate it in a tiny, audited module)
  * Either: "no `unsafe` at all" (best for trust).
  * Or: 1 small `unsafe` module with documented safety contracts and exhaustive tests.
2. No panics in normal flow
  * Public functions return `Result<_, Error>` instead of `panic!`.
  * Panics only for programmer bugs (e.g. `unreachable!()` in truly unreachable branches).
3. Deterministic, side-effect-free core
  * Pure math functions: no global state, no randomness, no time access.
  * Same inputs → same outputs.
4. `no_std` support
For safety-critical / embedded / avionics-style work, `no_std` is a big plus:
  * Use `#![no_std]` at the crate root, with optional std feature for convenience.
  * Avoid heap allocation in core types.

5. Clippy and lint policy
  * Turn on `#![deny(warnings)]` in CI.
  * Use `#![warn(clippy::all, clippy::pedantic, clippy::nursery)]` and selectively allow what you really need.
  * This supports a “zero-warning” policy, which safety folks like.

---

**C. Validation, testing, and documentation**
1. Property-based tests
Use `proptest` or `quickcheck` style tests:
  * For random valid rotations and points:
    * `T.inverse().apply(T.apply(p)) ≈ p`
    * `(T2 ∘ T1).apply(p) ≈ T2.apply(T1.apply(p))`

  * Test composition/inversion round-trip.

2. Cross-checking with a reference library
  * Internally validate your transforms against `nalgebra`/`cgmath` in tests.
  * This gives a “second implementation” to catch mistakes.

3. Numerical safety checks (behind a feature flag)
  * In debug or with a `check-nans` feature:
    * Assert all outputs are finite (no NaN/inf).
  * Provide clear docs about:
    * coordinate conventions (right-handed? which axis up/forward?),
    * units (meters, radians),
    * expected ranges.

4. Fuzzing
  * Simple fuzz targets: random transforms, compositions, inverses.
  * Check for:
    * no panics,
    * no NaNs (optional),
    * invariants hold.

5. Documentation as a “mini safety case”
  In `README.md` and `docs/`:
  * State goals: prevent frame mixups via Rust’s type system.
  * Explain invariants: frames, units, right-hand rule, normalization.
  * Explain non-goals: e.g., “this does not replace independent verification and validation (IV&V), but supports it.”
  * Add formal-ish language that safety people like: “misuse prevented by construction,” “typestate-encoded invariants,” etc.

6. API stability & semver discipline
  * Avoid breaking changes to core types casually.
  * When possible, add new frames / types in a backward-compatible way.
  * Maintain a clear `CHANGELOG.md`.

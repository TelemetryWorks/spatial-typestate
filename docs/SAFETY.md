# spatial-typestate — Safety and Correctness Notes

This document explains how `spatial-typestate` is designed to support
safety-critical or high-integrity applications by enforcing key invariants
at the type level and keeping the implementation auditable.

The goal is **not** to claim formal certification, but to make it easier to
reason about correctness and to integrate this crate into a larger safety case.

---

## 1. Scope and Intent

`spatial-typestate` focuses on three core concerns:

1. **Frame correctness**  
   Prevent using a coordinate expressed in one frame (e.g. body) as though it
   were expressed in another frame (e.g. world).

2. **Unit correctness (early scaffolding)**  
   Tag scalar quantities with unit types (e.g. meters, radians) so that
   incompatible quantities cannot be combined without explicit intent.

3. **Rotation correctness**  
   Represent rotations with a `UnitQuat<F>` type that encodes the frame and
   enforces the unit-length invariant at construction time.

The crate is intended as a **building block** for systems where misinterpreting
coordinate frames or units could contribute to unsafe behavior.

---

## 2. Type-Level Invariants

### 2.1 Frames

Each coordinate frame is represented by a **zero-sized marker type** that
implements the `Frame` trait:

```rust
use spatial_typestate::Frame;

pub struct World;
pub struct Body;
pub struct Sensor;

impl Frame for World {}
impl Frame for Body {}
impl Frame for Sensor {}
```
The following types encode the frame in a generic parameter:  
* `Point3<F>` — point in frame F
* `Vector3<F>` — vector in frame F
* `Transform<From, To>` — transform from From to To
* `UnitQuat<F>` — rotation associated with frame F

This guarantees at compile time:
* A `Transform<From, To>` can only be applied to `Point3<From>`.
* The result is always `Point3<To>`.
* You cannot accidentally pass a `Point3<Body>` where a `Point3<World>` is expected without an explicit, visible conversion.

**Design principle**: frame mixups are prevented by construction, not by runtime checks.

### 2.2 Units

The `units` module introduces a generic scalar type:
```rust
Quantity<U>
```
where `U` is a marker unit type (e.g. `Meters`, `Radians`, `Degrees`).

Key properties:
* Only quantities with the **same unit type** can be added or subtracted.
* The underlying numeric type is `f64`, but it is only accessible via `Quantity::get()`.

At this stage, units are intentionally minimal. The design leaves room for future:
* Multiplication and division that produce derived units.
* Explicit conversion functions between related units (e.g. radians/degrees).

### 2.3 Rotations
`UnitQuat<F>` represents a unit quaternion associated with frame `F`.

Construction is controlled via:
* `UnitQuat::try_from_components(x, y, z, w)` — normalizes inputs, rejects:
  * non-finite values (`NaN`/`inf`) → `SpatialError::NonFinite`
  * zero-norm inputs → `SpatialError::ZeroNormQuaternion`
* `UnitQuat::identity()` — returns the identity rotation.

This ensures the **unit-length invariant** is enforced at the API boundary.

---

## 3. Implementation Constraints

To keep the crate auditable and predictable:

1. **No `unsafe` in the public API**
The crate is compiled with:
```rust
#![deny(unsafe_code)]
```
Any future `unsafe` (if ever introduced) must be:
* isolated in a clearly documented internal module, and
* justified with an explicit safety contract.

2. **`no_std` support**

The crate is `no_std`-friendly:
* Controlled by `std` / `no_std` feature flags.
* Core functionality avoids heap allocations and OS dependencies.

3. **No panics in normal operation**
* Constructors that can fail (`UnitQuat::try_from_components`) return
  `Result<_, SpatialError>` rather than panicking.
* Panics are reserved for programmer errors and test assertions.

4. **Deterministic behavior**
* All math functions are pure: same inputs → same outputs.
* No global mutable state, I/O, randomness, or time dependencies.

---

## 4. Testing and Verification Strategy

### 4.1 Unit Tests

The `tests/` directory includes:
* `basic_usage.rs` — smoke tests for the main types.
* `transform_roundtrip.rs` — checks transform identity and translation behavior.
* `quaternion_invariants.rs` — validates unit quaternion invariants.
* `fuzz_compat.rs` — a small harness suitable for fuzzing.

These tests are intended to be easy to read and map directly to documented
invariants.

### 4.2 Property-Based Tests

Using `proptest`, we test properties that must hold for **all** inputs within a range:
* `transform_proptest.rs`:
  * Identity transform preserves any point.
  * A translation transform adds its offset for any point.
* `quaternion_proptest.rs`:
  * `UnitQuat::try_from_components` produces a unit quaternion for any finite, non-degenerate input.
* `quantity_proptest.rs`:
  * Addition and subtraction behave as expected for quantities:
    * `(a + b) - b == a`
    * `0` is the additive identity.

### 4.3 Compile-Fail Tests

Using `trybuild`, we include **compile-fail** tests to ensure that certain misuses **never compile**:
* `tests/ui/frame_mismatch.rs`:
  * Attempts to apply `Transform<World, Body>` to `Point3<Body>`.
  * The test asserts that this code fails to compile due to a type mismatch.

This verifies the typestate design is enforced by the Rust compiler itself, not just by conventions.

### 4.4 Fuzzing Integration (Planned)

The `fuzz_compat` harness is designed to be reused in `cargo-fuzz` targets.
The intent is to:
* Continuously fuzz the transform and quaternion operations.
* Assert the absence of panics and NaNs for finite inputs.
* Complement unit/property tests with coverage over “weird” edge cases.

---

## 5. Limitations and Non-Goals (Current State)

* The crate does **not** yet provide:
  * Full physical unit algebra (derived units, conversion graphs, etc.).
  * A formal proof of correctness or certification under standards such as DO-178C or ISO 26262.
  * Domain-specific safety logic (e.g., envelope protection, collision detection).
* The math backend is currently a simple 4×4 matrix representation. Future versions may integrate with crates like nalgebra or glam, but the typestate-based API is intended to remain stable.

---

## 6. Roadmap for Stronger Assurance

Planned directions for improving safety and verifiability:
1. **Backend abstraction**
  * Wrap a well-tested math library behind a stable trait layer.
2. **Extended units system**
  * Derived units (e.g., velocity, acceleration).
  * Explicit, auditable conversions (e.g., degrees ↔ radians).
3. **Stronger invariants for transforms**
  * Checked constructors for rigid transforms (orthonormal rotations).
4. **Increased property and fuzz coverage**
  * Composition properties: `(T2 ∘ T1).apply(p) == T2.apply(T1.apply(p))`.
  * Roundtrip tests with inverses once they are implemented.
5. **Documentation alignment with safety standards**
  * Mapping crate guarantees to generic safety concepts:
    * "Preventing class of misuse by design."
    * "Type-level encoding of state and invariants."
  * Example patterns for integrating this crate into a larger safety case.

---

`spatial-typestate` is deliberately small and explicit, with most complexity pushed into the type system rather than runtime code. This design is meant to make it easier to review, reason about, and trust in systems where frame and unit mistakes are unacceptable.


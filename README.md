# Spatial Typestate

A small Rust library for frame-tagged 3D points, vectors, unit quaternions, and
rigid transforms. APIs are evolving. The crate is not certified for safety-,
life-, or mission-critical use; applications must independently validate their
physical frame definitions, calibration, unit declarations, and numerical requirements.

## Sensor -> aircraft -> world

```rust
use spatial_typestate::{Dimensionless, Feet, Meters, Point3, Transform, UnitQuat, Vector3, spatial_frames};
spatial_frames! { Sensor, Aircraft, World }
fn main() -> Result<(), spatial_typestate::SpatialError> {
    let sensor_aircraft = Transform::<Sensor, Aircraft, Meters>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0)?, // Rz(+90 degrees)
        Vector3::<_, Meters>::new(1.0, 2.0, 3.0), // source origin in target coordinates
    )?;
    let aircraft_world = Transform::<Aircraft, World, Meters>::try_from_rotation_translation(
        UnitQuat::try_from_components(1.0, 0.0, 0.0, 1.0)?, // Rx(+90 degrees)
        Vector3::<_, Meters>::new(10.0, 20.0, 30.0),
    )?;
    let sensor_world = sensor_aircraft.then(aircraft_world)?;
    let point = Point3::<Sensor, Meters>::new(2.0, 0.0, 1.0);
    let world = sensor_world.apply_point(point)?;
    assert!((world.x - 11.0).abs() < 1e-9);
    assert!((world.y - 16.0).abs() < 1e-9);
    assert!((world.z - 34.0).abs() < 1e-9);
    let restored = sensor_world.try_inverse()?.apply_point(world)?;
    assert!((restored.x - point.x).abs() < 1e-9);
    let vector = sensor_world.apply_vector(Vector3::<_, Dimensionless>::new(2.0, 0.0, 1.0))?;
    assert!((vector.y + 1.0).abs() < 1e-9); // translation is not applied
    // Explicit conversion: both point and translation must use the same length.
    let feet_map = sensor_world.convert_to::<Feet>()?;
    let feet_point = point.convert_to::<Feet>()?;
    let feet_world = feet_map.apply_point(feet_point)?.convert_to::<Meters>()?;
    assert!((feet_world.z - world.z).abs() < 1e-9);
    Ok(())
}
```

Run the [complete example](https://github.com/TelemetryWorks/spatial-typestate/blob/main/examples/sensor_alignment.rs), which verifies all
coordinates, sequential/composed mapping, inverse roundtrip, and vectors:

```powershell
cargo +1.99.0-x86_64-pc-windows-msvc run --locked --jobs 2 --example sensor_alignment
cargo +1.99.0-x86_64-pc-windows-msvc run --locked --jobs 2 --no-default-features --features no_std --example sensor_alignment
```

The example executable uses std for printing even when the library is no_std.
Its analytic result is point (11,16,34) and vector (0,-1,2). These are supplied
numeric relationships, not a sensor calibration performed by the library.

## Contracts and limits

- Bare frame structs only need `impl Frame`; the four spatial value types have
  Copy/Clone/Debug/PartialEq without marker bounds. Frame mismatches still fail
  to compile. A label cannot prove that physical measurements use the right frame.
- The checked transform constructor uses Hamilton (x,y,z,w), right-handed active
  algebra and column vectors: p_To=R(q)*p_From+t_To. Columns of R are source basis
  vectors in To; t is the source origin in To. UnitQuat<To> alone does not encode
  the source label. Application axes and physical frame relationships remain caller choices.
- `first.then(next)` means next(first(point)). `apply_vector` uses only R.
  Row storage is matrix[row][column], with last-column translation. Raw bottom
  rows are ignored by point application/composition, and composition emits a
  canonical affine bottom row. Each operation returns Result and rejects
  non-finite participating inputs or outputs. Sequential and composed mappings
  check different intermediates, so their overflow errors can differ.
- Public matrix storage/from_matrix remain unvalidated. `try_inverse` checks
  finite entries, affine row, orthonormal rotation and det(R)=+1 with absolute
  tolerance 1e-10, then returns R^T and -R^T*t. It rejects non-rigid finite input
  or non-finite input/output, including inverse translation overflow.
- Inverse tolerance permits near-rigid input. Error scales with coordinate and
  translation magnitude and accumulates over long chains; no universal absolute
  roundtrip bound exists. Successful application/composition returns finite values;
  raw construction does not establish a finite or rigid invariant.
- UnitQuat accepts all finite nonzero components, including MAX/subnormals,
  rejects non-finite/all-zero input, and has private fields with const getters.
  Unit length is approximate; tiny relative components may round to signed zero.
  Equality compares components, so q and -q are unequal despite equivalent rotation.
- Points/transforms require an explicit length tag; vectors require an explicit
  unit tag. There is no default unit. Translation, point mapping and composition
  require matching lengths. Generic vector mapping preserves its unit independently
  of translation. UnitQuat remains dimensionless.
- Explicit checked `convert_to::<Feet>()`/`convert_to::<Meters>()` is shared with
  Quantity; it preserves frames and changes only transform translation. No
  automatic mixing, dimensional algebra or angle conversion is implemented.
  Raw constructors/public components still assert units without validating them.
- SpatialError implements Display/core Error. Constructors return its concrete
  exhaustive enum without allocation/dynamic dispatch; callers may choose boxed
  propagation. New variants require downstream exhaustive-match updates.

See [requirements and evidence](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/requirements/requirements.md),
[math conventions](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/math_conventions.md), [design](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/DESIGN.md),
[frames](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/frames.md), and [safety notes](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/SAFETY.md).

## Unit migration and limitations

Replace old `Point3<F>`, `Vector3<F>`, and `Transform<From,To>` annotations with
`Point3<F,L>`, `Vector3<F,U>`, and `Transform<From,To,L>`. Choose the actual units;
old numbers are not automatically meters. Use Dimensionless for direction vectors,
not positions or translation. Existing method names and checked Result handling
remain. Meters and international Feet are the first convertible length tags.

Custom Unit/LengthUnit markers remain open. Optional `LinearLengthUnit` metadata
provides meters-per-unit for length conversions only; opaque vectors can rotate
without metadata. Custom declarations are trusted, not dimensionally inferred.
Nonpositive/non-finite scales return `InvalidUnitScale`; a ratio rounded to zero
or infinity returns `UnrepresentableUnitConversion`. Add these variants to
exhaustive SpatialError matches. Non-finite inputs/results return `NonFinite`.

Conversion computes a representable scale ratio then multiplies components.
Rounding and component underflow to signed zero are allowed; overflow is an error.
Some extreme ratios are rejected even when rearranging arithmetic could work.
Finite same-unit component bits are preserved. No exact roundtrip or universal
accuracy guarantee is made. Raw matrix coefficients must be dimensionless for
these unit semantics; tags cannot verify calibration, raw data, or custom claims.
See [unit decisions and all limitations](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/units.md)
for the conservative algorithm, raw escape hatches and deliberately excluded scope.

## Features, development, and verification

The only runtime features are `std` (default) and `no_std` (a marker).
Disable defaults to select the no-std implementation:

```toml
spatial-typestate = { version = "0.0.2", default-features = false, features = ["no_std"] }
```

Enabling no_std alongside defaults does not disable std. All runtime feature
graphs have zero normal dependencies; dev testing/benchmark tools remain.
The unused nalgebra/glam features/dependencies were removed, not implemented as
backends. The std path retains native sqrt; no-std uses a private eight-step
Newton helper only on scaled squared norms in [1,4]. No libm, correctly-rounded
sqrt equivalence or timing guarantee is claimed.

The declared MSRV is 1.85, the committed development pin is 1.91.1, and explicit
local/CI runtime verification uses installed Rust 1.99.0. No toolchain policy was
changed. [CONTRIBUTING.md](https://github.com/TelemetryWorks/spatial-typestate/blob/main/CONTRIBUTING.md) has exact commands and CI scope.
The [CI workflow](https://github.com/TelemetryWorks/spatial-typestate/blob/main/.github/workflows/ci.yml) runs Linux/Windows default/no_std/
all-feature tests, example execution, warning-denied lint/docs, compatibility
library checks, dependency graph gates, and runner-only thumb/MUSL cross-builds.
Local tests do not claim remote CI success or device execution. Bare-metal target
installation is authorized on CI only; it has not been performed locally.

The translation compatibility helper has deterministic/property tests, not a
cargo-fuzz setup. Two other example files remain placeholders;
diagrams are unpopulated. See [migration/change notes](https://github.com/TelemetryWorks/spatial-typestate/blob/main/CHANGELOG.md) and the
[canonical remaining-work list](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/ROADMAP.md). License: [Apache-2.0](https://github.com/TelemetryWorks/spatial-typestate/blob/main/LICENSE).

## Performance characterization

[Measured host study and limitations](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/performance.md)
cover checked math/conversion, actual std/no-std normalization, error/extreme
inputs, chained/batched workflows and isolated optimization controls. Results
retain raw samples, per-run intervals and observed spikes on one Windows/Ryzen
host across LTO/no-LTO profiles. They are not universal or embedded timing guarantees.
No production optimization or new prepared/batch API is introduced by the study.

```powershell
cargo +1.99.0-x86_64-pc-windows-msvc bench --locked --jobs 2 --bench spatial -- --test
# Run selected timings only in a quiet window; see the report for repeats/profiles.
cargo +1.99.0-x86_64-pc-windows-msvc bench --locked --jobs 2 --bench spatial -- point_candidates
```

[Borrowed-validation prototype and decision record](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/borrowed_validation.md)
compare caller-local hoisting with lifetime-bound point/vector preparations.
The isolated prototype preserves per-input/output checks and numeric/type
contracts. Preparation error timing and any batch API remain decisions for
review; no production API is added. New measurements remain separate from the
original study, with environment load, variance and codegen limitations recorded.

## Python batches

An unreleased, separate [Python package](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/PYTHON-GUIDE.md)
provides Rust-owned point/vector batches, immutable runtime frame/unit metadata,
checked transforms/quaternions, and bytes-backed memoryviews without a Python
object per row. Python frame/unit errors are runtime checks, not Rust compile-time
proofs. Import/export copy, the binding requires std/CPython, and custom Rust unit
markers are not exposed. The core remains dependency-free/no_std-capable.
No PyPI publication or native performance parity is implied.

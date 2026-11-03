# Spatial Typestate

A small Rust library for frame-tagged 3D points, vectors, unit quaternions, and
rigid transforms. APIs are evolving. The crate is not certified for safety-,
life-, or mission-critical use; applications must independently validate their
physical frame definitions, calibration, units, and numerical requirements.

## Sensor -> aircraft -> world

```rust
use spatial_typestate::{Point3, Transform, UnitQuat, Vector3, spatial_frames};
spatial_frames! { Sensor, Aircraft, World }
fn main() -> Result<(), spatial_typestate::SpatialError> {
    let sensor_aircraft = Transform::<Sensor, Aircraft>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0)?, // Rz(+90 degrees)
        Vector3::new(1.0, 2.0, 3.0), // source origin in target coordinates
    )?;
    let aircraft_world = Transform::<Aircraft, World>::try_from_rotation_translation(
        UnitQuat::try_from_components(1.0, 0.0, 0.0, 1.0)?, // Rx(+90 degrees)
        Vector3::new(10.0, 20.0, 30.0),
    )?;
    let sensor_world = sensor_aircraft.then(aircraft_world)?;
    let point = Point3::<Sensor>::new(2.0, 0.0, 1.0);
    let world = sensor_world.apply_point(point)?;
    assert!((world.x - 11.0).abs() < 1e-9);
    assert!((world.y - 16.0).abs() < 1e-9);
    assert!((world.z - 34.0).abs() < 1e-9);
    let restored = sensor_world.try_inverse()?.apply_point(world)?;
    assert!((restored.x - point.x).abs() < 1e-9);
    let vector = sensor_world.apply_vector(Vector3::new(2.0, 0.0, 1.0))?;
    assert!((vector.y + 1.0).abs() < 1e-9); // translation is not applied
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
  the source label. Application axes and numeric units remain caller choices.
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
- Quantity<U> is a scalar unit tag. Spatial coordinates/translations are raw f64;
  full dimensional algebra and implicit unit conversions are not implemented.
- SpatialError implements Display/core Error. Constructors return its concrete
  exhaustive enum without allocation/dynamic dispatch; callers may choose boxed
  propagation. NonRigidTransform is a new variant requiring downstream match updates.

See [requirements and evidence](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/requirements/requirements.md),
[math conventions](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/math_conventions.md), [design](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/DESIGN.md),
[frames](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/frames.md), and [safety notes](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/SAFETY.md).

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
sqrt equivalence, timing guarantee, or benchmark performance number is claimed.

The declared MSRV is 1.85, the committed development pin is 1.91.1, and explicit
local/CI runtime verification uses installed Rust 1.99.0. No toolchain policy was
changed. [CONTRIBUTING.md](https://github.com/TelemetryWorks/spatial-typestate/blob/main/CONTRIBUTING.md) has exact commands and CI scope.
The [CI workflow](https://github.com/TelemetryWorks/spatial-typestate/blob/main/.github/workflows/ci.yml) runs Linux/Windows default/no_std/
all-feature tests, example execution, warning-denied lint/docs, compatibility
library checks, dependency graph gates, and runner-only thumb/MUSL cross-builds.
Local tests do not claim remote CI success or device execution. Bare-metal target
installation is authorized on CI only; it has not been performed locally.

The translation compatibility helper has deterministic/property tests, not a
cargo-fuzz setup. Two other example files and benches remain placeholders;
diagrams are unpopulated. See [migration/change notes](https://github.com/TelemetryWorks/spatial-typestate/blob/main/CHANGELOG.md) and the
[canonical remaining-work list](https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/ROADMAP.md). License: [Apache-2.0](https://github.com/TelemetryWorks/spatial-typestate/blob/main/LICENSE).

# Migration: published Rust 0.0.1 to candidate Rust 0.1.0

Candidate decision, 2026-11-08: Rust **0.1.0**, Python distribution **0.1.0**,
and its private native crate **0.1.0**. These are unpublished candidate versions,
not an installation or publication announcement. This step selects metadata and
finalizes migration notes; it does not approve artifacts, tags or uploads.

The live registry check on that date found only Rust 0.0.1 (not yanked), and
PyPI returned 404. A 404 does not reserve the Python name or prove upload rights.
The baseline below is the actual [published crate](https://crates.io/crates/spatial-typestate/0.0.1),
archive SHA256 `b4c0b2c27b4ce9703ba7710f04281febaaf41f2c0327ef652f9c427b1c27320c`.
Its `.cargo_vcs_info.json` names commit
`897f2be9ad55dcab11fea2a1b3d88dce88510df7`. That is archive metadata, not a tag.
The interim 0.0.2 checkout was never published at this check.

## Rust changes relative to the published API

| Published 0.0.1 | Candidate 0.1.0 / caller action |
| --- | --- |
| `Point3<F>` | `Point3<F, L>` with an explicit `L: LengthUnit`, such as `Meters` or `Feet`. |
| `Vector3<F>` | `Vector3<F, U>` with an explicit `U: Unit`; use `Dimensionless` for a unitless direction. |
| `Transform<From, To>` | `Transform<From, To, L>` with an explicit length tag. Its translation and mapped points share `L`. |
| `apply_point(p) -> Point3<To>` | `apply_point(p) -> Result<Point3<To, L>, SpatialError>`; propagate with `?` or handle the error. Participating non-finite inputs/results now fail instead of propagating unchecked values. |
| `identity`, `from_matrix`, `from_translation` | Still available with the extra length type. Raw matrix/translation constructors remain unvalidated. |
| Public quaternion `x`, `y`, `z`, `w` | Private components: read through `x()`, `y()`, `z()`, `w()`. Mutation is no longer available. |
| `UnitQuat::new_unchecked` | Removed. Use `try_from_components` and handle errors, or `identity()`. There is no public unchecked replacement. |
| Two exhaustive `SpatialError` variants | Add arms for `NonRigidTransform`, `InvalidUnitScale`, and `UnrepresentableUnitConversion`. |
| `nalgebra`, `glam` feature flags | Removed along with their optional dependencies. Remove these flags from manifests/commands; no backend selection replaces them. |
| No declared `rust-version` | Declared library MSRV 1.85, edition 2024. Development pin 1.91.1 and runtime/UI verification compiler 1.99.0 are separate policies. |

There is no default unit. Choose tags from the meaning of existing coordinates;
adding `Meters` to feet-valued numbers does not convert them. `Frame`, `Unit`,
`LengthUnit`, `AngleUnit`, `Meters`, `Radians`, `Degrees` and `Quantity` remain.
`Feet`, `Dimensionless` and the opt-in `LinearLengthUnit` trait are additions.
Manual value traits no longer require value-trait derives on bare frame markers.

### The existing point operation: exact old and new equivalents

Published 0.0.1 (checked against the downloaded archive):

```rust
use spatial_typestate::{Frame, Point3, Transform};
struct Body;
struct World;
impl Frame for Body {}
impl Frame for World {}

fn main() {
    let p = Point3::<Body>::new(1.0, 2.0, 3.0);
    let map = Transform::<Body, World>::from_translation(10.0, 20.0, 30.0);
    let mapped: Point3<World> = map.apply_point(p);
    assert_eq!((mapped.x, mapped.y, mapped.z), (11.0, 22.0, 33.0));
}
```

Candidate 0.1.0, with the same coordinates asserted to be meters:

```rust
use spatial_typestate::{Frame, Meters, Point3, SpatialError, Transform};
struct Body;
struct World;
impl Frame for Body {}
impl Frame for World {}

fn main() -> Result<(), SpatialError> {
    let p = Point3::<Body, Meters>::new(1.0, 2.0, 3.0);
    let map = Transform::<Body, World, Meters>::from_translation(10.0, 20.0, 30.0);
    let mapped: Point3<World, Meters> = map.apply_point(p)?;
    assert_eq!((mapped.x, mapped.y, mapped.z), (11.0, 22.0, 33.0));
    Ok(())
}
```

Keeping the old return assumption after fixing the generics must not compile:

```rust,compile_fail
use spatial_typestate::{Frame, Meters, Point3, Transform};
struct Body;
struct World;
impl Frame for Body {}
impl Frame for World {}
fn main() {
    let p = Point3::<Body, Meters>::new(1.0, 2.0, 3.0);
    let map = Transform::<Body, World, Meters>::identity();
    let _mapped: Point3<World, Meters> = map.apply_point(p); // Result is not Point3
}
```

### Additions, not renamed 0.0.1 operations

`then`, `apply_vector`, `try_inverse`, `try_from_rotation_translation`, and
`convert_to` did **not** exist in published 0.0.1. Their `Result` contracts are
new API relative to that baseline. Unreleased changelog entries about earlier
unchecked forms describe intermediate development, not calls a 0.0.1 user had.

```rust
use spatial_typestate::{Dimensionless, Feet, Frame, Meters, Point3,
                        SpatialError, Transform, UnitQuat, Vector3};
struct Body;
struct World;
impl Frame for Body {}
impl Frame for World {}

fn main() -> Result<(), SpatialError> {
    let map = Transform::<Body, World, Meters>::try_from_rotation_translation(
        UnitQuat::<World>::identity(), Vector3::<World, Meters>::new(10.0, 20.0, 30.0))?;
    let next = Transform::<World, World, Meters>::identity();
    let combined = map.then(next)?; // next(map(p)), not map(next(p))
    let direction = combined.apply_vector(Vector3::<Body, Dimensionless>::new(1.0, 0.0, 0.0))?;
    assert_eq!((direction.x, direction.y, direction.z), (1.0, 0.0, 0.0));
    let _inverse = combined.try_inverse()?;
    let meters = Point3::<World, Feet>::new(1.0, 0.0, 0.0).convert_to::<Meters>()?;
    assert_eq!(meters.x, 0.3048);
    Ok(())
}
```

The quaternion tag is the target frame; it does not prove the physical relation
between source and target. Vectors ignore translation and preserve their own
unit tag. Points/composition share the transform's length tag. Matrix application
is row-major with column vectors and translation in the last column; see
[math conventions](math_conventions.md), not the old column-major prose.

### Quaternion and error behavior

The old constructor squared raw components, summed, then took a square root.
Finite tiny inputs could underflow to a zero norm; finite large inputs could
overflow the norm and produce a non-unit result. Max-component scaling now
handles finite nonzero extremes with documented rounding. Relative components
can round to signed zero, and normalization bits can differ from 0.0.1.
This is not a claim of greater accuracy or correctly rounded normalization.
All-zero inputs return `ZeroNormQuaternion`; non-finite inputs return `NonFinite`.
Equality compares components, not rotation equivalence (`q` and `-q` can differ).

Neither error enum is `non_exhaustive`. Update exhaustive matches; for example:

```rust
use spatial_typestate::SpatialError;
fn category(error: SpatialError) -> &'static str {
    match error {
        SpatialError::NonFinite => "numeric input/result",
        SpatialError::ZeroNormQuaternion => "zero quaternion",
        SpatialError::NonRigidTransform => "inverse requires a proper rigid matrix",
        SpatialError::InvalidUnitScale => "invalid length-unit metadata",
        SpatialError::UnrepresentableUnitConversion => "scale ratio cannot be represented",
    }
}
fn main() { assert_eq!(category(SpatialError::NonFinite), "numeric input/result"); }
```

Raw point/vector components, scalar arithmetic and public transform matrices
remain unvalidated. Checked application validates only participating inputs and
results: raw bottom rows are ignored, as is translation for vectors. Finiteness
is not rigidity, dimensional algebra, calibration or certification. Sequential
mapping and composition have different intermediates and error/rounding behavior.
`try_inverse` checks affine/proper-orthonormal structure at absolute `1e-10`;
near-rigid acceptance is not an arbitrary-magnitude roundtrip guarantee.

Length conversion is explicit, with trusted positive finite `LinearLengthUnit`
metadata, then a positive finite representable scale ratio, then finite values
and results. Invalid metadata and unrepresentable ratios have distinct errors.
Transform conversion scales translation only, retaining rotation bits. Rounding
and component underflow are allowed; overflow fails. Extreme-ratio rescue,
offset conversions and general dimensional algebra are not provided.

The only current runtime features are `std` (default) and marker `no_std`.
Disable defaults for no-std; adding the marker alone does not turn off std.
Current runtime graphs have zero normal dependencies, unlike the old manifest's
typenum/num-traits/thiserror and optional backend dependencies. Standard builds
use native sqrt; no-std uses a private eight-step helper only on scaled norms
in `[1,4]`. Do not infer a general sqrt, universal timing or device-runtime claim.

## Python 0.1.0: first release candidate, not a published migration

There is no previous published Python package in the observed PyPI namespace.
The distribution name is `spatial-typestate`, the import is `spatial_typestate`,
and the extension is `spatial_typestate._native`. The private Cargo package is
`spatial-typestate-py` (`publish=false`), not another public Rust release.

- Frames use frozen process-local identity, not their names; two `Frame("World")`
  objects are different frames. Wrapper `is` is not identity equality. Keep and
  pass the same frame objects; identity is not serializable. Opaque classes reject
  copy/deepcopy/pickle. Stubs aid callers
  but cannot replace runtime frame/unit/kind checks or Rust's generics/lifetimes.
- Frozen point/vector batches own contiguous Rust float64 data. Import accepts
  only bare native `d`, itemsize 8, C-contiguous flat `3N` or `(N,3)` buffers;
  malformed/ambiguous shape, strides, dtype and prefixed/endian formats fail.
  Non-finite coordinates are rejected on import, earlier than Rust raw constructors.
- Import copies once while attached before Rust work detaches. A readonly view
  of mutable storage is not immutable: callers must exclude concurrent foreign/
  native writers during import. No atomic snapshot or borrowed-lifetime claim.
- First flat `view()` zero-fills and copies once to cached immutable bytes;
  repeated exports share the base. A viewed batch retains Vec plus bytes, about
  two payloads. A view survives batch deletion. No alignment or end-to-end
  zero-copy/speed-parity promise is made; there is no NumPy runtime dependency.
- Batch operations are all-or-nothing, reporting the first ascending zero-based
  failing row in `SpatialError.index`, with `code` and setup/frame/unit checks.
  Structural buffer/type errors can instead be TypeError, ValueError or BufferError;
  setup errors have no row index. Empty mapping does not eagerly validate unused
  raw matrix values. Units are
  closed runtime tags with explicit meter/foot conversion; generic custom-unit
  extension and compile-time frame rejection do not cross the Python boundary.
- Size arithmetic is checked before allocation, but host OOM can abort. The
  binding requires std and CPython; the core's no-std contract is independent.
- Tested wheels are GIL-enabled CPython 3.11/3.14 on Windows/Linux x86_64;
  metadata permits 3.12/3.13, neither is in CI (local Windows 3.12 is narrower
  evidence). Linux baseline is manylinux_2_28; glibc 2.28/2.36 containers on a
  runner kernel are not universal-host proof. No macOS, musl, other architecture,
  PyPy or free-threaded support is asserted.
- Use the private PEP 517 backend and installed development wheel/rebuild flow.
  Editable installs reject; direct maturin bypasses provenance gates. Rebuilds
  compile in a fresh staging tree. See the [Python guide](PYTHON-GUIDE.md).

Rust/Python versions evolve independently even though these candidates both say
0.1.0; native and pyproject versions must match. Wheels carry compiled core code,
not a dependency on an installed Rust crate. Source archives vendor the exact
path-dependent core. Backend provenance records actual source identity, versions,
lock hashes and build tools; source identity and a later wheel's compiler record
are distinct. Those records are unsigned, and equal source hashes do not imply
byte-identical binaries. Exact artifacts, hashes, platforms and publication still
need the separate [release gates](RELEASING.md).

## Validation record

Validated on 2026-11-08 with the explicit installed Rust 1.99.0 compiler,
two build workers, offline dependency resolution and locked build/run commands:

- Built the actual checksum-verified 0.0.1 archive's library and compiled/ran the
  old example against it. Its two-arm error match also compiled. The old
  normalization edge checks reproduced squared-norm underflow and overflow.
- Compiled/ran all three positive current examples in out-of-tree consumers,
  with both std and no-std core dependencies. Finite-extreme quaternion checks
  also passed in both configurations. The changed-return example failed with
  E0308 as intended; the old exhaustive error match failed with E0004.
- Parsed manifest/lock comparisons show only the core version and one self-package
  version entry per lock changed. Locked normal graphs show no core runtime
  dependency; the native dependency graph is unchanged apart from core identity.
  Python and native version manifests are byte-unchanged.
- Compiled/ran the exact README/rustdoc Git dependency snippet at
  `1b80c3d7aa930538eb29ce0107a6e5ec2523ea86`. Cargo resolved manifest 0.0.2 and
  the demonstrated core API, not candidate package identity 0.1.0.

These are source/example checks, not candidate artifact qualification. No manual
crate package, wheel/sdist candidate build, tag, upload or artifact signoff was
performed in step 1. Later artifact preparation needs an exact reviewed source
commit and the separate release gates.

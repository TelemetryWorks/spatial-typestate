# Python batch guide

The unreleased `spatial_typestate` Python package is a separate CPython extension
over the Rust core. It makes one object per batch, not one point/vector object
per row. No PyPI publication or prebuilt-wheel availability is promised.
The core remains dependency-free and no_std-capable; PyO3/build dependencies live
only in `python/native`, with their own lockfile. The binding uses std.

## Build and test locally

Use GIL-enabled CPython 3.11-3.14 and an installed Rust toolchain. The wheel uses
CPython's 3.11 stable ABI; that does not promise PyPy/free-threaded support.
Linux/Windows x86_64 package jobs test 3.11 and 3.14; local development uses 3.12.
Other platforms/source builds need their own validation. No platform wheels are
published by this task. Rust core pin/MSRV are unchanged.

```powershell
python -m venv target/python-venv
$env:PATH = (Resolve-Path target/python-venv/Scripts).Path + [IO.Path]::PathSeparator + $env:PATH
$env:RUSTUP_TOOLCHAIN = '1.99.0-x86_64-pc-windows-msvc'
$env:CARGO_BUILD_JOBS = '2'
python -m pip install --require-hashes --only-binary=:all: -r python/requirements-build.txt
python -m maturin build --manifest-path python/native/Cargo.toml --release --locked --jobs 2 --out target/python-wheels
python -m pip install --no-deps target/python-wheels/spatial_typestate-0.1.0-cp311-abi3-win_amd64.whl
python -I -m unittest discover -s python/tests -v
```

Use the actual emitted wheel filename on Linux. Hash-locked build requirements
cover x86_64 Windows/Linux; other platforms require reviewed hashes/tooling.
The optional `python/requirements-interop.txt` installs test-only NumPy in this
venv; it is not a runtime requirement. Tests run against the installed wheel,
not `python/src`. The source distribution vendors the core path dependency;
CI also builds/installs it on Linux and runs the same tests. This uses
--no-build-isolation and the already hash-locked maturin; ordinary isolated builds
resolve the exact maturin==1.16.0 requirement in pyproject.toml (without the CI
hash file unless the caller supplies it). Native parity tests:

```powershell
$env:PYO3_PYTHON = (Get-Command python).Source
cargo +1.99.0-x86_64-pc-windows-msvc test --manifest-path python/native/Cargo.toml --locked --jobs 2
cargo +1.99.0-x86_64-pc-windows-msvc clippy --manifest-path python/native/Cargo.toml --locked --all-targets --jobs 2 -- -D warnings
cargo +1.99.0-x86_64-pc-windows-msvc fmt --manifest-path python/native/Cargo.toml -- --check
```

## Sensor -> aircraft -> world

```python
from array import array
from spatial_typestate import Frame, Points, Quaternion, Transform, METERS, FEET

sensor, aircraft, world = Frame("Sensor"), Frame("Aircraft"), Frame("World")
sensor_aircraft = Transform.from_rotation_translation(
    sensor, aircraft, METERS, Quaternion(aircraft, 0., 0., 1., 1.), (10., 20., 30.))
aircraft_world = Transform.from_rotation_translation(
    aircraft, world, METERS, Quaternion(world, 1., 1., 0., 0.), (1., -2., 3.))
points = Points.from_buffer(array("d", [2., 3., 4.]), sensor, METERS)
mapping = sensor_aircraft.then(aircraft_world)
result = mapping.apply_points(points)
assert all(abs(a-b) < 1e-10 for a, b in zip(result.view(), [23., 5., -31.]))
restored = mapping.inverse().apply_points(result)
assert all(abs(a-b) < 1e-10 for a, b in zip(restored.view(), points.view()))
feet_result = mapping.convert_to(FEET).apply_points(points.convert_to(FEET))
assert feet_result.unit == FEET
```

The installed-wheel analytic test exercises this exact setup. Quaternion components
are Hamilton (x,y,z,w); checked normalization handles finite nonzero extreme inputs.
Its frame must equal the transform target. The caller still asserts the physical
source/target relationship. `then(next)` means next(first(point)). `inverse()` is
the core's checked rigid inverse, not a general matrix inverse; its absolute
1e-10 validation tolerance does not imply a magnitude-independent roundtrip bound.

Frames have identity, not name equality. Two `Frame("World")` calls create
DIFFERENT frames. Keep/share the original object. Metadata getters can return new
Python wrappers, so use `batch.frame == frame`, not `is`; hashing uses the same
underlying identity. Frames and the other opaque values reject copy/deepcopy/
pickle; identity is process-local. Classes are frozen and cannot be subclassed.
There are no setters, row relabel operations or string-based identity registries.

Points and transform translations require explicit `METERS` or international
`FEET` (one foot is exactly 0.3048 m by definition; floats still round). No implicit
conversion occurs. `convert_to` preserves frames; transform conversion scales
translation only, preserves linear coefficient bits and canonicalizes the bottom.
Same-unit finite component bits survive, including signed zeros; underflow and
rounding are allowed, while overflow is an error. Arbitrary extreme-ratio rescue,
offset units, angles and dimensional algebra are not included.

`Vectors.from_buffer` accepts lengths or `DIMENSIONLESS`; `apply_vectors` preserves
its unit independently of the transform's translation unit and omits translation.
Only these three built-in tags exist; Rust's custom unit/velocity markers are not
exported. Numeric linear coefficients are assumed dimensionless for unit meaning.

## Buffers, ownership and views

Input must expose a direct C-contiguous float64 buffer with itemsize 8 and
**exact unprefixed native format `d`**, shaped (N,3) or flat 3*N. Flat buffers are
provided for stdlib `array('d')` and empty batches; len%3!=0 is rejected. Other
rank/shape/strides/dtypes/endian encodings, including `@d`, ctypes `<d` and
opposite-endian doubles, are rejected rather than converted. Nonempty input must
meet PyO3's alignment check; unaligned NumPy input is rejected. Empty Nx3 NumPy
buffers work without element reads. No list/tuple-of-rows fallback is provided.

The buffer is copied once into a private Rust Vec while attached to Python, then
the foreign buffer is dropped. A read-only view of mutable backing storage is
still copied. **The caller must stop native/external writers during import.**
The GIL cannot freeze native producers; importing an actively changing buffer is
not an atomic/coherent snapshot. After import, caller mutations cannot affect it.
Detached work touches only immutable Rust-owned data and produces a new private
Vec. Every row invokes existing checked core math; no Python callbacks, PyFloat,
row tuple/dict or per-row Python wrapper is built in the numeric loop.

`batch.view()` lazily exports one immutable bytes-backed flat native-double
memoryview. `batch.shape` is (N,3), including N=0. CPython cannot cast an empty
view to shape (0,3); its exported view is therefore flat (0,) too. For nonempty
batches use `view.cast('B').cast('d', shape=batch.shape)` to obtain 2D without
copying. NumPy can use `np.asarray(batch.view()).reshape(batch.shape)` without
an additional payload copy. No alignment guarantee is made for bytes exports;
a consumer requiring alignment may need a copy. The view's bytes base keeps
values alive after deleting the batch; it is not a borrowed Rust lifetime.

The first export uses safe `PyBytes::new_with`: one full payload serialization/
copy directly from Vec to bytes, plus PyO3's zero fill. No temporary Vec<u8> is
created. The bytes is cached per batch: repeated views reuse it without another
payload copy. A viewed batch retains BOTH its Vec and cached bytes (~2 payloads)
until dropped. The view can outlive the batch, retaining just bytes. Application
allocates a new output Vec; constructing per-row stack core values adds no whole-
payload copy. No Vec-to-Arc or intermediate output collection copy is used.

For source array -> import -> apply -> view while retaining all batches, live
payloads include the source array, imported Vec, output Vec and exported bytes:
roughly 4 * N * 3 * 8 bytes, plus metadata/capacity/allocator overhead. A view of
the input adds another cached payload. The binding is NOT end-to-end zero copy.
Sizes are checked for address-space overflow before allocation; host OOM may
still abort and is not universally a recoverable Python exception.

## Errors, empty batches and raw transforms

`SpatialError` derives from `ValueError` with `code` and `index` attributes.
Core codes are NonFinite, ZeroNormQuaternion, NonRigidTransform, InvalidUnitScale
and UnrepresentableUnitConversion (the latter two are not normally reachable
with this closed valid unit set). FrameMismatch/UnitMismatch cover metadata.
Wrong batch kinds/non-length units raise TypeError. Malformed buffers/setup use
TypeError, ValueError or BufferError. Exception attributes are informational;
mutating one cannot relabel a batch or bypass validation.

Metadata is checked first. An operation returns a whole new batch or raises at
the first failing row, ascending, zero-based `index`; non-row errors have None.
No output buffer argument, partial result, NaN sentinel or output mutation exists.
A failed call leaves input intact. Import rejects nonfinite coordinates earlier
than Rust's raw Point3/Vector3 constructors; this is deliberate binding behavior.
Finite input can still overflow during checked math/conversion.

`Transform.from_matrix(source,target,unit,matrix)` is explicitly raw setup,
with row storage, column-vector multiplication and translation in the last column.
It is frozen but unvalidated. Point mapping ignores the bottom row; vector mapping
also ignores translation, including nonfinite ignored values. Finite scale/shear
maps are accepted by application; finiteness is not rigidity/calibration. Core
inverse checks all entries/affine row/rotation/determinant; composition/conversion
use their own documented scopes. Successful arithmetic keeps core association,
including signed-zero/subnormal behavior and conservative intermediate-overflow
errors. No fast-math or experimental prepared-map optimization is introduced.

Empty applications check metadata but have no row on which to call core math:
they succeed even for a nonfinite raw matrix. This is not eager preparation.
Compose/inverse/transform conversion always run their core operation regardless
of whether a caller later maps zero points. Signals may wait until a detached
batch finishes; no cancellation or per-row Python signal callback is promised.

## What Python does not preserve

| Rust facility | Python contract / cost |
| --- | --- |
| Compile-time frame/unit rejection | Immutable runtime identity/tags checked on calls; stubs are hints, not proofs. |
| Arbitrary generic/custom markers | Closed meter/foot/dimensionless subset; no custom scale declarations/registry. |
| Lifetimes and zero-sized tags | Owned Rust buffers and runtime metadata; no Rust borrow capability crosses FFI. |
| no_std and embedded execution | Binding needs std + CPython/platform extension; core remains unchanged. |
| Raw nonfinite values until operation | Import rejects them immediately with row index. |
| Fixed-size allocation-free math | Batch/FFI storage allocates; copies, capacity and OOM limits apply. |
| Native call latency | FFI/import/export/metadata overhead; no native parity, all-host speed or timing guarantee. |
| Physical truth | Still caller-declared frames/calibration and dimensionless raw coefficients; no certification. |

See [the reviewed design](python_design.md), [math limits](math_conventions.md),
[units](units.md) and [requirements/evidence](requirements/requirements.md).
[Measurements and their limits](python/2026-11-03/README.md) are recorded separately;
they are not a CI timing gate.

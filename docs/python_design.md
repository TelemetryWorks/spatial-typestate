# Python batch binding: bounded first increment

Status: reviewed bounded design; implementation evidence follows in the Python guide.
The Rust core, its public API, lockfile, runtime dependency graph, no_std path,
pin and MSRV remain unchanged. No package publication or release is assigned.

## Architecture and dependencies

Use a separate `python/native` publish=false cdylib with its own Cargo.lock,
path dependency on the core and PyO3 0.29.2. Use a thin `python/src/spatial_typestate`
facade/stubs with no Python runtime dependencies; maturin 1.x is a project-local
build dependency. Build with explicit installed Rust 1.99 and two workers.
Target ordinary GIL-enabled CPython 3.11-3.14 using abi3-py311 (buffer ABI floor);
local validation uses installed 3.12. No free-threaded, PyPy or device support claim.
Own release profile: opt-level=3, thin LTO, one codegen unit, unwind (FFI panic
handling remains PyO3's responsibility). No handwritten unsafe in the binding.

Reference inspected live at [aero1553@759ebd4](https://github.com/joey-huckabee/aero1553/tree/759ebd432e5f8048cbccb10f6f80fdbd3edd436a):
python/native/Cargo.toml, src/lib.rs, table.rs, stream.rs, python/pyproject.toml,
docs/PYTHON-GUIDE.md and thin Python entry/table modules. Reuse separation,
owned Rust work and immutable bytes exports, not the reference's decoder classes.

## Bounded public workflow

- `Frame(name)`: frozen, distinct identity per construction. Equal names do not
  imply equal frames. Share the same Frame instance for a shared coordinate system.
  Rust-held Arc identity survives Python wrapper lifetimes; no global name registry.
  Equality/hash use Arc allocation identity, not wrapper identity or the name. Getters
  may return another wrapper that compares equal. Copy/deepcopy/pickling are rejected;
  identity is process-local and not a serialization contract.
- Frozen `Unit` values `METERS`, `FEET`, `DIMENSIONLESS`; closed built-in subset.
  Points and transforms require a length unit; vectors accept all three.
- `Points.from_buffer(buffer, frame, unit)` and `Vectors.from_buffer(...)`:
  immutable Rust-owned contiguous float64 triples, one object per batch. Accept
  C-contiguous native `d` buffers shaped (N,3), plus flat 3*N buffers (including
  empty) for stdlib array interop. Reject other formats/itemsize/strides/endian/
  dimensions/shape. No list-of-tuples fallback or row objects/iteration API.
- `Quaternion(frame,x,y,z,w)`: checked core normalization, frozen read-only values.
- `Transform.from_rotation_translation(source,target,unit,rotation,translation)`:
  rotation must have target identity; translation is a fixed three-value setup
  parameter in the declared length unit. Source relationship remains caller-asserted.
- `Transform.from_matrix(source,target,unit,matrix)`: explicit raw unvalidated
  4x4 setup path, retaining the core's finite/ignored-entry behavior at operation.
- `apply_points`, `apply_vectors`, `then`, `inverse`, `convert_to` delegate to
  existing checked core operations. Point/translation/composition length matches;
  inverse retains units; vector unit survives rotation independently of translation.
  Batch and transform meter/foot conversion is explicit, core-backed. No Quantity
  wrapper, custom unit registry, relabel operation, prepared API or general batch API.

Internally runtime metadata is checked before marker-erased core calls. Closed
unit dispatch happens outside Rust row loops, constructing concrete core typed
values for each row; no duplicated matrix/quaternion/conversion formula. Immutable
metadata is enforced by frozen non-subclassable PyO3 classes with private fields.
Stubs help discoverability; they do not establish Rust-style compile-time proofs.

## Ownership, buffers, copies and concurrency

Use the safe PyO3 buffer acquisition/copy interface while attached. Validate the
buffer and copy once into owned Vec<f64>, then release every buffer borrow before
`py.detach`. Never access a foreign buffer from a detached loop. A read-only view
of a mutable exporter is still snapshotted. The caller must prevent concurrent
native/external mutation during import; holding the GIL does not synchronize
native producers. No coherent/atomic snapshot of an actively changing exporter
is promised. Support ordinary GIL CPython only in this increment.

Imported values are private immutable Vec<f64> storage (no Vec-to-Arc payload copy). Detached operations
borrow only immutable Rust-owned data and transforms; no callbacks, Python item
iteration, PyFloat/tuple/dict construction, locks or Python API in a row loop.
Returned batch storage is newly owned; input and output never alias. Python objects
are created after reattachment. Borrow lifetimes are not manufactured across FFI.

`batch.view()` returns a read-only native-double flat memoryview of immutable
PyBytes; `batch.shape == (N,3)` provides shape even when N=0 (CPython memoryview
cannot cast an empty view to a zero-shaped 2D view). Callers may reshape nonempty
views without copying. Bytes and views keep storage alive after deleting the batch.
Export uses PyO3 0.29.2's verified safe `PyBytes::new_with` initializer to write
native bytes directly: one payload serialization/copy into PyBytes plus the API's
zero initialization, no intermediate Vec<u8>. Cache that immutable PyBytes lazily
with PyOnceLock per batch; repeated views share the cached bytes and add no payload
copy. The first view holds both Vec and bytes, so a retained exported batch has
roughly two payloads. The view keeps bytes alive after deleting its batch.
No alignment promise: bytes payload alignment is not a Python buffer guarantee;
consumers may need an aligned copy. No unsafe casting/buffer implementation.
Check byte/count sizes against isize::MAX with checked arithmetic before allocations;
host OOM may still abort. Import rejects len%3!=0 and ambiguous shapes.

The [CPython buffer documentation](https://docs.python.org/3/c-api/buffer.html)
marks Py_buffer and its members as Stable ABI since Python 3.11.
Safe export initializer source is [PyO3 0.29.2 bytes.rs](https://github.com/PyO3/pyo3/blob/v0.29.2/src/types/bytes.rs).


## Errors and atomicity (proposed first contract)

All-or-nothing return, stop at first failing row in ascending order. New private
output is discarded on error; no partial result or user-provided output buffer.
A single `SpatialError(ValueError)` carries stable `code` and optional `index`.
Core errors retain their variant code; metadata mismatch uses FrameMismatch,
UnitMismatch; wrong batch kind uses TypeError. Malformed buffer/setup uses
TypeError/ValueError/BufferError (including PyO3 alignment rejection).
No Python error object per successful row. Row error index is zero based.

Validate metadata before row math. Import rejects nonfinite coordinates with
NonFinite/index; later core calls reject overflow. Raw matrix numerical checks
remain per existing core call, not new eager validation: empty application has
no participating row, so metadata is checked and an empty output is returned
without validating a raw matrix. Document this explicitly, not as preparation.
Composition/inverse/conversion follow existing core checks even for empty users.
For vector mapping translation/bottom remain ignored; points ignore bottom only.
No automatic scale conversion, silent masking, partial writes or NaN sentinels.

## Guarantees lost / limits

| Rust facility | Python binding |
| --- | --- |
| Compile-time frame/unit rejection | Immutable runtime identity/tags checked on calls; stubs are not proof. |
| Generic custom markers and unit metadata | Only meters, international feet and dimensionless vectors initially. |
| Borrow checker and zero-sized labels | Owned Rust data with per-batch metadata and FFI lifetimes; no exposed borrowed-map API. |
| no_std/embedded core | Binding requires std, CPython and platform wheels; core remains no_std capable. |
| Raw NaN coordinates accepted until operation | Python import rejects nonfinite coordinates immediately, with row index. |
| Fixed stack values/no allocation | Batches/FFI buffers allocate; host OOM not guaranteed to become a recoverable Python exception. |
| Native call cost | FFI, validation/import/export copies and allocation overhead; no automatic parity/speed claim. |
| Physical frame/calibration truth | Still caller assertions; labels do not verify calibration, dimensions of raw coefficients or sensor correctness. |

No general dimensional algebra/angles/custom registry, row indexing objects,
serialization identity, certification, end-to-end zero copy, simultaneous-write
snapshot guarantee, GPU or prepared-map production promotion.

## Acceptance and evidence plan

Native unit tests compare binding kernels directly against checked core calls,
including bit patterns/signed zero, both lengths/vector units, nonfinite/overflow,
raw ignored entries and extreme quaternions. Python stdlib unittest covers installed
wheel import/stubs, analytic sensor-aircraft-world workflow, explicit conversions,
identity/name collisions, wrong kind/unit/frame, frozen metadata, first-row index/
atomicity, zero rows, format/shape/stride/endian rejection, alias independence,
view lifetime/read-only storage and concurrent calls on immutable batches.
Successful loops produce no per-row Python values by source inspection and
batch object/memory measurements, not an unsupported universal allocator proof.

Build/install a release wheel in a local venv and test outside the source tree.
Add Linux/Windows wheel build/import/runtime CI without changing core gates;
run core default/no_std/all-features suites once after final edits. Clippy/fmt
for binding separately and unchanged core graph/pin/MSRV evidence. Measure bounded
setup/import, owned-batch apply, export and end-to-end latency across batch sizes,
repeat/spikes and peak process memory; compare Python scalar workflow as context,
not as a core parity claim. Coordinate quiet timing separately. No timing gate.

Wheel CI pins setup-python/checkout/toolchain actions and hashes the pinned local build requirement. New Python code is included in returned external checks; no exclusion of Sonar gates.

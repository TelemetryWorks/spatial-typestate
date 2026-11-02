# Safety and correctness notes

This library provides numeric and type-level contracts, not certification,
physical calibration, or proof of application safety. The authoritative
[requirements/evidence table](requirements/requirements.md) distinguishes
implemented checks, unchecked compatibility behavior, and documented limits.

## Frame and unit labels

Frame labels constrain function inputs/outputs. Manual traits on Point3,
Vector3, Transform and UnitQuat do not require derives on marker structs; Debug
retains phantom labels without storing marker values. Types cannot verify that
coordinates or transformations describe their claimed physical frames.
Quantity<U> only adds/subtracts matching units; its value is public. Points,
vectors, and translations still store raw f64 without dimensional units.

## Quaternion validity

Private components and removal of unchecked construction preserve the checked
normalization boundary. All finite nonzero components, including MAX and
subnormals, are accepted; any non-finite component or signed all-zero input is
rejected. Max-absolute scaling bounds the squared norm to [1,4]. Normalized
components are finite, with unit length within rounding error; tiny relative
components can round to signed zero. Const getters/identity are read-only.
Equality is component equality, not equivalence under the antipodal q/-q rotation.

Std builds retain native sqrt. No-std builds use a private eight-step Newton
helper with no new dependency. See [convergence and tolerances](math_conventions.md).
Tests compare boundaries/adjacent values, 100,001 dense values and 100,000 sampled
bit patterns to a test-only native sqrt reference. Error/residual allowances
are 4*EPSILON and 8*EPSILON relative; complete normalized squared-norm checks
allow 32*EPSILON. These are regression allowances, not a correctly-rounded sqrt
claim. Linking std as a test reference does not enable the library's std feature.

## Rigid workflow and raw compatibility

Checked rotation/translation construction uses right-handed active Hamilton
(x,y,z,w) algebra with p_To=R*p_From+t_To. R columns are source basis vectors in
To, and t is source origin in To. UnitQuat<To> does not label From; the caller
asserts the physical relationship. A finite target translation is required.

Raw matrices remain public/unvalidated. Point application and composition use
the affine mapping defined by their first three rows and ignore bottom rows;
there is no perspective division. Composition order is next(first(p)); vectors
receive no translation. These methods are unchecked and may overflow or yield
NaN for general inputs. Pure finite translations can overflow to signed infinity
but cannot yield NaN under ordinary IEEE 754 arithmetic. The compatibility helper
checks exact per-axis expected sums, including infinity sign (zero signs compare
numerically equal); it is not a configured or continuous cargo-fuzz setup.

Checked inversion rejects all non-finite entries and finite matrices failing
an affine-row, rotation-row orthonormality, or determinant +1 check, each with
absolute tolerance 1e-10. Output is R^T,-R^T*t with canonical bottom row;
non-finite output/intermediate translation overflow returns NonFinite. Scaling,
shear, reflection and projective inputs are not silently transposed as inverses.
Proper 180-degree rotations are accepted. Near-rigid inputs within tolerance are
accepted, so error scales with input magnitude and long-chain drift. No uniform
absolute roundtrip bound exists. Bounded properties use point range [-100,100],
translation range [-1000,1000], and absolute 1e-9 roundtrip/composition tolerance.

## Errors, allocation, and unsafe code

SpatialError is an exhaustive concrete enum implementing Display/core Error.
NonRigidTransform is an API addition: downstream exhaustive matches must adapt.
Constructors/math use stack values, no allocation, boxing, formatting, virtual
error calls, global state or I/O. Callers may format errors or choose Box<dyn
Error>; tests exercise both. Source review and #![deny(unsafe_code)] enforce the
library constraint, not downstream code. No measured speed or timing guarantee
is claimed. There are no normal dependencies in any runtime feature configuration;
dev-only testing tools remain separate. No libm or backend switch is retained.

## Validation limits

See [CONTRIBUTING.md](../CONTRIBUTING.md) for exact checks and CI scope. Independent
analytic axis/rational rotation oracles, noncommuting composition, invalid raw
inverse cases, 1,024 bounded workflow samples, extreme quaternions, bare markers,
and reviewed compile-fail fixtures provide regression evidence, not formal proof.
Runtime suites exercise std/no-std/all-features on the host. MSRV/pin and target
checks are compile-only unless explicitly stated; wasm/thumb/MUSL compilation
does not prove embedded execution, timing, calibration, or certification.

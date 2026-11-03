# Design

The crate has no normal dependencies. Its core is fixed-size f64 values with
PhantomData labels: Frame, Point3<F,L>, Vector3<F,U>, Transform<From,To,L>, and
UnitQuat<F>. Manual Copy/Clone/Debug/PartialEq implementations depend only on
stored numeric values, not traits on the frame or unit markers. Debug retains phantom
frame information; equality is component equality, including for quaternions.

UnitQuat has private components and checked normalization; identity and const
getters preserve that boundary. Standard builds use native sqrt; no-std uses
the private bounded Newton helper described in [math conventions](math_conventions.md).
Quantity<U> is a scalar unit tag sharing checked linear-length conversion with
points/vectors/transforms; its arithmetic remains unchecked. Required length
parameters have no default. Translation and point/composition lengths match;
rotation is dimensionless, and vector mapping preserves any unit independently
of transform translation. See [unit decisions](units.md) for metadata, rounding,
conservative failures, raw escape hatches and custom-declaration trust boundaries.

The useful rigid workflow is:

1. Normalize a target-frame Hamilton quaternion.
2. Construct Transform<From,To,L> from that quaternion and target-frame translation.
3. Apply points (R*p+t), vectors (R*v), or compose with then(next).
4. Request checked try_inverse() when the reverse mapping is needed.

The frame relationship is asserted by the caller. UnitQuat<To> does not encode
From, and types cannot verify a physical calibration. The checked constructor
produces a proper rigid affine matrix within floating-point rounding. Public
matrix storage and from_matrix deliberately remain an unchecked compatibility
path. Application and composition return Result, checking participating inputs
and computed outputs for finiteness without checking rigidity. Existing method
names are retained; callers propagate failures with ?. Inversion additionally
validates raw rigidity with absolute tolerance 1e-10.

Errors are concrete enum values implementing Display and core::error::Error.
Library math uses no allocation, boxing, unsafe code, global state, or I/O.
Formatting/boxing occurs only if the caller requests it. This is a code-level
constraint, not certification or a measured timing guarantee.

See [requirements and evidence](requirements/requirements.md),
[frame semantics](frames.md), and [coordinate interpretation](coordinate_systems.md).

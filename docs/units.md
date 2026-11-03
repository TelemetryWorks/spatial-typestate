# Explicit units and conversion decisions

`Point3<F,L:LengthUnit>` and `Transform<From,To,L:LengthUnit>` require a length
tag. `Vector3<F,U:Unit>` requires a unit tag, which may be length, Dimensionless,
or an opaque application unit such as velocity. There is no default Meters or
unspecified unit. This is an intentional breaking migration: choose the actual
unit of old numeric values, rather than silently interpreting them as meters.

Point application accepts and returns the transform's length unit. Checked
rotation/translation construction takes `Vector3<To,L>`. Composition requires
the same length on both transforms, and inversion retains it. UnitQuat is
dimensionless. `apply_vector<U>` preserves any U independently of translation
unit L; only the linear coefficients participate. They must be dimensionless
for this interpretation to be correct. Types cannot inspect the physical units
of raw matrix entries.

## Explicit linear length conversion

Meters and international Feet implement `LinearLengthUnit`. One international
foot is exactly 0.3048 meter by definition, distinct from the historical U.S.
survey foot ([NIST definition](https://www.nist.gov/pml/us-surveyfoot)). The f64
representation and arithmetic still round.

`convert_to::<V>()` returns Result and is shared by Quantity, Point3, length
Vector3, and Transform. It changes no frame. Transform conversion scales only
translation, copies the linear 3x3 bits unchanged, and emits bottom row
`[0,0,0,1]`. It represents the same physical mapping in a different length unit;
it does not create a map whose source and target use different units. It checks
all first-three-row entries for finiteness, but ignores the raw bottom row and
does not validate rigidity. Finite scale/shear remains allowed, interpreted as
dimensionless coefficients. Application/composition never convert implicitly.

The deliberately simple conversion algorithm is:

1. Validate both meters-per-unit declarations as positive finite f64 values.
2. Compute `factor = source_scale / target_scale` once; require a positive,
   finite result. Positive subnormal factors are allowed with potentially substantial relative
   precision loss; a rounded zero or
   infinity is rejected even if the input is zero or a rearrangement could work.
3. Require each participating component finite, multiply by factor, and require
   the result finite. Transform translation alone is multiplied.

Metadata is validated before numeric inputs. Invalid declarations return
`InvalidUnitScale`; an unrepresentable factor returns
`UnrepresentableUnitConversion`; non-finite inputs/results return `NonFinite`.
These are concrete SpatialError variants, without allocation or boxing. The enum
is exhaustive: add match arms for the new variants when migrating.

Finite same-unit components preserve their bits, including signed zero,
subnormals and MAX. Transform same-unit conversion still canonicalizes its
bottom row. Rounding and component underflow to signed zero are permitted.
Overflow returns an error; no rescaling, compensated arithmetic, ratio rescue,
or alternate evaluation order is attempted. No exact roundtrip, correctly rounded
conversion, all-extreme-ratio support, or universal accuracy bound is claimed.
The bounded roundtrip property uses values in [-1e6,1e6] and mixed allowance
`1e-11 + 32*EPSILON*abs(expected)`. Sampling is regression evidence, not proof.

## Custom units and trust boundaries

Unit and LengthUnit are open marker traits. An opaque custom length needs no
conversion metadata to be used in a point or transform. An opaque velocity or
direction unit needs only Unit to be rotated. No marker value traits are needed
for Copy/Clone/Debug/PartialEq on the numeric wrappers.

Custom linear lengths opt into `LinearLengthUnit: LengthUnit` and declare
`METERS_PER_UNIT`. Declarations must actually describe linear lengths. Numeric
validation can reject invalid scales, but cannot verify the claimed dimension,
calibration, linearity, or scale accuracy. A caller can lie by implementing
LengthUnit for an angle-like custom type; open extensibility is a trust boundary,
not dimensional inference. Built-in angles and Dimensionless are not lengths
and cannot use length conversion. Degrees/radians conversion is not implemented.

Raw Point3/Vector3/Quantity constructors and public numeric fields permit
unvalidated values and manual relabeling by reconstructing a value. Transform
from_matrix/public matrix and raw from_translation scalars assert units without
verifying them. Prefer the checked typed rotation/translation constructor for
an existing translation. Quantity's same-unit add/subtract is still ordinary
unchecked f64 arithmetic and can overflow. Unit tags do not establish a general
finite-value invariant or guarantee that a measurement has its declared unit.

This increment deliberately excludes dimensional multiplication/division,
offset units, angle/trigonometric conversion, arbitrary conversion registries,
quaternion source-frame redesign, and automatic conversion inside math. It adds
no dependencies or allocations and changes neither compiler policy nor release
version. Explicit required tags were chosen over legacy defaults or a second
parallel wrapper family; conservative factor validation keeps the implementation
small at the cost of rejecting some mathematically representable conversions.

See [requirements/evidence](requirements/requirements.md),
[matrix conventions](math_conventions.md), and [migration notes](../CHANGELOG.md).

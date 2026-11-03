# Matrix and floating-point conventions

Matrices are stored as `[[f64; 4]; 4]`, indexed `matrix[row][column]`.
`Transform<From, To>::apply_point` multiplies the first three rows by the column
vector `[x, y, z, 1]`, returning a `Point3<To>` from a `Point3<From>`:

```text
x' = matrix[0][0]*x + matrix[0][1]*y + matrix[0][2]*z + matrix[0][3]
y' = matrix[1][0]*x + matrix[1][1]*y + matrix[1][2]*z + matrix[1][3]
z' = matrix[2][0]*x + matrix[2][1]*y + matrix[2][2]*z + matrix[2][3]
```

Translation occupies the last column of the first three rows. For example,
this matrix maps coordinates `(2, 3, 4)` to `(7, 22, 34)`:

```text
 0  -1   0  10
 1   0   0  20
 0   0   1  30
 0   0   0   1
```

The runnable `Transform::from_matrix` API-doc example and the raw-matrix
integration test exercise this case. Affine inputs are expected to have bottom
row `[0, 0, 0, 1]`, but `apply_point` never reads that row or divides by a
computed homogeneous coordinate. `from_matrix` and public matrix mutations are
unvalidated: the type does not enforce affine/rigid structure, orthonormality,
or finite numeric inputs. It is not a general projective transform evaluator.

Storage alone fixes no global physical axes or units. The checked constructor
uses the right-handed active Hamilton quaternion formula below; raw matrices
remain caller-defined. Frame semantics/calibration are supplied by the application.

## Rigid workflow algebra

`try_from_rotation_translation(UnitQuat<To>, Vector3<To>)` constructs
`p_To = R(q) * p_From + t_To`, with Hamilton components `(x,y,z,w)`:

```text
R = [ 1-2(y²+z²)   2(xy-zw)      2(xz+yw)   ]
    [ 2(xy+zw)     1-2(x²+z²)    2(yz-xw)   ]
    [ 2(xz-yw)     2(yz+xw)      1-2(x²+y²) ]
```

Columns of R are source basis vectors expressed in To; t is the source origin
expressed in To. The quaternion's single target tag does not encode From; the
caller asserts that relationship. The constructor rejects non-finite translation.
It preserves a canonical bottom row and uses no trigonometric dependency.
Quaternions q and -q generate equivalent rotations but compare unequal when
their components differ: PartialEq is not rotation equivalence.

`first.then(next)` means `next(first(p))`: R = R_next*R_first and
t = R_next*t_first + t_next. It ignores both raw bottom rows and emits
`[0,0,0,1]`, matching apply_point's affine interpretation. Different evaluation
order introduces rounding, so sequential and composed results need not be bit-equal.
`apply_vector` uses R*v without translation. Application and composition return
Result under their existing names. Their used inputs and computed output must be
finite; raw bottom rows are ignored, as is translation during vector application.
This is a finiteness contract, not proof of rigidity or calibration.
Sequential application and composition have different intermediate calculations,
so a sequence can overflow even if its composed map succeeds (or conversely).

`try_inverse` first rejects any non-finite entry. Finite matrices must have
bottom row `[0,0,0,1]`, row dot products matching the identity, and det(R)=+1,
each within absolute tolerance 1e-10. This accepts proper 180-degree rotations
and rejects scaling, shear, reflection, and projective input beyond tolerance.
It returns R^T and -R^T*t with a canonical bottom row, and rejects non-finite
output (including intermediate translation overflow) with NonFinite. Finite
validation failures return NonRigidTransform. This is not a general matrix inverse.

Tolerance admits near-rigid raw inputs, not exact orthogonality. Error scales
with coordinate and translation magnitude and may accumulate over long chains.
The bounded workflow property uses points in [-100,100] and translations in
[-1000,1000], allowing absolute 1e-9 roundtrip/composition error. No uniform
absolute roundtrip bound is claimed for unbounded inputs or long chains.

Arithmetic retains the existing ordinary `f64` evaluation order. Non-finite
participating inputs or computed results return SpatialError::NonFinite. Finite
inputs do not guarantee success: intermediate multiplication/addition can
overflow, even if differently ordered real-number arithmetic would cancel it.
No compensated arithmetic, saturation or clamping is introduced. Raw constructors
and public fields remain unvalidated; no finite-value type invariant is implied.

For pure translation and finite inputs, zero/one products and a finite-plus-finite
addition cannot produce NaN, but can overflow. The compatibility helper verifies
exact finite per-axis sums (zero signs compare numerically equal) or NonFinite
for invalid input/overflow. General affine maps can produce non-finite results
through products and cancellation too; those are also errors.

## No-std quaternion norm

After max-component scaling, each component has magnitude at most one and at
least one has magnitude one. The squared norm `s` is therefore in `[1, 4]`.
Standard builds use native `s.sqrt()`. Without `std`, a private helper starts
at `a = 2` and takes eight fixed Newton steps, written as
`a -= 0.5 * (a - s / a)`. It is used only for this bounded norm; no public
square-root API is introduced and no allocation or unsafe code is needed.

In exact arithmetic the initial relative error `e = a / sqrt(s) - 1` lies in
`[0, 1]` and follows `e_next = e^2 / (2 * (1 + e))`. Successive upper bounds
are `1/4`, `1/40`, `1/3280`, about `4.65e-8`, `1.08e-15`, and `5.9e-31` after
six steps. Eight steps provide room for rounding to settle. This convergence
argument does not assert that finite-precision results are IEEE correctly rounded
or identical to native sqrt. Helper tests allow relative error `4 * f64::EPSILON`
against native sqrt and relative squared residual `8 * f64::EPSILON`; complete
normalization tests use squared-norm tolerance `32 * f64::EPSILON` to also allow
scaling, division, and summation rounding.

Tests check boundaries and adjacent representable values, 100,001 evenly spaced
values, and 100,000 reproducibly randomized bit patterns in the interval. The
no-std library path is also exercised by extreme-value quaternion regressions
and 1,024 finite-bit-pattern samples per property-test run. Unit tests link std
only as a native sqrt reference; this does not enable the library's std feature.
Sampling and comparison are regression evidence, not an exhaustive proof.

The no-std helper has fixed iteration count but may be slower than native sqrt;
no benchmark or timing guarantee is claimed. It avoids adding libm. All runtime
feature configurations have no normal dependencies. Previously advertised unused
nalgebra/glam switches were removed; no backend implementation existed to replace.

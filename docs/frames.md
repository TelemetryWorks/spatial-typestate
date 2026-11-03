# Frame labels

A frame is an application-defined type implementing the empty Frame: 'static
trait. Recommended labels are bare zero-sized structs; no derives are required:

```rust
use spatial_typestate::Frame;
struct Sensor;
struct Aircraft;
struct World;
impl Frame for Sensor {}
impl Frame for Aircraft {}
impl Frame for World {}
```

The spatial_frames! macro is optional convenience. Point3<F,L> and Vector3<F,U>
carry one label; Transform<From,To,L> constrains input and output labels.
PhantomData stores no marker value. Copy/Clone/Debug/PartialEq do not require
marker implementations of those traits. Different labels remain distinct even
when the coordinate values are numerically identical.

Transform<Sensor, Aircraft, Meters>.then(Transform<Aircraft, World, Meters>) gives
Result with Transform<Sensor, World, Meters> on success. Application and composition
require handling possible NonFinite errors. Applying a World vector to a Sensor-input transform
or composing mismatched intermediate frames fails to compile. Private quaternion
components prevent mutation around normalization; no unchecked constructor exists.

UnitQuat<To> describes numeric orientation using target-frame coordinates. It
has no source-frame parameter, so the caller supplies the intended From->To
relationship when constructing a transform. A type-correct relationship can
still be physically wrong: the library does not measure or validate calibration.

Length/unit tags are separate from frame labels. Point application and composition
also require matching lengths; vector rotation preserves U even when it differs
from transform translation L. No default unit or implicit conversion is provided.
See [unit contracts and limitations](units.md). Physical calibration, custom
unit declarations and raw numeric relabeling remain caller responsibilities.

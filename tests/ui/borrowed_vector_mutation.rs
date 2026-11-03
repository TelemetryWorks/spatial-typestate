#[allow(dead_code)]
#[path = "../../benches/support/borrowed.rs"]
mod borrowed;
use spatial_typestate::{Dimensionless, Frame, Meters, Transform, Vector3};
struct World;
impl Frame for World {}
fn main() {
    let mut map = Transform::<World, World, Meters>::identity();
    let prepared = borrowed::BorrowedVector::prepare(&map).unwrap();
    map.matrix[0][3] = f64::NAN;
    assert!(map.matrix[0][3].is_nan());
    let _ = prepared.apply_vector(Vector3::<World, Dimensionless>::new(1.0, 2.0, 3.0));
}

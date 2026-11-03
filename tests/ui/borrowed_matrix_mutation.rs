// Other prototype operations are unused in this focused rejection fixture.
#[allow(dead_code)]
#[path = "../../benches/support/borrowed.rs"]
mod borrowed;
use spatial_typestate::{Frame, Meters, Point3, Transform};
struct World;
impl Frame for World {}
fn main() {
    let mut map = Transform::<World, World, Meters>::identity();
    let prepared = borrowed::BorrowedPoint::prepare(&map).unwrap();
    map.matrix[0][0] = f64::NAN;
    assert!(map.matrix[0][0].is_nan());
    let _ = prepared.apply_point(Point3::new(1.0, 2.0, 3.0));
}

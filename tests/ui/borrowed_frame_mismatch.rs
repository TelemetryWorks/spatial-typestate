#[allow(dead_code)]
#[path = "../../benches/support/borrowed.rs"]
mod borrowed;
use spatial_typestate::{Frame, Meters, Point3, Transform};
struct Sensor;
struct World;
impl Frame for Sensor {}
impl Frame for World {}
fn main() {
    let map = Transform::<Sensor, World, Meters>::identity();
    let prepared = borrowed::BorrowedPoint::prepare(&map).unwrap();
    let _ = prepared.apply_point(Point3::<World, Meters>::new(1.0, 2.0, 3.0));
}

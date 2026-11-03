#[allow(dead_code)]
#[path = "../../benches/support/borrowed.rs"]
mod borrowed;
use spatial_typestate::{Feet, Frame, Meters, Point3, Transform};
struct World;
impl Frame for World {}
fn main() {
    let map = Transform::<World, World, Meters>::identity();
    let prepared = borrowed::BorrowedPoint::prepare(&map).unwrap();
    let _ = prepared.apply_point(Point3::<World, Feet>::new(1.0, 2.0, 3.0));
}

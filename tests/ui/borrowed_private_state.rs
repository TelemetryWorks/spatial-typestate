#[allow(dead_code)]
#[path = "../../benches/support/borrowed.rs"]
mod borrowed;
use spatial_typestate::{Frame, Meters, Transform};
struct World;
impl Frame for World {}
fn main() {
    let map = Transform::<World, World, Meters>::identity();
    let prepared = borrowed::BorrowedPoint::prepare(&map).unwrap();
    let _ = prepared.map;
}

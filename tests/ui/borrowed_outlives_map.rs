#[allow(dead_code)]
#[path = "../../benches/support/borrowed.rs"]
mod borrowed;
use spatial_typestate::{Frame, Meters, Transform};
struct World;
impl Frame for World {}
fn escape<'a>() -> borrowed::BorrowedPoint<'a, World, World, Meters> {
    let map = Transform::identity();
    borrowed::BorrowedPoint::prepare(&map).unwrap()
}
fn main() { let _ = escape(); }

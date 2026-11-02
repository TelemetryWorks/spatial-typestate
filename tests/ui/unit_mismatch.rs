use spatial_typestate::{Meters, Quantity, Radians};
fn main() {
    let length = Quantity::<Meters>::new(1.0);
    let angle = Quantity::<Radians>::new(1.0);
    let _ = length + angle;
}

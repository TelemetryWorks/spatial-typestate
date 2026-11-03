use spatial_typestate::{Feet, Meters, Quantity};
fn main() {
    let _ = Quantity::<Meters>::new(1.0) + Quantity::<Feet>::new(1.0);
}

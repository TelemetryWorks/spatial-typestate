//! spatial-typestate
//! ==================
//!
//! A Rust library for **type-state enforced 3D coordinate systems**.
//!
//! # Motivation
//!
//! In many aerospace, robotics, and simulation systems, the same physical point
//! can be expressed in multiple coordinate frames (world, body, sensor, etc.).
//! Mixing up those frames can silently produce incorrect results and, in the
//! worst case, unsafe behavior.
//!
//! `spatial-typestate` encodes the **frame of reference** (and eventually
//! physical units) into the **type system**, so that many classes of mistakes
//! become **compile-time errors** instead of runtime surprises.
//!
//! # Design goals
//!
//! - **Compile-time frame safety**: it should be impossible to accidentally use
//!   a point in one frame as if it were in another frame without an explicit,
//!   checked conversion.
//! - **Minimal, explicit API**: no hidden implicit conversions; all frame
//!   changes go through a `Transform<From, To>` or an explicit constructor.
//! - **`no_std` friendly**: usable on embedded and bare-metal targets.
//! - **Auditable**: no `unsafe` in the public API. Any future `unsafe`
//!   blocks will be isolated and documented with explicit safety contracts.
//!
//! # Quick example
//!
//! ```rust
//! use spatial_typestate::{Frame, Point3, Transform};
//!
//! // Define two frames.
//! struct World;
//! struct Body;
//!
//! impl Frame for World {}
//! impl Frame for Body {}
//!
//! // A point in the body frame.
//! let p_body: Point3<Body> = Point3::new(1.0, 0.0, 0.0);
//!
//! // A transform from Body -> World.
//! let t_body_world: Transform<Body, World> = Transform::identity();
//!
//! // Safely convert to world frame.
//! let p_world = t_body_world.apply_point(p_body);
//! ```
//!
//! # Feature flags
//!
//! - `std` (default): enables integration with the Rust standard library.
//! - `no_std`: builds without `std`. Disable default features and enable this:
//!   ```toml
//!   spatial-typestate = { version = "0.1", default-features = false, features = ["no_std"] }
//!   ```
//! - `nalgebra`: (planned) use `nalgebra` as an underlying math backend.
//! - `glam`: (planned) use `glam` as an underlying math backend.

#![cfg_attr(not(feature = "std"), no_std)]
#![deny(unsafe_code)]
#![warn(
    missing_docs,
    missing_debug_implementations,
    rust_2018_idioms,
    clippy::all,
    clippy::pedantic
)]

pub mod errors;
pub mod frame;
pub mod macros;
pub mod point;
pub mod quaternion;
pub mod transform;
pub mod units;
pub mod vector;

// Re-export primary types for a clean public API.
pub use crate::errors::SpatialError;
pub use crate::frame::Frame;
pub use crate::point::Point3;
pub use crate::quaternion::UnitQuat;
pub use crate::transform::Transform;
pub use crate::units::{Degrees, Meters, Quantity, Radians, Unit};
pub use crate::vector::Vector3;

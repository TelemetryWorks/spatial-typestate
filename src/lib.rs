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
//! `spatial-typestate` encodes the **frame of reference** and explicit
//! length/vector units into the **type system**, so that many classes of mistakes
//! become **compile-time errors** instead of runtime surprises.
//!
//! # Design goals
//!
//! - **Compile-time frame safety**: it should be impossible to accidentally use
//!   a point in one frame as if it were in another frame without an explicit,
//!   checked conversion.
//! - **Minimal, explicit API**: no hidden implicit conversions; all frame
//!   changes go through a `Transform<From, To, Meters>` or an explicit constructor.
//! - **`no_std` friendly**: usable on embedded and bare-metal targets.
//! - **Auditable**: no `unsafe` in the public API. Any future `unsafe`
//!   blocks will be isolated and documented with explicit safety contracts.
//!
//! # Quick example
//!
//! ```rust
//! use spatial_typestate::{Meters, Frame, Point3, Transform};
//!
//! // Define two frames.
//! struct World;
//! struct Body;
//!
//! impl Frame for World {}
//! impl Frame for Body {}
//!
//! // A point in the body frame.
//! let p_body: Point3<Body, Meters> = Point3::<_, Meters>::new(1.0, 0.0, 0.0);
//!
//! // A transform from Body -> World.
//! let t_body_world: Transform<Body, World, Meters> = Transform::identity();
//!
//! // Safely convert to world frame.
//! let p_world = t_body_world.apply_point(p_body).unwrap();
//! ```
//!
//! # Feature flags
//!
//! - `std` (default): uses native square root for quaternion normalization.
//! - `no_std`: marker for builds without `std`. Disable default features.
//!   Published 0.1.0 is available from crates.io (checked 2026-11-09):
//!   ```toml
//!   spatial-typestate = { version = "0.1.0", default-features = false, features = ["no_std"] }
//!   ```
//!   Its source is tag `rust-v0.1.0` at
//!   `9974fd6a00521d631d6ff6e35d4aa936f6b624cf`.
//!   Historical validation used Git revision `1b80c3d7aa930538eb29ce0107a6e5ec2523ea86`,
//!   whose manifest says 0.0.2; it is not the published 0.1.0 package identity.
//!   The absence of `std` selects a private bounded Newton square root; the
//!   marker alone does not disable default features. No normal dependencies
//!   are enabled in any runtime feature configuration.
//!
//! These are the only runtime features. Previously unused optional backend
//! switches were removed; every runtime feature set has no normal dependencies.

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
pub use crate::units::{
    AngleUnit, Degrees, Dimensionless, Feet, LengthUnit, LinearLengthUnit, Meters, Quantity,
    Radians, Unit,
};
pub use crate::vector::Vector3;

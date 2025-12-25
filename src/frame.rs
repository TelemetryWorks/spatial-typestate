//! Frame definitions and traits.
//!
//! This module contains the [`Frame`] marker trait. You implement `Frame`
//! for zero-sized types that represent coordinate frames in your domain.
//!
//! ```rust
//! use spatial_typestate::Frame;
//!
//! struct World;
//! struct Body;
//! struct Sensor;
//!
//! impl Frame for World {}
//! impl Frame for Body {}
//! impl Frame for Sensor {}
//! ```

/// Marker trait for a coordinate frame.
///
/// Typical usage is to define zero-sized types representing frames in your
/// domain and implement `Frame` for them. The trait is intentionally empty:
/// all semantics are carried at the type level.
pub trait Frame: 'static {}

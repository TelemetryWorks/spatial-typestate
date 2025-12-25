//! Macros for ergonomic frame definitions.
//!
//! The [`spatial_frames!`] macro lets you declare multiple zero-sized frame
//! types and implement [`crate::Frame`] for each in one go.
//!
//! ```rust
//! use spatial_typestate::spatial_frames;
//!
//! spatial_frames! {
//!     World,
//!     Body,
//!     Sensor,
//! }
//! ```
//!
//! This expands roughly to:
//!
//! ```ignore
//! pub struct World;
//! impl spatial_typestate::Frame for World {}
//! // etc...
//! ```

/// Define one or more zero-sized frame types and implement [`Frame`] for them.
///
/// Each identifier becomes a `pub struct` with `Debug`, `Clone`, `Copy`,
/// `PartialEq`, and `Eq` derives, plus an implementation of [`crate::Frame`].
///
/// # Examples
///
/// ```rust
/// use spatial_typestate::spatial_frames;
///
/// spatial_frames! {
///     World,
///     Body,
///     Sensor,
/// }
/// ```
#[macro_export]
macro_rules! spatial_frames {
    ( $( $name:ident ),+ $(,)? ) => {
        $(
            #[derive(Debug, Clone, Copy, PartialEq, Eq)]
            pub struct $name;

            impl $crate::Frame for $name {}
        )+
    };
}

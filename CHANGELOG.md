# Changelog

## [Unreleased]

### Changed

- **Breaking:** `Transform::apply_point`, `apply_vector`, and `then` now return
  `Result<_, SpatialError>` under their existing names. Add `?` or explicit error
  handling to callers; no separate `try_` variants or unchecked alternatives are
  introduced. Participating non-finite inputs and computed overflow/NaN return
  `NonFinite`. Raw bottom rows remain ignored; vector application also ignores
  translation. Finiteness checks do not certify rigidity or calibration.
- Sequential application and composition validate different intermediates and
  can return errors at different stages. Evaluation order is retained without
  compensated arithmetic or clamping. The checks add work to every operation;
  no benchmark timing or zero-overhead claim is made.
- **Breaking:** UnitQuat components are private. Replace q.x/q.y/q.z/q.w reads
  with const x()/y()/z()/w() getters. Replace mutation or removed new_unchecked
  calls with try_from_components and handle its Result, or use const identity().
- **Breaking:** SpatialError adds NonRigidTransform. Add a match arm to downstream
  exhaustive matches. It reports finite raw matrices that fail checked inversion.
- Point3/Vector3/Transform/UnitQuat implement Copy/Clone/Debug/PartialEq without
  marker trait bounds. Debug retains phantom frame information; quaternion
  equality remains component equality, not q/-q rotation equivalence.

### Added

- Checked rotation/target-translation construction, typed then composition,
  translation-free apply_vector, and checked try_inverse. Existing raw matrix
  storage/construction and unchecked apply_point remain compatible.
- A complete sensor-aircraft-world example with analytic expected coordinates,
  composition, inverse, and vector verification, also using a no-std library.
- Hand-written Display/core Error, without allocation or dynamic dispatch in math.
- Numbered implemented requirements/evidence and actual design/frame/math docs;
  populated contributor guidance and a single canonical remaining-work roadmap.
- Direct read-only Linux/Windows runtime, lint/docs/release, dependency graph,
  MSRV/pin library, and thumb/MUSL compile-only CI gates. Actions are SHA-pinned;
  redundant old Clippy/Rustfmt workflows are consolidated. Service configs unchanged.

### Fixed

- Extreme quaternion normalization with max-component scaling, including finite
  MAX/subnormals. Reject any non-finite component and signed all-zero inputs.
  Approximate unit length and possible relative underflow are documented.
- No-std quaternion norm via a private eight-step bounded Newton approximation,
  with native sqrt retained for std, dense/native-reference and actual no-std tests.
  No correctly-rounded equivalence or timing guarantee is claimed.
- Matrix docs now specify row storage, column vectors, target-frame translation,
  ignored raw bottom row, checked versus unchecked behavior, and inverse tolerance.
- Translation compatibility assertions now check exact per-axis sums, including
  expected signed overflow; deterministic and sampled regressions were added.
- Existing unused imports, formatting/lint findings, and broken rustdoc links;
  reviewed compile-fail baselines and explicit marker/unit/frame regressions.
- Removed-constructor rejection uses a paired checked-success/compile-fail
  doctest rather than an E0599 wording snapshot, preserving the same contract
  on the pinned compiler and 1.99. Stable rustdoc verifies failure, not error code.

### Removed

- **Breaking:** unused nalgebra/glam features and optional dependency declarations
  (including implicit nalgebra_dep/glam_dep features). Remove those feature names
  from caller manifests/commands; use std or disable defaults for no-std. No
  backend runtime implementation existed to replace, and no backend was integrated.
- Unused direct thiserror/num-traits/typenum dependencies. Every runtime feature
  graph is now empty; dev tools still bring transitive num-traits. The lockfile
  only prunes unused packages/root edges; retained versions were not upgraded.
  No dependency or libm was added.

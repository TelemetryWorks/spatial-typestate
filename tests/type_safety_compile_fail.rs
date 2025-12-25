//! Compile-fail tests to ensure that frame mismatches are caught at compile time.
//!
//! These tests use the `trybuild` crate to compile small example programs that
//! are *expected* to fail. If they ever compile successfully, the test fails.

#[test]
fn frame_mismatch_does_not_compile() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/frame_mismatch.rs");
}

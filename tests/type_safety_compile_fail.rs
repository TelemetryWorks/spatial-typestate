//! Compile-fail tests for frame mismatches and quaternion invariant bypasses.
//!
//! These tests use the `trybuild` crate to compile small example programs that
//! are *expected* to fail. If they ever compile successfully, the test fails.

#[test]
fn frame_mismatch_does_not_compile() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/frame_mismatch.rs");
}

#[test]
fn quaternion_components_cannot_be_mutated() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/quaternion_components_private.rs");
}

#[test]
fn workflow_frame_mismatches_do_not_compile() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/composition_frame_mismatch.rs");
    t.compile_fail("tests/ui/vector_frame_mismatch.rs");
    t.compile_fail("tests/ui/unit_mismatch.rs");
}

#[test]
fn length_contract_mismatches_do_not_compile() {
    let t = trybuild::TestCases::new();
    t.compile_fail("tests/ui/point_length_mismatch.rs");
    t.compile_fail("tests/ui/translation_length_mismatch.rs");
    t.compile_fail("tests/ui/composition_length_mismatch.rs");
    t.compile_fail("tests/ui/length_arithmetic_mismatch.rs");
}

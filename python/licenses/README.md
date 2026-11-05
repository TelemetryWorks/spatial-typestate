# Locked dependency notices

License texts are copied from Cargo's checksum-verified sources for the exact
native Cargo.lock entries. inventory.json records crate version, registry/source,
archive checksum, SPDX expression, scope and normalized-LF license-text hashes.
The backend rejects drift against the lock and text hashes. No dependency was
added or upgraded to create these notices.

runtime means runtime-capable, including target-conditional crates; it does not
assert every listed crate is linked on every target. build-only includes proc
macros and their dependencies. Both groups are included conservatively. In
particular unicode-ident also requires Unicode-3.0 terms, and target-lexicon has
the LLVM exception; neither is silently reduced to MIT/Apache.

Actual compiler distribution Rust std/bundled-component notices are separate
_compiler_notices wheel resources, recorded by hash in provenance. They depend
on the compiler used to build that wheel, not the compiler that created an sdist.
This inventory is attribution evidence, not legal certification or an SBOM
attestation. Review/update it whenever the native lock changes.

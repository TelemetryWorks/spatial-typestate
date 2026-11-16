# Spatial Typestate vX.Y.Z

- Release date: YYYY-MM-DD
- Shared Rust/Python/native version: X.Y.Z (owner-selected)
- Tag: `vX.Y.Z`
- Reviewed source SHA: FULL_COMMIT_SHA
- Coordinated workflow run: RUN_URL

## Changes and migration

Summarize both Rust and Python changes from their last publications. Link the
one combined dated changelog section and any migration instructions. State the
actual supported/tested scope; no certification or universal-platform claim.

## Verification and assets

Before announcing completion, follow all three deployment approvals and public
checks in [RELEASING](../docs/RELEASING.md#coordinated-publisher-implementation-and-approvals).
Record the exact four artifact filenames/hashes: crate, Linux/Windows cp311-abi3
wheels and canonical Linux sdist. Both registries must serve the approved bytes.
Every Python file needs verified PyPI PEP 740 provenance and the expected UI
display; correct package metadata is a separate gate.

Retain the artifacts, source-graph CycloneDX SBOMs, GitHub provenance/SBOM bundles,
per-file PyPI provenance objects and converted publish bundles, release manifest,
runtime receipts, public verification records and external `SHA256SUMS`.
Link the documented online/offline verification paths. No SLSA level, complete
binary SBOM or Python bit-reproducibility claim is implied.

The workflow does not produce container images, GPG summaries or Cosign-key
signatures. Do not invent them. Historical 0.1.0 artifacts/tags remain unchanged
and do not gain retroactive attestations.

If either registry or a later evidence step fails, report an incomplete
coordinated release and its exact public state. No rerun publication, overwriting
accepted files, moving tags or token/local fallback.

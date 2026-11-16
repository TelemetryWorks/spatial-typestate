# Unified publisher implementation review — 2026-11-16

Owner assignment: 2026-11-15.

Scope: one workflow, release-only helpers/tests/tool lock and documentation,
based on main `5b34624acc7ffd1e1d36238f6a08e2e012bdd0fa`. No tag, package upload,
Release object, version, Cargo lock/dependency, pin/MSRV or settings mutation.
`publish-0.1.0.yml` is unchanged and remains retired/disabled.

## Model and deliberate differences

Read the irig106-types reference at `2899b30`, both
[workflow](https://github.com/TelemetryWorks/irig106-types/blob/2899b30/.github/workflows/trusted-publishing.yml)
and [approver/verification guidance](https://github.com/TelemetryWorks/irig106-types/blob/2899b30/docs/RELEASING.md).
Use the same SHA-pinned crates.io OIDC auth action and no-overwrite/draft-first
Release retention model. Here one `vX.Y.Z` releases both registries, with this
crate's explicit 1.99.0 checks and 1.85/1.91 compatibility policy, not the
reference's stable/serde/WASM matrix. No first unified version is chosen.

Read-only GitHub API inspection confirmed `crates-io` and `pypi` have required
owner review, no admin bypass, and only selected tag `v*`. This is observation,
not setup. Registry-side Trusted Publisher identity/Trusted-Publishing-only
configuration remains an independent owner prerequisite. The ordering and
partial-release recovery in RELEASING remain the proposal pending owner execution;
this PR implements its guarded sequence, not approval to run it.

## Local validation

- actionlint 1.7.12 workflow/expression validation and zizmor 1.32.0 regular
  persona offline/online audits pass. Shellcheck/pyflakes are not installed;
  optional integrations are not claimed.
- All nine direct action repository/version/SHA identities and pinned action
  metadata paths resolved via upstream APIs, including annotated tags. The
  short-lived auth output is used only by the single Cargo publish step. New
  attestation actions' subject/bundle interfaces and the official PyPA action's
  OIDC/PEP 740 interface were inspected.
- Nineteen focused finite fixture tests pass, covering tag/version/lock/source
  checks, exact canonical selection, runtime receipts, pre-install hashes,
  public metadata/partial state, signature-failure propagation and strict
  certificate claims, every-file proof retention, CLI wiring, and draft/no-
  overwrite asset behavior. The complete pipeline unittest suite passes
  (109 tests). No registry write, real package build or benchmark was run.
- Focused local branch coverage of the two release helpers is 97% combined (guard 98%, integrity 95%); this
  is fixture coverage, not proof of live publishing. Cryptographic verification
  boundaries are mocked to test failure propagation; no future release's actual
  certificate/attestation has been produced or verified. Separately, the actual
  pinned library verified a fresh public pypi-attestations 0.0.31 wheel against
  its real Integrity API proof (`pypi/pypi-attestations`, `release.yml`, `pypi`),
  and rejected a one-bit signature mutation. All nine required Fulcio certificate
  extension fields were present in the expected tag/commit form. This verifies
  the tool interface and primitive on upstream evidence, not this new publisher.
- Hash-locked pypi-attestations 0.0.31 dependencies installed in a private
  temporary verification environment, without global installs or runtime changes.
  Its real `verify`, `certificate_claims`, GitHub publisher and Bundle serialization
  interfaces match the helper. The existing coverage lock contains a host-specific
  hash unsuitable for this aarch64 machine, so local-only coverage used the same
  7.17.2 version's aarch64 distribution; no CI coverage lock was changed.
- LF, local documentation links, shell-example syntax, final scope and whitespace
  checks accompany the PR. Hosted exact-head CI is separate pending evidence.

The crate public metadata API returned HTTP 403 from this cloud host. No
absence/ownership claim is inferred from it. The implementation's Trusted
Publisher field names were checked against upstream crates.io
[`TrustpubData`](https://github.com/rust-lang/crates.io/blob/main/crates/crates_io_database/src/models/trustpub/data.rs)
(provider/repository/run_id/sha); registry failures block the workflow.
No upload was run to test propagation, metadata preservation or issuer behavior.

## Security and evidence boundaries

Builds/verification have only contents read and no secrets/OIDC. Publishing is
sequential, separately environment-gated and attempt-1-only; both versions must
be absent before either upload, and PyPI is checked again before its upload.
An accepted first upload is never retried to repair later evidence. Cargo's
before/after byte checks cannot undo an accepted mismatch; stop for owner review.
The third approval checks both registries and each PyPI Provenance UI display,
not only green steps, before the sole contents-write job retains assets.

Python candidates use the private backend and existing hash-locked build/interop
requirements; no maturin CLI bypass. Only Linux 3.11's wheel/sdist and Windows
3.11's wheel are selected. Linux has four same-hash runtime records and a Git-free
sdist rebuild; the selected Windows wheel is independently installed on both
3.11/3.14 outside the checkout. The source record, licences/metadata/RECORD/ELF
checks and compiled-source identity remain distinct from signature identity.

PEP 740 uses the PyPI Integrity API plus production certificate/transparency
verification and exact GitHub issuer/repository/workflow/ref/commit/hosted-runner
claims. API publisher/environment equality is also required. The environment
binding itself is an owner configuration/approval gate, not an invented X.509
claim. GitHub SLSA and SBOM bundles are separate additional evidence. SBOMs describe
source graphs including development/build components; no complete binary/OS SBOM,
code safety, SLSA level or Python bit-reproducibility is claimed.

No live tag route, environment approval, OIDC issuance, Cargo/PyPI upload,
attestation signing, public metadata correction or Release retention was executed.
Those remain gated runtime evidence for a separately authorized version/tag.
Published 0.1.0 bytes and its historical dual tags are untouched.

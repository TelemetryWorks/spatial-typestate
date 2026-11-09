# Versioning, compatibility and release gates

This policy separates candidate preparation from publication authorization.
Selecting metadata does not authorize artifacts, tags, uploads or new support.
An owner must assign those later steps and approve the exact artifacts/versions.
No release schedule is promised. The historical `publish-0.1.0.yml` workflow is
retired, disabled and forbidden for future use; no compliant future publisher is
configured or approved by this policy change.

## Mandatory future PyPI publishing policy

Owner decision (2026-11-08): **every future PyPI release/upload** must use OIDC
Trusted Publishing from a reviewed hosted GitHub Actions job **and** publish
PEP 740 publish attestations for every distribution file: all wheels and the
sdist. Trusted Publishing alone is insufficient: some providers authenticate
uploads without producing attestations. Local builds and qualification remain
allowed; API-token/password uploads, local `maturin upload`/`twine upload`, token
fallbacks and `attestations: false` are forbidden for future PyPI uploads. This
rule does not change the crates.io publishing policy.

Before any future upload:

1. Separately review and configure the PyPI Trusted Publisher for the exact
   repository `TelemetryWorks/spatial-typestate` and named workflow filename.
   Record its allowed ref and immutable publishing-tooling commit. If the
   publisher is environment-bound, the publish job must use that exact reviewed
   GitHub environment; record the binding (or its explicit absence). Missing or
   mismatched setup is a release blocker, not permission to use a token.
2. Use the official `pypa/gh-action-pypi-publish` action pinned to a reviewed full
   commit SHA, with `attestations: true`, no password/token inputs and no
   `skip-existing`. Grant `id-token: write` only to the single publish job, never
   top-level or to build/test jobs. Keep build/qualification separate from
   publishing and carry the approved per-file SHA256 manifest across jobs/runs.
3. Validate the exact artifact set, source commit, embedded source records and
   hashes before upload. Record the publishing workflow/ref/commit separately
   from the artifact source commit if they differ. An attestation-generation,
   signing or upload failure stops release; never retry via a token or silently
   omit a wheel or sdist's attestation.

After upload, before declaring completion or creating release tags:

- For **each** filename, fetch
  `https://pypi.org/integrity/<project>/<version>/<filename>/provenance` and retain
  its bundle. HTTP 404 means no provenance; any missing/invalid proof is a failed
  release requiring investigation, not a pass or permission to re-upload a file.
- Cryptographically verify each publish attestation, including its signing
  certificate and transparency evidence, using reviewed verification tooling.
  Require the GitHub Actions OIDC issuer `https://token.actions.githubusercontent.com`,
  exact repository, workflow filename, ref and publishing-tooling commit to match
  the reviewed identity. Require the attested subject filename and SHA256 to
  equal the approved manifest and freshly downloaded public file. Independently
  check the artifact's embedded source identity against the approved source
  commit; do not substitute a tooling commit for a different build source.
- Confirm each PyPI file page displays **Provenance** with the expected publisher,
  rather than **Without provenance**. Record URLs, hashes, identity and verified
  results for every wheel and sdist. The UI alone is not cryptographic proof.

Publish attestations identify which workflow published particular bytes; they do
not prove reproducible builds, review, source-to-binary equivalence or code safety.
Build provenance and the existing unsigned `_provenance.json` source/build record
are separate evidence. A missing Trusted Publisher/OIDC permission or any failed
attestation/verification gate must fail closed with no credential fallback.

Python 0.1.0 was uploaded locally with a token and has **no public attestations**.
Its embedded source record and matching hashes do not populate PyPI Provenance.
This historical release is not repaired by this policy: no re-upload or
retroactive attestation claim is permitted. See the
[0.1.0 publication record](publication-0.1.0.md).

Primary references: [Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/),
[producing attestations](https://docs.pypi.org/attestations/producing-attestations/),
[consuming attestations](https://docs.pypi.org/attestations/consuming-attestations/)
and the [Integrity API](https://docs.pypi.org/api/integrity/).

## Candidate decision (2026-11-08, step 1 only)

| Package | Selected candidate | State |
| --- | --- | --- |
| Rust `spatial-typestate` | 0.1.0 | New breaking compatibility line from published 0.0.1; replaces the unpublished 0.0.2 development metadata. |
| Python distribution `spatial-typestate` | 0.1.0 | Retained first-release candidate; not published on PyPI. |
| Private native crate `spatial-typestate-py` | 0.1.0 | Matches pyproject; `publish=false`, exact core path dependency unchanged. |

A fresh primary registry check still found only Rust 0.0.1 (not yanked) and
PyPI HTTP 404; remote tags and GitHub releases were empty. The crate archive
checksum and VCS commit match the dated baseline below. Equal candidate numbers
do not couple future Rust/Python versions. See the self-contained
[migration from the actual published crate and Python first-release limits](migration-0.0.1-to-0.1.0.md).

Step 1 changes only candidate metadata and migration documentation. It does not
approve a candidate artifact campaign, hashes/signoff, tags or uploads. Ordinary
protected-PR CI builds remain quality gates, not publication or artifact approval.
Current registry installation of version 0.1.0 is **not available** at this check.
The following 2026-11-04 section is a historical snapshot, not current checkout
version metadata.

## Observed baseline (2026-11-04)

Primary registry checks, which must be repeated before any release:

- [crates.io API](https://crates.io/api/v1/crates/spatial-typestate): only 0.0.1,
  published 2026-03-22, not yanked, no rust_version metadata; its advertised
  nalgebra/glam features belong to the old API. Archive SHA256 is
  b4c0b2c27b4ce9703ba7710f04281febaaf41f2c0327ef652f9c427b1c27320c.
- Root Cargo.toml is 0.0.2, **unpublished** at that check. Current checked APIs,
  explicit unit parameters and removed backend features differ from published
  0.0.1. Do not substitute 0.0.1 into current guide code and expect compatibility.
- [PyPI JSON](https://pypi.org/pypi/spatial-typestate/json) returned HTTP 404.
  This is not a name reservation or evidence of future upload permission.
  pyproject.toml and the publish=false native crate are both 0.1.0, unpublished.
- git ls-remote --tags origin returned no tags. No existing release tag is
  asserted to identify the published 0.0.1 source commit. The downloaded archive's
  .cargo_vcs_info.json does record full commit
  897f2be9ad55dcab11fea2a1b3d88dce88510df7 (an ancestor of current main).
  This is archive metadata, not a release tag; use that source plus the archive
  as the baseline for migration review.

For current APIs use a reviewed source checkout or explicit full Git commit as
in [README](../README.md), not an unavailable registry version. The Unreleased
[changelog](../CHANGELOG.md) includes breaking migration: explicit point/transform
length and vector unit tags, Result-returning apply/then, private normalized
quaternion components/no unchecked constructor, exhaustive error variants and
removed backend features/dependencies. No source-compatibility promise is inferred
from leaving an unpublished manifest version unchanged during development.

## Independent package versions, one explicit provenance record

Rust and Python version independently; their numbers need not match. Python's
native crate version must match pyproject.toml for each Python artifact set.
A core-only change does not require a Python bump until a new wheel/sdist carrying
that change is delivered. Delivering changed core behavior in Python requires a
new Python version, classified by the Python-visible impact; a Rust source break
hidden by an unchanged adapter need not be a Python break. Python-only additions
do not require republishing the Rust crate. Never replace artifacts under an
existing version, including wheels rebuilt from a different core commit.

Backend-produced wheels now include an importlib.resources-readable
_provenance.json source/build record and compiler notices (see
[package readiness](package_readiness.md)). Legacy/direct-maturin wheels lack
this gate. There is no new native build-info API. A path dependency/version alone
still does not identify an unpublished core revision. The following remains a
mandatory exact-artifact release gate, not publication authorization:

1. Record the full reviewed repository commit, Rust manifest version, Python
   distribution/native versions, both lockfile hashes and compiler/build-tool
   versions in a release manifest associated with the artifact set.
2. Include the same core-identity/provenance record as an immutable package
   resource in each Python wheel and sdist, readable via importlib.resources,
   before first publication. No new native runtime API is required. Test its
   content against the exact build source, including the vendored core in sdist.
3. Record SHA256 for every crate/wheel/sdist in the release manifest. A user must
   be able to map installed distribution version + artifact hash to the core
   commit even when core is not separately published. Document resource lookup
   in the release-specific guide. Local editable/source builds are not release
   artifacts and must not masquerade as those hashes.
4. After signoff, use distinct immutable tags rust-vX.Y.Z and python-vX.Y.Z
   pointing to the reviewed source commit. Tags/manifest identify the release;
   they do not retroactively create provenance for legacy 0.0.1.

The sdist must contain the exact path-dependent core source and native lockfile;
building must not silently resolve a newer Git HEAD or registry core. Wheels
contain compiled core code, not a runtime dependency on an installed Rust crate.
Record build inputs/hashes, but do not promise bit-for-bit reproducible native
binaries across hosts, linkers or build paths.

## Change classification

Follow [Cargo compatibility rules](https://doc.rust-lang.org/cargo/reference/semver.html)
and [Python version syntax/specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/).
Python packaging does not itself enforce this project's semantic guarantees.

| Change | Version treatment for future releases |
| --- | --- |
| Documentation/test-only correction, bug fix preserving documented successful behavior/API | Patch within a 0.y line (y > 0), or patch after 1.0. |
| Backward-compatible API addition | Minor after 1.0; patch is permitted within 0.y, with explicit release notes. |
| Removed/changed signature, required unit/generic, enum variant added to exhaustive Rust error, feature removal, supported input/error/atomicity changes | Breaking: next minor line before 1.0; major after 1.0. |
| Raised MSRV/Python floor, dropped supported platform/feature, changed math association/bit promises or runtime frame identity | Treat conservatively as breaking, even if a package manager allows it. |
| Security/numeric correctness fix requiring incompatible behavior | Breaking classification plus prominent migration/advisory; no silent patch exception. |

For Cargo **0.0.x, each patch is a separate caret compatibility line**; that
does not mean every patch actually changes API. For 0.y.z with y > 0, changing
y is incompatible while z stays in the same caret line. Recommendation: first
new Rust release of the substantially changed current API should start 0.1.0,
not imply compatibility with legacy 0.0.1. The owner selected that 0.1.0 candidate
in step 1 above; the earlier 0.0.2 metadata was unpublished. This selection does
not authorize publication or guarantee compatibility beyond the stated policy.

Before 1.0, a breaking release requires migration notes/examples and an explicit
compatibility-line change, but no guaranteed deprecation duration. Prefer an
additive deprecated path for one published compatible line when it can remain
safe and small; do not retain unsafe or misleading behavior solely for grace.
After 1.0, normal removals should first be deprecated in a minor release and
remain until the next major release. No LTS/backport SLA is promised. Consumers
should pin/review upgrades; Python compatible-release specifiers can span broader
versions than intended (for example ~=0.1 versus ~=0.1.0).

## Tested scope versus support intent

| Area | Current evidence / boundary |
| --- | --- |
| Rust | Edition 2024, MSRV 1.85 library compile checks; development pin 1.91.1; runtime/UI compiler 1.99.0. These are separate policies, not interchangeable requirements. |
| Core host | Linux/Windows CI default/no_std/all-feature runtime suites, lint/docs/release checks. |
| Embedded/MUSL | CI thumbv7em-none-eabihf and MUSL library compilation only; no device runtime/timing evidence. |
| Python | GIL-enabled CPython 3.11 and 3.14 wheel/runtime CI on Linux/Windows x86_64; Linux 3.11 source rebuild. Local Windows 3.12 evidence is narrower than CI. |
| Python metadata | >=3.11,<3.15 and abi3-py311 allow 3.12/3.13, neither 3.12 nor 3.13 is in the CI matrix. abi3 does not validate every interpreter/platform or provide Rust ABI compatibility. |
| Not claimed | macOS/other architectures, PyPy, free-threaded CPython, published wheels, Python no_std or certified behavior. |

Linux readiness wheels now target manylinux_2_28_x86_64, knowingly excluding
glibc 2.17-2.27 and musl. CI checks actual ELF requirements and the same wheel in
fresh pinned manylinux floor (glibc 2.28) and Bookworm (2.36) containers. These
are narrow host/container checks, not universal Linux/kernel compatibility.
Windows remains x86_64. Publication must still approve the exact tested artifacts
and align claims with retained evidence; metadata alone does not expand support.

## Future release checklist and signoff

1. Owner assigns package(s), target versions, support matrix and publication
   authorization; recheck registries, ownership/name availability and migration
   against the **last published** package, not only previous main.
2. Freeze reviewed source commit. Update versions only in that authorized task;
   core manifest, Python native/pyproject and relevant lock entries must agree
   where applicable. Update changelog, compatibility/provenance record and guides.
3. Run [contributor gates](../CONTRIBUTING.md) and all returned CI contexts on
   that exact commit. Independent reviewer verifies migration, licenses,
   provenance, package contents and supported platforms; maintainer signs off.
4. Run cargo +<explicit-installed-toolchain> package --locked (including archive
   verification), inspect cargo package --list and archive contents; verify
   included README links/licenses and no Python/dev evidence/secrets in the core
   archive. Do not use --allow-dirty to bless a release artifact.
5. Build locked release wheels and sdist with the pinned/hash-locked backend.
   Inspect wheel METADATA/WHEEL, license, stubs, provenance and dependencies.
   Install each actual wheel in a fresh environment outside checkout; run all
   installed-wheel tests and [lab workflow](python_lab_workflow.md) without NumPy,
   then optional interop. Rebuild/install sdist from extracted sources and repeat.
   CI --no-build-isolation proves the pinned backend, not arbitrary backend
   resolution; pyproject currently pins maturin==1.16.0 for isolated builds.
6. Review native compatibility tags and declared Python/MSRV/platform limits.
   Record hashes and build environments, retain logs/artifacts. Check no debug
   local paths, credentials, private datasets or unlicensed inputs are packaged.
7. Only after explicit owner artifact approval, perform assigned upload actions.
   For PyPI, satisfy the mandatory Trusted Publishing and per-file attestation
   gates above, including public verification before completion/tags. Registry
   credentials stay out of Git/logs. Re-download the published
   artifacts, verify hashes, install/build and smoke-test the public artifacts.
   Verify release manifest links before announcing availability.
8. On a defective published artifact, document impact and issue a new version;
   consider registry yanking with owner authorization rather than replacing a
   version. No automatic rollback, deletion or publishing credentials are set up.

Publication is still blocked on a separately assigned release task, the provenance
verification and exact artifact decisions. Readiness tooling does not constitute
artifact approval or promise a first publication date.

# Versioning, compatibility and release gates

This policy separates candidate preparation from publication authorization.
Selecting metadata does not authorize artifacts, tags, uploads or new support.
An owner must assign those later steps and approve the exact artifacts/versions.
No release schedule is promised. The historical `publish-0.1.0.yml` workflow is
retired, disabled and forbidden for future use; no compliant future publisher is
configured or approved by this policy change.

## Published release (checked 2026-11-09)

Rust [0.1.0](https://crates.io/crates/spatial-typestate/0.1.0) and Python
[0.1.0](https://pypi.org/project/spatial-typestate/0.1.0/) are available. Both name
source C2 `9974fd6a00521d631d6ff6e35d4aa936f6b624cf`; release tags
`rust-v0.1.0` and `python-v0.1.0` point there and must never move. Core and Python
versions were managed independently for that release; future releases follow
the unified owner decision below. Private native 0.1.0 matches Python, `publish=false`.

```toml
[dependencies]
spatial-typestate = "0.1.0"
```

For no-std library selection replace that dependency with:

```toml
spatial-typestate = { version = "0.1.0", default-features = false, features = ["no_std"] }
```

```sh
python -m pip install --only-binary=:all: spatial-typestate==0.1.0
```

Python metadata is >=3.11,<3.15; published wheels are x86_64 Windows and
manylinux_2_28 Linux, cp311-abi3. Qualification covers GIL-enabled CPython 3.11/3.14
and Linux glibc 2.28/2.36 containers. 3.12/3.13 are metadata-compatible, not CI
matrix entries; local Windows 3.12 is additional evidence. No macOS, musl, ARM,
PyPy or free-threaded claim. Wheel-only installation fails without a matching
wheel; ordinary pip may build the sdist and require installed Rust/build tools.
See [installation/build details](PYTHON-GUIDE.md) and the
[published Rust migration / Python first-release limits](migration-0.0.1-to-0.1.0.md).

Python 0.1.0 is a historical token upload without public attestations. The
[publication record](publication-0.1.0.md) distinguishes exact-byte/source
verification from signed provenance. The published registry descriptions and
0.1.0 rustdoc still contain candidate/unpublished text frozen at C2; updating
repository docs does not change those published pages or permit re-upload.

The following future policy is mandatory. The dated candidate and baseline
sections below it are historical snapshots, not current availability guidance.

## Mandatory future registry publishing policy

Owner policy (2026-11-13, documented here 2026-11-15): every future TelemetryWorks
crate/package upload to **crates.io or PyPI** uses OIDC Trusted Publishing from a
reviewed hosted GitHub Actions workflow. No stored registry token, local real
publish, password or credential fallback is permitted. Local packaging and
credential-free dry runs remain preparation, not publication. PyPI additionally
requires the per-file PEP 740 attestations below. This supersedes the earlier
PyPI-only policy's crates.io exemption.

Rust 0.1.0 was published using a stored `CARGO_REGISTRY_TOKEN` credential; Python
0.1.0 used a local token upload. Neither is a template for future uploads. Their
existing source C2, hashes and tags above remain historical; do not re-upload,
move tags or imply retroactive Trusted Publishing/attestations.

### Trusted Publishing migration: owner and agent steps

These are **planned prerequisites**, not settings/workflows installed by this
roadmap PR. Missing setup blocks the next release; do not recover by uploading
locally. The disabled `publish-0.1.0.yml` stays retired and must not be copied.

**Owner decision 2026-11-15 (superseding the earlier same-day dual-tag choices):**
one tag **`vX.Y.Z` releases both** the Rust crate and Python package from the same
verified commit. Future Rust and Python versions move **in lockstep**: one version,
one tag and one combined changelog section. The private native version matches
that version and remains `publish=false`. Future `rust-vX.Y.Z` and `python-vX.Y.Z`
release routes are retired. Historical `rust-v0.1.0` / `python-v0.1.0` stay at C2
untouched; they are not renamed or supplemented with a retroactive `v0.1.0` tag.

**Owner decision 2026-11-15 (environments):** both **`crates-io`** and **`pypi`**
are protected GitHub environments with the owner as required reviewer, no admin
bypass, selected **Tag** rule **`v*`** and no branch rule. Bind each registry's
Trusted Publisher and its publish job to the corresponding exact environment.
A single tag does not bypass either environment's approval. These are owner setup
requirements, not settings configured by this PR.

**Agent work, through separately reviewed PRs:**

1. Use the [irig106-types release workflow][types-workflow] and
   [release/approver guidance][types-releasing] as the security model. Its 0.1.0
   release on 2026-11-15 has public [crates.io `trustpub_data`][types-publication]
   naming `TelemetryWorks/irig106-types`, run `43727921675` and commit
   `3c517358694646652939c236968b202ebf76e28a`. That success is evidence for the
   reference, not configuration or permission for spatial-typestate.
2. Prepare one coordinated `release.yml` triggered **only** by `v*.*.*` tag
   pushes, no dispatch/branch/PR publishing path. Validate exact `v` + the shared
   Cargo/pyproject/native version and the peeled event SHA on reviewed main.
   Verify both artifact sets before any publish job; each publish job checks out
   the same verified immutable source SHA and uses its own environment. Preserve
   this repository's existing toolchain/feature/artifact gates, rather than
   adopting the reference crate's stable toolchain/feature matrix.
3. Full-SHA pin all actions, including `rust-lang/crates-io-auth-action` (the
   inspected reference uses `3268eb413133e2960fa4ae0e963ca76380c54cd9`, v1.0.6;
   re-review before implementation). Only the registry publish jobs get
   `id-token: write`, never build/verification jobs or top-level permissions.
   Pass its exchanged short-lived credential only to the upload step, never a
   repository secret; verify cleanup/revocation behavior of the selected action.
4. Prepare the coordinated workflow's PyPI qualified-artifact publish job with
   `environment: pypi`, official SHA-pinned publisher, OIDC and attestations for
   every wheel/sdist, as specified below. No password input, stored token,
   `skip-existing` or disabled attestations. Keep artifact source and publishing
   tooling identity explicit, with approved per-file hashes. The trigger tag,
   checked-out release source and both packages' embedded source identities must
   name the same verified commit; record any separate qualification-tooling commit
   as tooling only, never as substitute source.
5. Document preflight and failure gates, independent owner approval and public
   verification. Check new crates.io version metadata's Trusted Publishing
   repository/run/commit against the approved run, fresh archive SHA256/index
   checksum and embedded VCS SHA. Preserve the existing PyPI Integrity API,
   metadata JSON, fresh-download and install checks. No success claim from a
   green upload step alone; inspect public state before any separately reviewed
   recovery from a partial upload.

**Owner work, separately authorized settings/credential actions:**

1. Create GitHub environments **`crates-io`** and **`pypi`** with the owner as a
   required reviewer, explicit approval and administrator bypass disabled. A sole
   owner who triggers the release must still be able to approve it; do not enable
   prevent-self-review in a way that locks that owner out. Naming an environment
   in YAML can auto-create it unprotected, so verify effective protection first.
2. Restrict BOTH `crates-io` and `pypi` deployment eligibility to selected
   **Tag** rule `v*`, with no branch rule. Separately review owner-only tag creation
   and update/deletion protection for `v*`: environment eligibility does not control who may push a
   tag. Existing `rust-v0.1.0`/`python-v0.1.0` tags stay unchanged. Apply the
   owner-decided shared `v*` Tag rule and the exact Trusted Publisher bindings;
   do not retain future dual-tag or independent-version release routes.
3. On crates.io, configure the GitHub Trusted Publisher fields for
   owner `TelemetryWorks`, repository `spatial-typestate`, workflow `release.yml`,
   environment `crates-io`. On PyPI, configure that package's Trusted Publisher
   for the same repository and coordinated reviewed `release.yml` filename,
   and environment `pypi`. Verify the saved identities and ref/environment gates.
4. Enable crates.io **Trusted Publishing only** and verify it is effective;
   delete any stored **`CARGO_REGISTRY_TOKEN`** and **`PYPI_API_TOKEN`** repository
   or environment secrets. Inventory names only; this document does not assert
   that those secrets currently exist. Revoke superseded long-lived credentials
   at each registry and remove obsolete local release credentials through an
   authorized owner action. Deleting a GitHub secret does not revoke its token.
   No token may be retained as a fallback during migration.

### Proposal: coordinated ordering and partial-release handling

**Proposal, not an owner-selected implementation:** verify/qualify BOTH packages,
review the shared version/tag/source, both publisher configurations and exact
artifact hashes before any upload. Then publish crates.io, independently verify
its public bytes/Trusted Publishing identity, and only then permit the PyPI job
(after its own protected-environment approval). Finally verify every Python file's
hash, metadata and PEP 740 proof before declaring the shared release complete.
The tag already exists as the workflow trigger; it is not a completion signal.
Registry operations are not an atomic transaction, and a later approval may be
denied or fail even after the first registry succeeds.

- If either verification/preflight fails, publish neither package. If the first
  upload fails or returns an ambiguous result, stop and inspect public registry
  state before starting PyPI or considering recovery; do not assume no upload.
- If Rust succeeds but PyPI fails (including a partial file set), record an
  **incomplete coordinated release**, list exactly what is public, and stop.
  Do not announce completion, move/delete the shared tag, overwrite a version,
  re-upload accepted files, use `skip-existing`, or fall back to local/token upload.
- **Recovery proposal:** obtain independent review and owner authorization for a
  narrowly scoped OIDC/attested upload of only still-missing approved bytes from
  the SAME verified source, after re-verifying all accepted public artifacts.
  If that cannot safely complete the set, propose a new coordinated version/tag;
  owner decides recovery/yanking. Never silently rebuild different bytes under
  the partially published version or blindly rerun the whole workflow. A public
  version mismatch during failure is an incident to report, not a policy exception
  allowing independent completed releases.

This ordering/recovery proposal needs a separate workflow review before use.

### Independent approver checklist

Before approving a pending environment deployment, the owner must obtain the
actual tag and run commit from GitHub independently of workflow outputs; fetch
current main and verify ancestry/version. Compare the run commit's workflow bytes
with the immutable independently reviewed workflow on main (Git blob equality is
sufficient). Do not let a tag's modified workflow attest to its own safety. Inspect
checks, exact artifact hashes/contents and source identity; refuse approval for
any mismatch, even with green verification. Never bypass environment protection.

**Immutable-published-text lesson:** before publication inspect the actual
packaged README/metadata, rendered descriptions, changelog date and instructions
for stale candidate claims and broken packaged links. Editing GitHub docs later
cannot change text embedded in an already published crate/wheel/sdist. The
reference's checklist complements this crate's historical frozen-0.1.0 lesson;
use a separately authorized new version for package corrections, not re-upload.

[types-workflow]: https://github.com/TelemetryWorks/irig106-types/blob/fef4233b1e4deca170e881fc34438555b09e15d8/.github/workflows/release.yml
[types-releasing]: https://github.com/TelemetryWorks/irig106-types/blob/fef4233b1e4deca170e881fc34438555b09e15d8/docs/RELEASING.md
[types-publication]: https://crates.io/api/v1/crates/irig106-types/0.1.0

## Mandatory future PyPI publishing policy

Owner decision (2026-11-08): **every future PyPI release/upload** must use OIDC
Trusted Publishing from a reviewed hosted GitHub Actions job **and** publish
PEP 740 publish attestations for every distribution file: all wheels and the
sdist. Trusted Publishing alone is insufficient: some providers authenticate
uploads without producing attestations. Local builds and qualification remain
allowed; API-token/password uploads, local `maturin upload`/`twine upload`, token
fallbacks and `attestations: false` are forbidden for future PyPI uploads. This
PyPI-specific attestation rule supplements the both-registry OIDC policy above.

Before any future upload:

1. Separately review and configure the PyPI Trusted Publisher for the exact
   repository `TelemetryWorks/spatial-typestate` and named workflow filename.
   Record its allowed ref and immutable publishing-tooling commit. Bind both the
   publisher and publish job to the protected `pypi` environment described above.
   Missing or mismatched setup is a release blocker, not permission to use a token.
2. Use the official `pypa/gh-action-pypi-publish` action pinned to a reviewed full
   commit SHA, with `attestations: true`, no password/token inputs and no
   `skip-existing`. Grant `id-token: write` only to the single publish job, never
   top-level or to build/test jobs. Keep build/qualification separate from
   publishing and carry the approved per-file SHA256 manifest across jobs/runs.
3. Validate the exact artifact set, source commit, embedded source records and
   hashes before upload. Record the publishing workflow/ref/commit and each
   artifact source explicitly; the shared tag and both packages must identify
   the same verified release source commit. Record any separate qualification
   tooling identity as such. An attestation-generation,
   signing or upload failure stops release; never retry via a token or silently
   omit a wheel or sdist's attestation.

After upload, before declaring the coordinated release complete (the single
`vX.Y.Z` trigger tag already exists):

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
- Separately verify the new version's public PyPI JSON has
  `license_expression: Apache-2.0`, non-null `license_files` containing `LICENSE`,
  and exactly the canonical Repository, Documentation and Issues `project_urls`
  declared in pyproject. Missing/changed fields block coordinated completion;
  correct wheel/sdist headers alone do not prove that the uploader preserved the
  metadata form. This JSON check is not attestation proof and cannot replace the
  per-file Integrity API checks. See the [historical 0.1.0 diagnosis](package_readiness.md#project-links-and-licence-display-2026-11-09).
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

## Historical candidate decision (2026-11-08, step 1 only)

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
Registry installation of version 0.1.0 was **not available** at that step-1 check.
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

At that historical check, the guide used a reviewed source checkout or full Git
commit rather than an unavailable registry version. Current installation uses
published 0.1.0 as above. The Unreleased
[changelog](../CHANGELOG.md) includes breaking migration: explicit point/transform
length and vector unit tags, Result-returning apply/then, private normalized
quaternion components/no unchecked constructor, exhaustive error variants and
removed backend features/dependencies. No source-compatibility promise is inferred
from leaving an unpublished manifest version unchanged during development.

## Unified future version, tag and explicit provenance record

**Owner decision 2026-11-15:** future Rust/Python releases share one version,
`vX.Y.Z` tag, source commit and combined changelog section. A core-only or Python-only
change still releases both at that shared version after both artifact sets pass
qualification. Classify the combined release by the more disruptive consumer
impact; use the existing compatibility rules for each surface. Native/pyproject
and core manifests/lock self-entries must agree in the next authorized release
preparation task. Never replace artifacts under an existing version.

### Proposal: choosing the first coordinated version

The published Rust/Python releases currently both say 0.1.0, but were selected
under the former independent-version policy and retain their two historical tags.
**Proposal:** recheck each registry's latest versions and classify all changes
since each package's last publication. If only backward-compatible corrections
are included and the number is unused in both registries, propose **0.1.1** for
both. If either surface requires a pre-1.0 breaking change, propose **0.2.0** (or
another jointly unused compatible line justified by the actual changes) for both.
The owner chooses the version; these are examples, not a bump or release approval.
Do not mechanically select a number without checking availability and semantics.

A future release-preparation PR will set all version metadata consistently and
write ONE dated changelog section, with Rust and Python changes described within
it. After review/qualification and owner authorization, one new `vX.Y.Z` tag
identifies both artifacts' verified source. Preserve the earlier independent
selection records as history; neither old tag moves and no new 0.1.0 upload is
permitted. No version or tag is changed by this roadmap PR.

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
   commit for the coordinated release. Document resource lookup
   in the release-specific guide. Local editable/source builds are not release
   artifacts and must not masquerade as those hashes.
4. Under the superseding **owner decision 2026-11-15**, ONE `vX.Y.Z` tag triggers
   both publishes from the same approved source. It must never move; Git tags
   are not technically immutable without protection. Historical `rust-v0.1.0`
   and `python-v0.1.0` remain at C2. Tags/manifest do not retroactively create
   registry provenance or signal completion without both registries' checks.

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
y is incompatible while z stays in the same caret line. Rust 0.1.0 starts a
new compatibility line for the changed API; it does not imply compatibility with
legacy 0.0.1. The earlier 0.0.2 metadata was unpublished. A future version decision
does not itself authorize publication or guarantee compatibility beyond this policy.

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
| Not claimed | macOS/other architectures, PyPy, free-threaded CPython, Python no_std or certified behavior. |

Linux readiness wheels now target manylinux_2_28_x86_64, knowingly excluding
glibc 2.17-2.27 and musl. CI checks actual ELF requirements and the same wheel in
fresh pinned manylinux floor (glibc 2.28) and Bookworm (2.36) containers. These
are narrow host/container checks, not universal Linux/kernel compatibility.
Windows remains x86_64. Publication must still approve the exact tested artifacts
and align claims with retained evidence; metadata alone does not expand support.

## Future release checklist and signoff

1. Owner assigns the coordinated Rust/Python release, one version, support matrix
   and publication
   authorization; recheck registries, ownership/name availability and migration
   against the **last published** package, not only previous main.
2. Freeze reviewed source commit. Update versions only in that authorized task;
   core manifest, Python native/pyproject and relevant lock entries must agree.
   Update one combined changelog section, compatibility/provenance record and guides.
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
   For both registries, satisfy the OIDC-only policy and protected-environment
   owner approval above; for PyPI also satisfy all per-file attestation gates.
   The single shared trigger tag precedes both uploads; verify both registries
   and all Python attestation/metadata gates before declaring coordinated completion.
   Registry credentials stay out of Git/logs. Re-download the published
   artifacts, verify hashes, install/build and smoke-test the public artifacts.
   Verify release manifest links before announcing availability.
8. On a defective published artifact, document impact and issue a new version;
   consider registry yanking with owner authorization rather than replacing a
   version. No automatic rollback, deletion or publishing credentials are set up.

Publication is still blocked on a separately assigned release task, the provenance
verification and exact artifact decisions. Readiness tooling does not constitute
artifact approval or promise a first publication date.

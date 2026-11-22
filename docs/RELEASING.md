# Versioning, compatibility and release gates

This policy separates candidate preparation from publication authorization.
Selecting metadata does not authorize artifacts, tags, uploads or new support.
An owner must assign those later steps and approve the exact artifacts/versions.
No release schedule is promised. The historical `publish-0.1.0.yml` workflow is
retired, disabled and forbidden for future use; that historical file is not a template for the current standard publisher.

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

The owner settings remain prerequisites; the reviewed
[`trusted-publishing.yml`](../.github/workflows/trusted-publishing.yml) implements
the tag-only build/verification and gated deployment path described below.
This workflow implementation does not configure registry publishers or settings. Missing setup blocks the next release; do not recover by uploading
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

1. Implement the [org standard at d1d2e18][org-standard], PyPI variant, in the
   existing `trusted-publishing.yml` and a reusable `build-release.yml`. Retain
   this crate's explicit compiler, feature, native/backend, platform and exact-byte
   qualification; do not substitute the reference package's broader platforms.
2. Run PR/manual unsigned dry runs before release preparation. Only a real `v*`
   tag **push** can authorize the nested signer or any downstream publication job;
   a manual dispatch even from a tag cannot. Every privileged checkout uses
   `github.sha`, with credentials disabled. Keep registry names/environments fixed.
3. Pin actions to full SHAs. Qualifiers have only contents read. Only the nested
   release signer and fixed non-release fixture signer get attestation/OIDC writes; the caller delegates those permissions
   without giving them to nested build jobs. Registry jobs get their separate
   minimal OIDC permissions and environment approvals, with no stored credential.
4. Preserve per-file PEP 740, public metadata/bytes, signature, installed-consumer
   and docs.rs gates. Use controlled existing-file recovery only as described below;
   `skip-existing` is not evidence that accepted bytes are correct.

[org-standard]: https://github.com/TelemetryWorks/.github/blob/d1d2e1829d0bbe3a8bf6e1ef285b999a7e33c1e7/docs/TRUSTED-PUBLISHING.md

**Owner work, separately authorized settings/credential actions:**

1. Verify GitHub environments **`crates-io`** and **`pypi`** with the owner as a
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
   owner `TelemetryWorks`, repository `spatial-typestate`, workflow `trusted-publishing.yml`,
   environment `crates-io`. On PyPI, configure that package's Trusted Publisher
   for the same repository and coordinated reviewed `trusted-publishing.yml` filename,
   and environment `pypi`. Verify the saved identities and ref/environment gates.
4. Enable crates.io **Trusted Publishing only** and verify it is effective;
   delete any stored **`CARGO_REGISTRY_TOKEN`** and **`PYPI_API_TOKEN`** repository
   or environment secrets. Inventory names only; this document does not assert
   that those secrets currently exist. Revoke superseded long-lived credentials
   at each registry and remove obsolete local release credentials through an
   authorized owner action. Deleting a GitHub secret does not revoke its token.
   No token may be retained as a fallback during migration.

### Coordinated ordering and partial-release handling

Owner assignment 2026-11-22 adopts the org standard's ordering: qualify BOTH,
then `publish-crates`, then `publish-pypi` (which **needs publish-crates**), then
`github-release` and read-only `verify`. The tag is an input, not a completion
signal. These registries do not provide a cross-registry transaction.

- A failed gate/build/reproduction/signature check publishes nothing. A failed or
  ambiguous upload requires inspection of public state before any recovery.
- Rust success followed by PyPI failure is an **incomplete coordinated release**.
  Record exactly what is public. Do not move tags, replace files, choose new bytes
  under that version, use a stored token or publish locally.
- After independent inspection and owner-approved recovery of the SAME source
  and payload, the standard permits rerunning the relevant failed publication job:
  crates.io skips an existing version only while comparing its served bytes/index
  and Trusted Publisher source; PyPI uses `skip-existing: true`, then the final
  verifier checks ALL public digests, metadata and PEP 740 identities. A conflicting
  existing file fails, never qualifies as recovery. Do not blindly rerun the whole
  workflow or rebuild different native bytes. Keep the original immutable artifacts.
- A published GitHub Release is read-only. A matching draft may receive only
  missing assets; existing assets are compared, never replaced. A mismatch stops
  recovery and needs owner incident/yank/new-version decisions.

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

[types-workflow]: https://github.com/TelemetryWorks/irig106-types/blob/2899b30/.github/workflows/trusted-publishing.yml
[types-releasing]: https://github.com/TelemetryWorks/irig106-types/blob/2899b30/docs/RELEASING.md
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
   `skip-existing: true` only under the controlled recovery rule above. Grant the PyPI publisher `id-token: write` only at its job level, never
   top-level or to build/test jobs. The separate crates.io publish job has its own
   narrowly scoped OIDC grant. Keep build/qualification separate from
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

## Coordinated publisher implementation and approvals

The [caller](../.github/workflows/trusted-publishing.yml) follows the
[org standard at d1d2e18][org-standard], PyPI variant. Pushes of `v*` tags are the
only signing/publication authority. `pull_request` changes to release tooling and
`workflow_dispatch` run the **same full qualification** and **Publish path (dry run)**,
without release-artifact signing, environment deployment or registry writes. A separate
fixed synthetic fixture is attested solely for the token-permission check below. Dispatching from a
`v*` tag is still unsigned/read-only. Default runners are Ubuntu 24.04; Windows
qualification remains on Windows. The retired `publish-0.1.0.yml` is left alone:
never enable, copy, edit or call it.

The first unified version is STILL an owner decision (0.1.1 versus 0.2.0 or
another jointly unused version). This workflow change chooses no version and
creates no tag or upload. It does not repair historical 0.1.0 provenance.

### What verification does

- `gate`: clean `github.sha`, lockstep core/native/pyproject and both core lock
  entries; remote **annotated** version tag peeled through GitHub's tag-object API;
  main ancestry and successful exact-commit main push runs of Rust, Python,
  CodeQL and Sonar; dated `## [X.Y.Z] - YYYY-MM-DD` changelog and committed
  `docs/releases/vX.Y.Z.md` with an H1 title. It reads all bounded API pages,
  without filtering successful runs at request time. Missing tag/CI/release notes
  are reported on PR/manual runs, but block a real tag push. Metadata/source
  mismatches block even dry runs. The release body is the dated changelog section;
  title is the committed release document's H1. Do not fabricate notes for 0.1.0.
- `build`: calls [the reusable builder](../.github/workflows/build-release.yml).
  Explicit Rust 1.99.0 runs three runtime/UI/example modes, fmt, clippy/docs/release
  modes, zero normal dependency graphs, 1.85.0/1.91.1 library compatibility,
  thumb debug/release and MUSL library compiles, root/native cargo-deny, default
  `cargo package` verification and a second byte-identical package. Pin/MSRV stay
  unchanged. Native tests/lint, backend packaging controls and installed-wheel
  tests run on Linux/Windows GIL-enabled Python 3.11/3.14, two workers.
- Linux 3.11 selects the manylinux_2_28 x86_64 cp311-abi3 wheel and canonical sdist;
  Windows 3.11 selects the cp311-abi3 win_amd64 wheel. Linux rebuilds the sdist
  without Git, checks metadata parity and tests both Linux wheel origins at
  3.11/3.14 and glibc 2.28/2.36. Windows separately installs the SAME 3.11-built
  wheel on 3.11/3.14 in outside-checkout venvs, stdlib then hash-locked NumPy suites
  and the lab. Direct maturin CLI cannot bypass the backend. Other matrix builds
  are diagnostics, not extra release files.
- `collect` selects exactly FOUR release files, validates source inventory,
  metadata/licenses/paths/RECORD/ELF and matching runtime receipts. It freezes
  `release-manifest.json` and LF `SHA256SUMS` in immutable `release-<version>`.
  CycloneDX 1.5 source-graph SBOMs (cargo-cyclonedx 0.5.9, locked/two workers)
  describe packaged core and native graphs, not complete binary/compiler contents.
- Nested `sign` alone signs release payloads, additionally checking actual
  push/tag/ref context. It signs only the builder's own fixed artifact, not
  caller-selected payloads. Immutable `release-<version>-attestations` contains
  `spatial-typestate-<version>.crates.intoto.jsonl` plus crate/Python SBOM bundles.
  Payload and sidecar never replace one another. Bundles are outside SHA256SUMS:
  verify their signatures instead of introducing a self-hash cycle. The GitHub
  signer is **build-release.yml**; the PyPI PEP 740 publisher remains
  **trusted-publishing.yml**, environment **pypi**. These are different identities.
- `publish-path-check`: read-only, no environment/OIDC. Strict full file-set and
  checksums, compiler matches the builder's exact output, `cargo package --locked
  --no-verify` must reproduce the frozen archive byte-for-byte. A fresh crates.io
  0.1.0 download must match the independently owner-reviewed committed
  [checksum fixture](../.github/release-fixtures/spatial-typestate-0.1.0.sha256)
  (`fc6b60a9...`, 64,458 bytes), NOT a second fresh download. This exercises the
  public byte-check path without implying 0.1.0 is attested or rebuilding it.
  A second known-good check reads the versioned PyPI JSON API, downloads BOTH
  published 0.1.0 wheels and the sdist from its file URLs, and compares JSON and
  downloaded SHA256 values with the independently pinned
  [Python checksum fixture](../.github/release-fixtures/spatial-typestate-python-0.1.0.sha256).
  This historical download check cannot exercise PEP 740: Python 0.1.0 has no
  public attestations. It does not claim retroactive provenance.

### Publication permissions and approval checklists

| Job | Permissions | Environment / approval |
| --- | --- | --- |
| `gate` | contents read, actions read | none |
| Nested qualification/collect | contents read | none |
| Nested `sign` (caller `build` delegates) | contents read, id-token write, attestations write | independent real-tag guard |
| `publish-path-check` | contents read | none; unsigned package dry run |
| Nested `permission-fixture` | contents read, id-token write, attestations write | none; fixed synthetic data, same-origin human PR/branch dispatch only |
| `publish-permissions-check` | id-token write ONLY, implicit metadata read; no OIDC request | none; real bundle verification only |
| `publish-crates` | contents read, id-token write | crates-io; owner required reviewer |
| `publish-pypi` | id-token write ONLY; no source checkout | pypi; owner required reviewer |
| `github-release` | contents write ONLY | none; needs BOTH registries |
| `verify` | contents read ONLY | none; needs GitHub release |

All publication jobs independently require the original tag-push event in
addition to gate outputs. Both environments must admit only `v*` tags and forbid
admin bypass; settings are checked separately, never changed by the workflow.
No build script/proc macro runs in the crates.io OIDC job: it packages/publishes
with `--no-verify` after the read-only builder's default verification. Same exact
compiler, clean source and byte comparison are required even after a long approval
wait. Cargo cannot upload an archive path, so its repackage and served-byte checks
are essential. PyPI receives exactly the two frozen wheels and sdist with explicit
attestations ON; nothing builds there.

Before **crates-io** approval, independently check the actual event/tag SHA, remote
annotation/main ancestry, reviewed workflow blob, complete build matrix, selected
hashes and nested-builder signatures/SBOM subjects. Verify environment and registry
bindings, intended main CI and dated packaged descriptions. Refuse any mismatch.
Before **pypi** approval, additionally require crates.io success, served archive/index
byte identity and Trusted Publisher source, then verify all three Python files and
publisher binding. The shared tag does not waive either independent approval.

`github-release` needs no third environment approval under this standard. It
checks signatures, committed title/body, all asset names/sizes/digests and fresh
bytes. It finds interrupted drafts by listing releases, adds only missing assets,
checks the complete draft then publishes; no `--clobber` or published-release
mutation. Latest uses the highest stable semantic version, not upload time.
`verify` rechecks fresh registry bytes/metadata, every PyPI Integrity API proof,
GitHub release assets, source/signer identities, an outside-checkout public-wheel
consumer and bounded docs.rs status. Pending after the bound or a failed build
fails completion. The PyPI UI Provenance checks above remain an independent owner
gate. No SLSA level, universal platforms, Python reproducibility or safety claim.

The checkout-free PyPI job runs a standalone stdlib-only
[`release_pypi.py stage`](../.github/scripts/release_pypi.py) with `python3 -I`.
The reusable builder supplies the fixed helper as a separate immutable artifact;
BOTH the dry run and PyPI job check its workflow-pinned SHA256 **before executing
it**. No downloaded code is trusted merely because it accompanies a payload.
The dry run exercises the same transport with `--help` and no signing authority.
Only the tag-push stage mode verifies every payload signature and each Python
SBOM binding, then creates `pypi-dist` with exactly the selected three files.
A failed signature leaves that directory absent and fails the step, blocking the
following official PyPI upload action. No `continue-on-error` or unconditional
upload is allowed. The helper is tooling, not a new Release asset or SBOM subject.
Tests pin this ordering and reject bad signatures before PyPI upload or GitHub
Release creation/attachment; removing those calls must fail their tests.

### Pre-release token-permission proof

The checkout-free **PyPI token permissions (dry run)** job has exactly the same
`GITHUB_TOKEN` permission declaration as `publish-pypi` (initially `id-token: write`
only), no deployment environment and no registry action. It sets `GH_TOKEN` in the
same way and runs the SAME standalone helper's shared provenance/SBOM verification
implementation with real `gh attestation verify --bundle` commands. It records the
runner's actual GH CLI version. It never requests an OIDC token or creates an
upload directory.

There is no signed historical spatial-typestate 0.1.0 fixture. The reusable
builder therefore signs only a separate, fixed `permission-probe.txt` plus empty
synthetic CycloneDX fixture, using a no-checkout job with pinned actions and no
repository-code execution. The fixture is NOT a crate, wheel, sdist or release
SBOM, and is never included in release payloads, release sidecars or Release assets.
Its fixture signer is still `build-release.yml`. This deliberately scoped exception
to unsigned package dry runs does not enable signing actual release artifacts from
PRs. Probe verification constrains the actual PR/branch ref and triggering commit;
release staging still requires the actual version tag push and tag identity.

Both fixture signing and its consumer run only for original-repository human
same-origin PRs or branch dispatches. Fork/Dependabot PRs and tag dispatches skip
this proof; a skipped check is NOT evidence of sufficient permissions. Before
pushing any real release tag, run the manual branch dry run at the reviewed release
commit and require the explicit permission check to pass, along with qualification.
Do not discover a token-permission failure after Rust has already published.

**Observed result, 2026-11-22: no `contents: read` grant is needed for the tested
local-bundle verification path.**
[Run 45058171021](https://github.com/TelemetryWorks/spatial-typestate/actions/runs/45058171021)
at PR head `b8c29bd23e5324ea2df58d9cb12568666f5611f1` passed the real
**PyPI token permissions (dry run)** job, as well as full qualification and Publish
path. The runner used GH CLI **2.104.0** (2026-11-12), Ubuntu 24.04 image
`20261116.133.1`. The job's setup log lists only **Metadata: read** under
GITHUB_TOKEN Permissions: no Contents or Attestations grant. The job declaration
has `id-token: write`, exactly like `publish-pypi`; the verifier did not request
OIDC. Its pinned helper verified both provenance subjects and the CycloneDX
subject/predicate from real same-run bundles with expected repository, reusable
signer, `refs/pull/42/merge` and merge SHA
`311d9e61d9adef1298d65bb9f375aa6a4f22ff85`. No contents permission was added to
the publisher, no personal token was used by that job, and no staging or upload
occurred. The initial fixture lacked the signer's required `serialNumber`; fixing
that synthetic format was independent of permissions and changed no real SBOM.

This result establishes the observed public-repository GH CLI/bundle path, not a
permanent guarantee for changed CLI/server policies, private repositories, PEP 740
or tag publication. Keep the live check and require a fresh branch dry-run pass
before a real release tag. Additional read permission, if ever required, must be
added to BOTH probe and publisher and demonstrated by the real check before a
tag. Local personal-token verification or mocked CLI success is not a substitute.
No registry/environment settings were changed.

### Online and offline verification

For every downloaded crate/wheel/sdist, set `version` and `commit` to independently
reviewed values. Download the immutable payload and sidecar together; require the
exact expected files and check every SHA256SUMS entry (no ignore-missing):

```sh
sha256sum --check --strict SHA256SUMS
repo=TelemetryWorks/spatial-typestate
builder=$repo/.github/workflows/build-release.yml
gh attestation verify "$file" --repo "$repo" \
  --bundle "spatial-typestate-$version.crates.intoto.jsonl" \
  --signer-workflow "$builder" --source-ref "refs/tags/v$version" \
  --source-digest "$commit" --deny-self-hosted-runners
# Use the crate or Python SBOM bundle respectively, same identity constraints:
gh attestation verify "$file" --repo "$repo" --bundle "$sbom_bundle" \
  --predicate-type https://cyclonedx.org/bom --signer-workflow "$builder" \
  --source-ref "refs/tags/v$version" --source-digest "$commit" --deny-self-hosted-runners
```

Compare the successfully verified CycloneDX predicate with the corresponding
local SBOM JSON, not an unverified decoded bundle. Online, the registry-downloaded
files can also use `gh attestation verify` lookup without `--bundle`, keeping
signer/ref/digest constraints. For offline use, provision `gh attestation trusted-root`
on a connected trusted machine, transfer it with all files/bundles, and add
`--custom-trusted-root trusted_root.jsonl` to each bundle verification. Provision
verifier binaries/trust roots independently; checksums alone are not authenticity.

For PyPI additionally fetch each file's Integrity API object and run the reviewed,
hash-locked [release_integrity.py](../.github/scripts/release_integrity.py) verifier:
PEP 740 identity is the CALLER workflow in `pypi`, not the reusable build signer.
Retain public proofs separately; never mutate/reseal the release payload to add them.
Source graph attestations are not build reproducibility or code-safety proofs.

### Practical limits of this conversion

The current backend/release helpers deliberately accept stable `X.Y.Z` only.
Rust SemVer and Python prerelease spellings differ; adding a reviewed shared
prerelease mapping (PEP 440 versus SemVer) needs a separate reviewed change
**before any pre-release tag is pushed**. Stable-only `X.Y.Z` is the accepted
current scope, not an implicit mapping or pre-release approval.
Artifact retention is 90 days; preserve the frozen payload/sidecar before expiry
for any authorized recovery, never substitute a rebuild. A PR dry run cannot
exercise OIDC, approval delay, registry writes or live tag-only signing. It does
exercise the full qualification, archive reproduction and known-good download.
Published 0.1.0 keeps its historical token-uploaded bytes, dual tags and missing
public PyPI attestations. The retired publisher is unchanged.

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

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

1. Use the [irig106-types release workflow][types-workflow] and
   [release/approver guidance][types-releasing] as the security model. Its 0.1.0
   release on 2026-11-15 has public [crates.io `trustpub_data`][types-publication]
   naming `TelemetryWorks/irig106-types`, run `43727921675` and commit
   `3c517358694646652939c236968b202ebf76e28a`. That success is evidence for the
   reference, not configuration or permission for spatial-typestate.
2. Prepare one coordinated `trusted-publishing.yml` triggered **only** by `v*.*.*` tag
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
   `skip-existing`. Grant the PyPI publisher `id-token: write` only at its job level, never
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

The [workflow](../.github/workflows/trusted-publishing.yml) is tag-only
(`v*.*.*`); it has no dispatch, branch or PR publication trigger. All actions are
full-SHA pinned, all checkouts disable persisted credentials, and workflow
permissions default to contents read. Verification jobs have no OIDC, package
credential, attestation or contents-write grant. `publish-crates` and
`publish-pypi` alone have job-scoped OIDC/attestations write; `release-assets`
has contents write only. The retired 0.1.0 publisher is neither used nor changed.

**Proposal implemented for review, still pending owner selection for execution:**
the ordering described above is verify BOTH, crates.io, PyPI, then durable Release
retention. An environment approval is not automatic approval of later jobs.
The FIRST unified version remains an owner decision (0.1.1 versus 0.2.0 or another
justified jointly unused version). This implementation changes no versions and
creates no tag; current 0.1.0 would fail the already-published-version guard.

### What verification does

- `source` checks the original repository/tag push, attempt 1, exact clean event
  SHA, live remote tag, main ancestry, all three manifest versions and both
  lockfile core entries. Neither registry may already contain the proposed
  version. An unavailable registry is a blocker, not evidence of absence.
- `verify-crate` runs the full Rust CI equivalent: installed explicit 1.99.0,
  three test modes and examples, fmt, both clippy/rustdoc/release modes, zero-normal-
  dependency graphs, all six 1.85.0/1.91.1 compatibility checks, thumb debug/release
  and MUSL library compilation. The pin and MSRV do not change. Windows core
  runtime/UI/example modes also run in the Windows Python 3.11 build job.
- `verify-python` runs the existing native and packaging gates on Linux/Windows
  GIL-enabled 3.11/3.14, using the in-tree backend via `package_ci.py`; no direct
  maturin CLI bypass. It checks prepared metadata, real artifact metadata,
  source inventory, paths, licences, RECORD and Linux ELF policy. Linux 3.11
  supplies the canonical sdist and manylinux_2_28 x86_64 wheel; Windows 3.11
  supplies the cp311-abi3 win_amd64 wheel. Other per-job builds are diagnostics,
  not additional release files. The Linux sdist is rebuilt without Git and both
  resulting Linux wheels run on both 3.11/3.14 at glibc 2.28 and 2.36.
- `verify-windows-wheel` downloads the SAME 3.11-built Windows wheel on 3.11 and
  3.14, checks its inventory hash before install, runs outside-checkout fresh-venv
  imports/provenance, stdlib and hash-locked optional NumPy suites and the lab.
- Final `verify` waits for every build/consumer job, selects exactly one crate,
  those two wheels and the canonical sdist, and rechecks source/metadata and
  matching runtime receipts. `release-manifest.json` binds source, tag, version,
  run and the four hashes. External LF `SHA256SUMS` covers all transfer files
  except itself. No self-hash or unsigned-manifest authenticity claim is made.

The crate is packaged with default Cargo verification, then byte-compared with
`cargo publish --dry-run` output. The fresh publish runner repeats this comparison
with explicit 1.99.0 BEFORE requesting its short-lived OIDC credential. Cargo
cannot upload a prebuilt archive path: real publish packages again. A fresh
crates.io download, index checksum and Trusted Publisher repository/run/SHA must
match before signing evidence. A post-upload mismatch cannot undo publication;
stop and report it, and leave any yank to the owner.

CycloneDX 1.5 source-graph SBOMs use cargo-cyclonedx 0.5.9 (`--locked`, two workers):
core from the unpacked crate, Python from the same verified native/core manifests
and locks, all features/targets. They include development/build dependencies and
are not a complete binary or Rust-compiler SBOM claim. Compiler notices remain
in the wheels under the existing packaging policy. Both SBOMs are retained and
attested about their corresponding artifact subjects.

PyPI receives exactly the three verified files with OIDC and explicit
`attestations: true`, no password, skip-existing or fallback. After upload,
fresh public hashes and the licence/URL JSON gate must pass. Every file's
Integrity API object is retained; hash-locked pypi-attestations 0.0.31 verifies
its certificate chain, transparency evidence, publisher and subject, followed by
exact issuer/repository/workflow/tag/commit and hosted-runner certificate checks.
No unverified payload is treated as identity. Both GitHub SLSA provenance and
source-graph SBOM attestations are also created for every Python distribution.
GitHub attestation bundles are separate from PyPI publish attestations and do not
substitute for them.

### Three independent approval checklists

For EACH deployment, obtain run ID, actual run commit/tag and reviewed-main
identity independently of workflow output. Fetch current main in a trusted
checkout and confirm the run commit is on main. Compare Git blob IDs for the
workflow, `.github/scripts/release_guard.py`, `release_integrity.py`, the
attestation requirements lock and relevant backend/build files against the
independently reviewed main source. A modified tag workflow cannot approve itself.
Record those identities and the exact four artifact hashes. No approval if a
required check is absent, skipped unexpectedly, failing or bound to another SHA.
The main commit's normal CI, CodeQL and real Sonar gate remain prerequisites;
the release jobs do not import a Sonar credential or replace that evidence.

1. **`publish-crates`, environment `crates-io`:** confirm both registry versions
   absent, tag/version/source match, all verification jobs and SAME-wheel tests
   passed, package contents and source records reviewed, and both registry
   Trusted Publishers/protected `v*` environment rules effective. Confirm the
   immutable workflow filename is `trusted-publishing.yml` (not `release.yml`).
   Check the reproducibility preflight; approve only this first deployment.
2. **`publish-pypi`, environment `pypi`:** repeat run/tag/source/blob/hash identity
   checks. Confirm crates.io serves the exact selected crate, its Trusted
   Publisher data and both GitHub crate attestations match. Confirm PyPI version
   still absent and its exact repository/workflow/environment binding. Approve
   only these two wheels plus the canonical Linux sdist; no rebuilding or new
   artifact selection after the first registry accepts bytes.
3. **`release-assets`, separate `crates-io` approval:** repeat all identities,
   confirm both registries' public bytes/checksums, PyPI modern licence/URL
   metadata and EVERY file's verified PEP 740 identity/digest. Independently open
   each PyPI file page and require its expected Provenance display (not Without
   provenance); an API pass alone is not a claim that the UI was inspected.
   Verify crate/Python GitHub provenance AND SBOM bundles against the same
   artifact hashes using the paths below. Missing evidence blocks approval.

Only the third job can create a GitHub Release. It re-resolves/peels the remote
tag to the verified commit and combines checked evidence. New Releases stay
**draft** until all files are present; existing assets must be byte-identical,
missing assets may be added, and nothing is overwritten. The tag and Latest
selection are never changed. Release assets have no Actions retention expiry,
but can still be deleted by authorized users; archive an independent copy.
Transfer/evidence artifacts last 90 days or less under repository policy.
Both publishers attempt to retain partial evidence on failure as diagnostics;
a failed job or inconsistent checksum set is never qualified release evidence.

### Failure and recovery boundary

Every helper and both publish jobs require attempt 1; no automatic upload retry,
rerun publication, skip-existing or token fallback. Registry propagation checks
are bounded READ retries only. Any failure after an accepted upload is an
**incomplete coordinated release**: inspect public state, preserve original run
artifacts/logs and report exact accepted/missing files. Never rerun publication
to repair an attestation, metadata field or Release asset. The separately reviewed,
owner-authorized recovery proposal above is not a dispatch/recovery feature of
this workflow; a retention-only recovery would also need separate review and
must not invoke either publisher. No moving/deleting a tag or reusing a version
for different bytes. Do not declare completion until the third approval and all
mandatory public checks pass.

### Path A: retained Release evidence, then offline verification

Choose version and source SHA independently from the reviewed release PR/tag;
these placeholders do not choose the first unified version. With an existing
GitHub CLI supporting attestation verification, while connected:

```sh
set -eu
version=X.Y.Z
commit=REPLACE_WITH_REVIEWED_TAG_COMMIT_SHA
repo=TelemetryWorks/spatial-typestate
gh release download "v$version" -R "$repo" -D evidence
gh attestation trusted-root > trusted_root.jsonl
(cd evidence && sha256sum -c SHA256SUMS)
curl --fail "https://static.crates.io/crates/spatial-typestate/spatial-typestate-$version.crate" -o registry.crate
cmp "evidence/spatial-typestate-$version.crate" registry.crate
```

Also download the three PyPI files using the new version's public JSON URLs and
compare EACH with the Release set, and retain the Integrity API objects. Verify
JSON metadata and the PyPI UI online as above. Save those observations, the exact
identity and independently fetched trusted roots. Do not trust roots supplied
only by the artifact distributor. Transfer the saved set to the disconnected site.
No later offline command proves the current live registry/UI state.

For each file offline, run the following using the trusted `version` and `commit`:

```sh
set -eu
cd evidence
repo=TelemetryWorks/spatial-typestate
workflow="$repo/.github/workflows/trusted-publishing.yml"
sha256sum -c SHA256SUMS
for file in "spatial-typestate-$version.crate" \
  "spatial_typestate-$version-cp311-abi3-manylinux_2_28_x86_64.whl" \
  "spatial_typestate-$version-cp311-abi3-win_amd64.whl" \
  "spatial_typestate-$version.tar.gz"; do
  kind=python
  if [ "$file" = "spatial-typestate-$version.crate" ]; then kind=crate; fi
  gh attestation verify "$file" -R "$repo" --bundle "$kind.provenance.sigstore.json" \
    --custom-trusted-root ../trusted_root.jsonl --signer-workflow "$workflow" \
    --source-ref "refs/tags/v$version" --source-digest "$commit" --deny-self-hosted-runners
  gh attestation verify "$file" -R "$repo" --bundle "$kind.sbom.sigstore.json" \
    --custom-trusted-root ../trusted_root.jsonl --signer-workflow "$workflow" \
    --source-ref "refs/tags/v$version" --source-digest "$commit" --deny-self-hosted-runners \
    --predicate-type https://cyclonedx.org/bom --format json > "$kind.verified-sbom.json"
  if [ "$kind" = python ]; then
    for bundle in "$file".publish-*.sigstore.json; do
      gh attestation verify "$file" -R "$repo" --bundle "$bundle" \
        --custom-trusted-root ../trusted_root.jsonl --signer-workflow "$workflow" \
        --source-ref "refs/tags/v$version" --source-digest "$commit" --deny-self-hosted-runners \
        --predicate-type https://docs.pypi.org/attestations/publish/v1
    done
  fi
done
python3 - <<'PYBOM'
import json
from pathlib import Path
for kind, name in [('crate', 'core'), ('python', 'python')]:
    results = json.loads(Path(kind + '.verified-sbom.json').read_text())
    boms = [r['verificationResult']['statement']['predicate'] for r in results]
    local = json.loads(Path(name + '.cdx.json').read_text())
    if local.get('bomFormat') != 'CycloneDX' or not boms or any(b != local for b in boms):
        raise SystemExit('SBOM bytes do not describe the verified predicate')
PYBOM
```

Checksums detect corruption, not authenticity. Successful signature/identity
verification binds subjects to hashes; the SBOM comparison authenticates its
parsed content. The signed workflow claims are not proof of code safety,
reproducible Python binaries, review or a SLSA level. Cargo reproducibility here
means the checked archive comparisons only, not arbitrary-machine reproducibility.

### Path B: registry downloads and online attestation lookup

Without Release assets, fresh-download the crate from static.crates.io and the
three Python files from the version's PyPI JSON URLs. Inspect the crate VCS SHA,
wheel/sdist `_provenance.json` clean SHA/source inventory, canonical filenames,
public checksums and licence/URL metadata. For EACH of the four files:

```sh
# Set file, repo, workflow, version and commit to independently reviewed values.
mkdir -p online-provenance online-sbom
(cd online-provenance && gh attestation download "../$file" -R "$repo" --predicate-type https://slsa.dev/provenance/v1)
(cd online-sbom && gh attestation download "../$file" -R "$repo" --predicate-type https://cyclonedx.org/bom)
gh attestation verify "$file" -R "$repo" --signer-workflow "$workflow" \
  --source-ref "refs/tags/v$version" --source-digest "$commit" --deny-self-hosted-runners
gh attestation verify "$file" -R "$repo" --signer-workflow "$workflow" \
  --source-ref "refs/tags/v$version" --source-digest "$commit" --deny-self-hosted-runners \
  --predicate-type https://cyclonedx.org/bom --format json > verified-sbom.json
```

Recover SBOM JSON only from successful verification output, as in Path A, never
from an unverified bundle. Keep each downloaded digest-named `.jsonl` set in its
own directory for later offline use.
For Python also fetch each Integrity API object; use reviewed/hash-locked
pypi-attestations tooling to verify the public file, then enforce the exact
certificate claims with `release_integrity.py` (not only the repository default).
For example, with the hash-locked verification dependencies already installed and
`reviewed_checkout` pointing to independently reviewed source (never an arbitrary
downloaded script), set `file` to each fresh canonical Python file and
`provenance` to its saved Integrity API JSON, then run:

```sh
PYTHONPATH="$reviewed_checkout/.github/scripts" python3 - "$file" "$provenance" "$version" "$commit" <<'PYPEP'
import json
from pathlib import Path
import sys
from release_integrity import verify_file
file, provenance, version, commit = sys.argv[1:]
verify_file(Path(file), json.loads(Path(provenance).read_text()), version, commit)
print('Verified PEP 740 publisher, certificate claims and file digest')
PYPEP
```

The workflow's output retains both original API objects and converted verified
Sigstore bundles for Path A. Library offline mode only disables TUF refresh;
provision its cache independently or use Path A's explicit trusted-root route.
Finally consume crates.io `=X.Y.Z` in outside-checkout std and no_std-library
consumers, and install the real PyPI wheels into clean supported environments.
A no_std library consumer using a std binary is not a bare-metal runtime proof.
The scope remains Windows/manylinux x86_64, GIL-enabled 3.11/3.14; no broader
platform, universal glibc, signed historical 0.1.0 or Python reproducibility claim.

References actually inspected for this implementation:
[pinned irig106-types workflow](https://github.com/TelemetryWorks/irig106-types/blob/2899b30/.github/workflows/trusted-publishing.yml),
[its approval/verification guidance](https://github.com/TelemetryWorks/irig106-types/blob/2899b30/docs/RELEASING.md),
[Cargo publish](https://doc.rust-lang.org/cargo/commands/cargo-publish.html),
[PyPI producing](https://docs.pypi.org/attestations/producing-attestations/),
[consuming](https://docs.pypi.org/attestations/consuming-attestations/),
[pypi-attestations 0.0.31 source](https://github.com/pypi/pypi-attestations/blob/bc6dbbed18090a51a97e7eef6d5afc30077740b3/src/pypi_attestations/_impl.py),
[GitHub verification CLI](https://cli.github.com/manual/gh_attestation_verify).


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

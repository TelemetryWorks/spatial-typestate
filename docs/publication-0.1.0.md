# Historical exact-artifact publication: 0.1.0

## Completed release and superseding future policy

Rust 0.1.0 was published on 2026-11-08 and Python 0.1.0 on 2026-11-09 UTC
(2026-11-08 local time). The owner superseded the hosted plan below with local
publication. Existing Cargo authentication published the exact qualified crate;
local maturin uploaded the exact two wheels and canonical sdist using a token.
Fresh public downloads matched all four qualified hashes, independently verified.
Both release tags point at C2 and must never be moved. Python 0.1.0 has **no public PyPI
attestations**; embedded `_provenance.json` is a separate unsigned source record.
Do not re-upload 0.1.0 or describe it as Trusted Published/attested.

**Every future PyPI upload must follow the [mandatory Trusted Publishing plus
per-file PEP 740 policy](RELEASING.md#mandatory-future-pypi-publishing-policy).**
Missing publisher setup or attestations blocks release; no local/token fallback.
The old `publish-0.1.0.yml` was never dispatched and remains disabled and retired.
Its password input and `attestations: false` are historical, noncompliant tooling,
not a template: never re-enable or copy it. No new publishing workflow or PyPI
Trusted Publisher configuration is approved by this document.

The original reviewed hosted route below is retained as superseded planning
history, not active execution instructions or permission to obtain credentials.

On 2026-11-08 the owner approved publication of the four qualified **final 0.1.0**
artifacts, with Python minimum 3.11 unchanged. This supersedes the qualification
bundle's historical `publication_approved=false`; it does not change those bytes
or rewrite the original qualification records.

Source is **9974fd6a00521d631d6ff6e35d4aa936f6b624cf (C2)**. Qualification tooling
was **3f17f85b9eb6ffc50f69db3980877e9668ff04fb (Q)**, manual run 42508333524.
Publication tooling R is separate. Neither Q, R nor moving main is the tag target.
The exact filenames/hashes are in [the qualification plan](candidate-qualification-0.1.0.md)
and its external LF manifest. The qualified crate SHA256 is
`fc6b60a9a7f3aa44122e51473cbe52026ae6330826b15401610489ca0b355abf`.

## Superseded hosted route and least privilege (historical)

The manual-only, no-input workflow requires main, run attempt 1, and one-time
variable `PUBLICATION_0_1_0=approved-9974fd6-once`. Activate only after exact-head
review, normal protected merge/post-CI and credential setup. Remove the variable
after the first attempt, successful or failed. No automatic upload retry,
skip-existing, force overwrite, custom registry uploader or artifact rebuild
substitution is permitted.

1. A credential-free preflight reads public owners and registry absence, verifies
   all four downloaded hashes, and reproduces the exact qualified crate on Linux
   with Rust/Cargo 1.99.0 from clean C2. Locked/default package verification and
   exact fc6b60a9 hash/VCS guards must pass **before any registry upload**.
2. PyPI receives exactly the two original wheels and canonical Linux sdist through
   the official PyPA action, pinned at peeled v1.14.3 commit
   `7245906fb61fa33a13554f9d5fb856fe61758086`. Metadata checking remains enabled;
   no repository override, skip-existing or attestation claim. The actual
   public three-file metadata/download hashes must pass before Cargo starts.
3. A separate Linux Cargo job repeats the clean C2/package/hash guard immediately
   before official `cargo +1.99.0 publish --locked --jobs 2`, with default verify.
   Cargo repackages; both the published index checksum and fresh download must
   equal the qualified hash. A mismatch is a stop, never a republish; any yank
   requires a separate owner decision.
4. Credential-free jobs freshly download/hash the public files, install the
   public Python wheels in clean Windows/Linux 3.11/3.14 venvs, run the installed
   suite and synthetic lab outside checkout, and compile/run registry Rust
   consumers. The std/no_std consumers are hosted std binaries selecting the
   library mode, not device runtime or full API coverage.
5. Only after both registries' exact bytes verify, create immutable
   `rust-v0.1.0` and `python-v0.1.0` tags pointing at C2. Do not move/delete an
   existing tag. GitHub release notes/manifest can be prepared separately.

Every job has contents:read; artifact download jobs additionally actions:read.
No workflow step has contents:write or handles both registry credentials.
`CARGO_REGISTRY_TOKEN` is exposed only to the official Cargo publish step;
`PYPI_API_TOKEN` only to the official PyPA action. SONAR_TOKEN is never used.

## Superseded hosted credential and failure boundary (historical)

Public crate owner is `joey-huckabee`, matching the authenticated GitHub login.
This is identity evidence, not proof that a supplied token has publish rights.
The existing local Cargo credential file was checked for presence only, never
read/exported. No undocumented permission-probe endpoint is assumed.

Use a short-lived crates.io token scoped to publish-update for spatial-typestate.
PyPI Pending Trusted Publishing is preferable if the owner configures it; the
reviewed token route instead needs a one-time account-wide token because the
project does not exist yet. Revoke that token immediately after use and delete
the GitHub secret. That historical choice does not authorize future token uploads;
the mandatory Trusted Publishing and attestation policy above supersedes it.
Credentials are supplied through the secure request mechanism,
never chat, files in Git, argv or logs. No local tool installation is needed.

PyPI 404 does not reserve the name or prove upload permission. Its first accepted
file creates the release. A partial PyPI upload or later Cargo failure therefore
means a partial public release: stop, inspect public file/version state and
report it. Never blindly retry/re-upload accepted files or reuse a version.
Bounded public GET polling is only for propagation, never upload retry.

After publication, retain public URLs, hashes, actual runtime evidence and tag
objects in a dated audit; availability documentation follows normal protected PR
review. Qualification limits remain: x86_64 GIL-enabled Python 3.11/3.14; 3.12/3.13
metadata-only; glibc 2.28/2.36 containers are not universal-host proof; no macOS,
musl, ARM or free-threaded claim. Artifacts/provenance are unsigned. Two accepted
operator risks and one sanitised false positive remain documented.

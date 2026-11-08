# Frozen 0.1.0 candidate qualification

Plan recorded on 2026-11-08, before the manual run. Actual qualification outcomes
and the crate hash belong to the external manifest, not a self-updating source
commit. Artifact preparation is authorized; publication is not. No tag, registry upload
or GitHub release is created by the manual qualification workflow. Its results
need exact-artifact review before a separate publication decision.

## Frozen source and selections

The candidate source is **9974fd6a00521d631d6ff6e35d4aa936f6b624cf** (C2).
Core, Python distribution and private native crate each say 0.1.0; these are
independent versions. The initial d0922de selection was superseded because the
core manifest's package exclusions changed, not relabelled as C2.

Python artifacts come only from successful push run **42505032821**, attempt 1,
at C2. Their source identity is
`9c5b2f7c362afb06671fe5a5b8b6edf58aa86db87c721437dd719e45b023fa44`.

| Selected file | GitHub artifact ID | SHA256 |
| --- | --- | --- |
| spatial_typestate-0.1.0-cp311-abi3-manylinux_2_28_x86_64.whl | 13626802673 (Ubuntu 3.11) | e591cc87071cdc7db9e1ff162d11d661f1e6854ab1c6cfbf96473cde7e57ebd5 |
| spatial_typestate-0.1.0.tar.gz | 13626802673 (canonical Linux sdist) | d94f841d8ab4368de4994b071f9d035fe5260feba2e50157200a9467d51e9448 |
| spatial_typestate-0.1.0-cp311-abi3-win_amd64.whl | 13627490908 (Windows 3.11) | b59ead8787b870d28f0aba2b7bd8264a993e2dfa93ca3fa9d3a5d249254c12c8 |
| spatial-typestate-0.1.0.crate | Created by manual qualification from C2 | Recorded in the external manifest; never substitute a PR checkout's archive |

Source artifacts expire on 2026-11-22 and have been downloaded with their original
GitHub archive digests verified. The external unsigned release manifest must
retain the selected files, hashes, run/attempt/IDs, source/build records, both
lock hashes, licenses, package inventories and qualification evidence. It must
not contain its own hash. Equal source identity does not imply equal binaries.

## Evidence already retained at C2

The selected Linux wheel's hash appears in all four runtime records: CPython
3.11.18 and 3.14.10, each at glibc 2.28 and 2.36 in the pinned images. The same
Ubuntu artifact contains the Git-free sdist rebuild, matching source blocks,
static metadata/license parity and four runtime records for that rebuilt wheel.
That rebuilt wheel is evidence, not another selected release wheel. Prepared
metadata, RECORD, native path/ELF checks and compiler notices passed in source CI.
The source run's other matrix wheels and Windows sdists are not selected.

These containers use the runner kernel and are not minimal hosts; no universal
Linux, musl, other architecture, macOS or free-threaded claim follows. Python
3.12/3.13 are metadata-permitted but not this qualification's runtime matrix.

## Manual qualification gates

The workflow is manual-only with no inputs, fixed source/artifact/hash literals,
read-only permissions and no publication credentials. Its reviewed tooling
commit **Q differs from C2**: Q adds qualification tooling, not candidate source.
The workflow checks out C2 explicitly and records both identities. Any separately
approved future release/tag must identify C2 and these exact artifacts, not Q or
moving HEAD. Changing candidate source requires a fresh reviewed selection.

- Windows 3.11 and 3.14 consume the **same selected 3.11-built wheel**, after
  verifying its hash. Fresh venvs have no system site packages. Installed
  provenance/version and site-packages import origin are checked. Tests and the
  synthetic lab run from outside the checkout, first without NumPy, then with
  the existing hash-locked test-only NumPy dependency. No wheel is rebuilt.
- The crate job checks clean C2, runs locked `cargo package` with its default
  verification and no dirty/no-verify bypass, checks the actual 68-file archive,
  original manifest/source bytes/licenses/lock/VCS identity, then runs std and
  no-std consumers against the **unpacked archive**. Cargo metadata proves the
  dependency resolves there. Cargo's absent optional dirty flag is allowed only
  alongside the clean-checkout checks; dirty:true is rejected.
- Logs and exact selected files are retained for 30 days. Failed-job uploads
  are diagnostics only; success requires all jobs passing and complete reports.
  No scan, build or signature is an attestation of vulnerability-free software.

After the manual run, the reviewer checks the actual hashes and reports. A small
external qualification report records results without a self-referential source
commit update. Publication and its credentials remain a separate task under
[the release gates](RELEASING.md).

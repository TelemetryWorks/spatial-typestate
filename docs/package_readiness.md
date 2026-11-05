# Package-readiness design (no publication)

Scope: embedded build evidence, Linux compatibility and inspectable dry-run
artifacts. Core source/API/dependencies/pin/MSRV and all package versions remain
unchanged. No tag, upload, registry credential or new runtime helper/API is added.

## Provenance ownership and records

Use an in-tree, stdlib-only PEP 517 backend, delegating compilation/metadata to
the already pinned maturin 1.16.0. Direct maturin CLI builds bypass this backend
and are therefore not readiness artifacts; documented commands/CI use the backend.
The wrapper owns final archive construction and regenerated wheel RECORD entries.
It delegates from an isolated temporary source staging tree (excluding targets,
Git internals and unrelated files), injects resources after compilation, and
leaves no trusted generated file in the checkout. No general maturin pre-build
hook is assumed. Staging preserves source bytes/logical paths and is checked
against the original inventory; source identity is collected before staging.

The package resource is spatial_typestate/_provenance.json, read with
importlib.resources (no new import-time behavior or native API). Schema 1 separates:

- source: core/Python/native versions, root/native lock hashes, normalized source
  file inventory and aggregate SHA256, Git base commit or null and state
  clean/dirty/unknown. A dirty commit identifies only the base, not all built bytes.
- build (wheel only): actual rustc/cargo versions and target, backend version,
  CPython build interpreter version, release profile/features, locked setting,
  path-remapping policy, compatibility request and actual final wheel tags.
- artifact_kind: sdist or wheel; no release=true assertion.

Wheel records also name source_origin (checkout/sdist), wrapper schema/version
separately from maturin version, and actual warning-denial setting.

Sdist provenance contains source identity only, never a claim about the later
compiler. Extracted builds recompute that identity against the vendored core,
native source and locks, then record their own actual compiler/config. No Git is
needed. Mismatch fails before compilation; it cannot fall back to registry core
or a newer Git checkout. Development/no-Git states are explicit, never release signoff. Editable builds
are explicitly rejected: immutable temporary staging cannot provide a durable
editable path. Rebuild/install a development wheel instead; each wheel build
uses a fresh temporary source tree and can force recompilation despite a target
cache, so the development loop is slower than maturin develop. An existing generated wheel record is not accepted as a source record.

The source inventory uses sorted POSIX logical relative paths (core/, native/,
package/, backend/, licenses/), disallowing traversal/symlinks. It covers all core
and native .rs files, their manifests and locks, Python facade/stubs, backend,
license texts, and effective pyproject configuration. Known maturin relocation
of manifest/package paths is canonicalized; other config changes must fail.
Text is explicitly .rs/.toml/.lock/.py/.pyi/.md/.txt, py.typed and the enumerated
license/notice files; non-UTF-8 or lone CR fails. CRLF is normalized to LF with no
other whitespace alteration. A compile-input guard rejects build.rs,
include_str!/include_bytes!/env!/option_env! or externally redirected source paths
until their input inventory is deliberately extended; none exists today.
Each entry hashes those normalized bytes. Aggregate hash is SHA256 over canonical
JSON of the sorted path->hash map (UTF-8, sorted keys, compact separators).
This is a source-content identity, not a hash of every documentation/test file.
Tests cover CRLF equivalence, changed source/locks/config, missing/extra source,
stale records, unknown/dirty identity and deterministic controlled fixtures.

For sdist creation, compare the canonical inventory of the source tree with the
relocated archive; reject unexpected changes, then insert the source resource.
At wheel build, validate a frozen sdist source resource if present; otherwise
derive fresh source identity from the checkout. Compare before/after compilation.
Frozen source records require PKG-INFO and no project-root .git directory/file.
A leftover frozen resource in a real checkout fails; it cannot override Git.
Valid sdist records take priority over a surrounding parent repository. Otherwise require git
rev-parse --show-toplevel to resolve exactly to the project root (not a parent
repository). Normal checkouts and worktrees (.git file) are both supported.
Failure/dubious ownership yields unknown for development, never an adopted
environment-provided revision. Git cleanliness includes untracked source.
Readiness CI additionally requires clean state and commit equal to the checked-out
expected SHA, failing on unknown/dirty. Checkout explicitly selects the PR head
SHA (not github.sha's synthetic merge ref), or the push SHA, before building.

Records contain allowlisted fields only: no timestamp, hostname, absolute path,
user name or arbitrary environment dump. They are descriptive evidence, not a
signature or tamper-proof attestation: an attacker replacing both code and record
can forge an unsigned package. Final artifact hashes live in a separate external
inventory, avoiding a self-hash cycle and self-referential commit claims.

## Package hygiene

Native build-only path remapping removes checkout/Cargo-home/Rustup-home prefixes
from dependency/panic location strings without changing arithmetic flags or the
repository core build policy. Scan the compiled binary as well as JSON/text for
local user/checkout paths; fail rather than silently claim successful cleanup.
No fast-math, unsafe or optimization is introduced. The wrapper sets the complete
CARGO_ENCODED_RUSTFLAGS list, not merely additive-looking RUSTFLAGS: checkout
builds explicitly retain -Dwarnings because environment flags replace Cargo
config flags. Extracted source builds omit that development policy unless CI
explicitly requests denial; the boolean is recorded. Reject unaccounted external
flag overrides rather than silently discard them. A warning-producing compile
fixture must fail under the checkout flag policy. The path scan tests actual
checkout/home/Cargo/Rustup prefixes (including binary PDB records), generic user
patterns and planted leaks; paths used for scanning are not embedded in JSON.

Disable maturin's auto-generated local-path/timestamp SBOM using its own
[tool.maturin.sbom] rust=false setting;
replace it with a versioned third-party notice/license inventory derived from the
locked graph. Include Apache-2.0 project license plus all applicable dependency
license/notice texts (including Unicode and LLVM-exception terms), not only a
License-Expression. Use project.license-files under python/, with matching paths
in the relocated sdist; let maturin own License-File/METADATA generation. Test
prepare_metadata/build_wheel parity. Only provenance injection needs wheel
postprocessing; recompute RECORD and verify every member's hash/size.
Obtain crate texts from the locked, checksum-verified Cargo sources without a new
tool; fail if the notice inventory differs from Cargo.lock. Distinguish runtime
crates from build/proc-macro-only crates. Include actual compiler-distribution
Rust std/bundled-component license notices with each wheel and record their
version/hash separately (not in the sdist source inventory). Inject the actual
installed compiler's COPYRIGHT-library/licenses texts as _compiler_notices
package resources beside provenance, not compiler-dependent License-File headers.
Thus sdist PKG-INFO and rebuilt wheel METADATA retain identical static license
fields even with a different rebuild compiler. Missing rust-docs notices are
explicitly unavailable in development records; readiness checks fail. CI installs
the exact toolchain's rust-docs component. Do not commit generated compiler
notices or treat them as source identity. Record license/source
hashes externally and test contents. No legal certification claim is made.

Sdist preserves actual core/native source, manifests/locks, Python package/backend
and licenses. Omit the development rust-toolchain.toml and .cargo/config.toml from
the archive, avoiding implicit toolchain installation and downstream new-warning
failures; this does not alter either repository file or CI warning-denial policy.
Omit agent instructions, tests, scripts and unrelated docs/evidence. Retain any
explicit Cargo target files required for manifest validity. Verify Python README
content is not accidentally replaced by the path-dependent core's README.
Downstream source builders select an installed compiler meeting MSRV; CI always
selects 1.99 explicitly. Record that actual compiler, not the sdist creator's.

## Linux baseline and evidence

Recommend manylinux_2_28_x86_64 (glibc >= 2.28), a supported AlmaLinux 8-based
manylinux image rather than a mutable ubuntu-latest build environment. This is
deliberately narrower than Rust's x86_64 GNU minimum glibc 2.17; it excludes older
glibc hosts rather than implying those have been tested. It avoids choosing the
older CentOS 7-based baseline solely for a broader tag. No musl/other architecture,
macOS or free-threaded support is added. 3.11/3.14 GIL-enabled CPython remain CI
versions; Windows jobs remain intact; local 3.12 evidence remains local.

Registry manifest bytes independently SHA256-verified on 2026-11-04:

- quay.io/pypa/manylinux_2_28_x86_64@sha256:7e41b1c7fd64dfc69703a1124b43c404382973ee06ec5d764b85c34d2221fded
- python (Linux amd64) 3.11-slim-bookworm@sha256:061c190f3d5815b341a18dfe8a45771f8ba68c15a607ea56997fde3009ac4eec
- python (Linux amd64) 3.14-slim-bookworm@sha256:47d41ea4947601fd5bc7ed6c00a7b9c1fbb936a7684873908a3c3b4e68ce3c86

Use containers only on GitHub runners, never install Docker locally. SHA-pinned
dtolnay/rust-toolchain runs on the host, installing exactly 1.99.0 through rustup's
official distribution manifest/checksum verification, not a mutable curl installer.
Mount that installed x86_64 GNU toolchain read-only at a neutral path inside the
manylinux container; invoke its cargo/rustc directly, without rustup there, and
verify/record actual versions/host and binary hashes. Actions do not run inside
the container. Its Python installs exact maturin from --require-hashes,
--only-binary requirements. The interpreter and build tools are pinned by the
image digest/tool hashes, not assumed to match a mutable runner. Build with
locked Cargo and two workers. Enforce
maturin --compatibility manylinux_2_28 --auditwheel check, then inspect the actual
ELF in the final postprocessed wheel with the image's existing readelf: all
version-need namespaces (GLIBC, GCC, etc.) checked against policy/baseline runtime,
NEEDED libraries allowlisted, expected architecture and final wheel tags. Build a
tiny real ELF using a GLIBC_2.29 symbol on the newer runner, and require the gate
to reject it (plus parser fixtures). No extra auditwheel dependency is needed.
Capture the audit report with external artifact inventory/hashes.

Readiness candidates are separate artifacts per matrix build (their hashes
identify them); no publication artifact is selected here. Each Linux candidate,
including the 3.11 build, runs on BOTH 3.11 and 3.14 in floor/newer containers.
The two Windows jobs currently build/test distinct candidates on their own
interpreter; this is not a same-binary cross-interpreter Windows claim.
The readiness Linux wheel is built in manylinux, not the former Ubuntu-native
wheel. Install those exact wheel bytes into a NEW container from the pinned
manylinux digest for each CPython 3.11/3.14 run, asserting runtime glibc ==2.28.
This is a fresh floor test in a build image with development tools, not a minimal
host. Also run the corresponding pinned Bookworm Python images, asserting glibc
==2.36: they provide one newer baseline, not two different glibc generations.
Use no source/build mounts on the import path. Run installed-package,
stdlib batch and lab tests; test code/fixtures can be copied separately. Check
actual runtime glibc/Python versions and no unexpected runtime dependencies.
Use an extracted sdist without Git, rebuild via the backend, compare source
identity and its new build record, install and test. This provides measured
floor/newer-container evidence, not proof for every glibc distribution or kernel.
The container host kernel is newer; no old-kernel runtime claim is made.

## Checks and handoff

Before implementation: coordinator/reviewer agree record/state semantics and
baseline. Then focused backend/archive/ELF-gate tests, actual local Windows wheel
and extracted-sdist build/install, license/content/path/hash inspection and lab
behavior. Core package --locked verification runs from a clean committed tree,
not --allow-dirty. CI validates both lock graphs, all existing core gates and all
four Python jobs plus container/source checks. Parse changed workflow YAML before
push and inspect every returned context before merge. Independent exact-head
approval and successful post-merge CI remain delivery requirements.

Artifact inventory lists filename, kind, SHA256, size, source identity, wheel tags,
license/stub/provenance presence and ELF inspection where applicable. No claim of
bit-identical rebuilds; hashes identify actual outputs. Publication still needs
a separate owner-approved exact artifact/version/release task.

Primary references: [PEP 517 in-tree backends](https://peps.python.org/pep-0517/#in-tree-build-backends),
[maturin distribution/audit](https://www.maturin.rs/distribution.html),
[maturin configuration](https://www.maturin.rs/config.html),
[PEP 600](https://peps.python.org/pep-0600/),
[manylinux image/status](https://github.com/pypa/manylinux),
[Rust target requirements](https://doc.rust-lang.org/rustc/platform-support.html).
The installed 1.99.0 rustc documentation independently lists kernel 3.2+/glibc
2.17+ for x86_64-unknown-linux-gnu; wheel checks still measure the actual output.

Python artifact CI explicitly checks out the PR head for source commit identity,
whereas core CI retains merge-ref testing. Before merging, the feature branch must
include current main; if main advances, merge it into the feature branch and
retest/review that new head, without rewriting published history.

Maturin 1.16's prepare hook hardcodes a native Linux tag even with an explicit
manylinux request (tags_from_bridge in the linked upstream source). The wrapper
projects only the exact cp311-abi3-linux_x86_64 prepared Tag line to the explicit
manylinux_2_28_x86_64 request, on Linux only. Other tags/counts fail loudly. This
is intent, not binary evidence: final wheel tags remain maturin/build/audit output,
and the strict prepared-file and ELF gates independently verify them. License
METADATA is untouched. Diagnostic uploads from failed jobs/attempts are not
readiness evidence; require successful exact-head jobs and artifact review.

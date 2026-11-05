# Versioning, compatibility and release gates

This policy defines future procedure, not publication authorization. No version,
tag, registry upload or new platform support is created by adopting it. An owner
must assign a separate release task and approve the exact artifacts/versions.
There is no automated publishing workflow or promised release schedule.

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

Current wheels have distribution version metadata but **no public embedded core
commit/build-info API**. A path dependency/version alone does not identify an
unpublished core revision. The following is a mandatory future release gate,
not a claim about metadata already shipped:

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
not imply compatibility with legacy 0.0.1; the owner selects the version during
the release task. This recommendation does not change current 0.0.2.

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

The CI Linux wheel is evidence of import on its runner, not a manylinux-baseline
or broad Linux-distribution promise. A publication task must explicitly choose
wheel tags/glibc baseline, test compatible clean environments and align docs with
actual artifacts before upload. Do not expand support by changing metadata alone.

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
7. Only after explicit owner artifact approval, perform assigned tag/upload
   actions. Registry credentials stay out of Git/logs. Re-download the published
   artifacts, verify hashes, install/build and smoke-test the public artifacts.
   Verify release manifest links before announcing availability.
8. On a defective published artifact, document impact and issue a new version;
   consider registry yanking with owner authorization rather than replacing a
   version. No automatic rollback, deletion or publishing credentials are set up.

Publication is still blocked on a separately assigned release task, the provenance
resource gate and explicit wheel baseline/artifact decisions. Adopting this policy
does not implement those gates or promise a first publication date.

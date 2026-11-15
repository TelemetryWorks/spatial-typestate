# Supply-chain rollout — 2026-11-15

Scope: spatial-typestate workflows/docs and the explicitly assigned Dependabot
configuration. Base main: `82f0736271789b9b33e78053302fb9e9a205c358`.
No publication, settings, version, lockfile or runtime change. PR #25's separate
roadmap work is not included in this branch.

## Reference and execution boundaries

Read the irig106-types pilot at [8bc3c9a](https://github.com/TelemetryWorks/irig106-types/tree/8bc3c9a),
including its Scorecard/zizmor workflows and dated pilot report. Compare the
[official Scorecard template](https://github.com/ossf/scorecard/blob/main/.github/workflows/scorecard-analysis.yml)
and the [pinned zizmor action contract](https://github.com/zizmorcore/zizmor-action/blob/45d7276c9ca790aabd705e31ca99c6185c3e76dd/action.yml).

- Scorecard runs weekly and on main pushes only, with `publish_results: true`.
  Its template requires top-level `read-all` (the explicit exception to the
  repository's contents-read default). Its analysis job grants only contents
  read, security-events write and id-token write. OIDC here publishes Scorecard
  results, not packages. SARIF is retained for five days and uploaded to code
  scanning. No PR checkout runs with these write permissions.
- zizmor runs on PRs to main touching `.github/workflows/**`, audits the entire
  workflow directory, and fails on regular-persona findings. It uses version
  1.32.0 and the SHA-pinned action, with online audits and read-only token;
  `advanced-security: false` selects failing audit mode without SARIF write scope.
- Dependabot checks Actions, root Cargo and `/python/native` (the actual separate
  Python Cargo manifest) weekly. Each entry permits five open PRs, groups only
  minor/patch updates and uses `chore(deps)` commits. Major updates remain separate;
  review, compatibility and required checks still apply. This does not authorize
  dependency upgrades or automatic merging.

## Complete direct-action inventory

Read-only upstream commit/tag APIs resolved all 12 distinct repository/commit
pairs below, including annotated tag peeling. Every `uses` in all eight workflows
has a full 40-character SHA and version comment. Existing pins are unchanged;
new Scorecard/zizmor steps use the pilot/template's pins.

| Repository | Version comment | Pinned commit |
| --- | --- | --- |
| SonarSource/sonarqube-scan-action | v8.4.1 | `e805d875275f728fac1885b413934be6d7c63f65` |
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| actions/checkout | v6 | `d23441a48e516b6c34aea4fa41551a30e30af803` |
| actions/download-artifact | v5 | `634f93cb2916e3fdff6788551b99b062d0335ce0` |
| actions/setup-python | v6 | `ece7cb06caefa5fff74198d8649806c4678c61a1` |
| actions/upload-artifact | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| actions/upload-artifact | v4.6.2 | `ea165f8d65b6e75b540449e92b4886f43607fa02` |
| dtolnay/rust-toolchain | v1 | `683b588c487a69d01f6c6ddf40f036ff682cc2c8` |
| github/codeql-action | v4.39.3 | `33d7b85da1a04171e211befe2c739303b9a4c066` |
| ossf/scorecard-action | v2.5.0 | `fa7117db83c52d787ae5a89f350999701505d78e` |
| pypa/gh-action-pypi-publish | v1.14.3 | `7245906fb61fa33a13554f9d5fb856fe61758086` |
| zizmorcore/zizmor-action | v0.8.1 | `45d7276c9ca790aabd705e31ca99c6185c3e76dd` |

All checkouts now have `persist-credentials: false`. All workflow-level
permissions are contents read except Scorecard's documented read-all. Existing
job grants remain: CodeQL security-events write; qualification/publication
artifact consumers actions read; all other existing jobs inherit contents read.
No new package-publishing capability or required-check rename is introduced.

## Findings and narrow exceptions

Initial offline regular-persona audit: five credential-persistence findings
(four Rust jobs, one Python job), fixed by disabling checkout persistence; two
Trusted Publishing findings in the retired publisher. Online auditing also
identified stale `master` version comments in CodeQL/Sonar. The pinned Rust action
is tag `v1`; comments now match, without changing the commit or toolchain.

Exactly two inline `use-trusted-publishing` suppressions document historical token
steps in `publish-0.1.0.yml`. Its live state was verified `disabled_manually`.
It remains retired and must never be enabled or copied. Suppression preserves a
historical file; it does not approve token publishing. Future publishers must meet
[the release policy](../RELEASING.md); a new `trusted-publishing.yml` is outside
this PR. No repository-wide suppression or severity/persona filter is added.

Sonar's sole change is the Rust action version comment. Removal, full scan,
180-second deadline, prunes, credential isolation, probe, collector and gate are
unchanged. No security-hardening exception is added to Sonar.

## Local validation and pending hosted evidence

On the cloud aarch64 host, existing-source static checks only:

- actionlint 1.7.12: all eight workflows pass its workflow/expression checks.
  Shellcheck and pyflakes are not installed; those optional integrations were
  not claimed as executed.
- zizmor 1.32.0 regular persona: offline and online audits both pass with zero
  unsuppressed findings; online used only the existing read-only CLI session.
- All direct-action pin/tag identities and both new action input contracts
  checked against upstream APIs. LF, local documentation links and
  `git diff --check` checked separately.

These are local results, not hosted CI PASS claims. Normal PR checks (including
zizmor and existing required gates) must run on the exact review head. Scorecard
publishing, its first badge value, OIDC issuance and SARIF upload cannot be
established by a local audit or this PR event; verify after an authorized merge's
main/scheduled run. No score, settings change or package attestation is claimed.

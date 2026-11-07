# Security analysis restoration

Configuration checkpoint, 2026-11-05. No scan result is inferred from workflow
success or absence of alerts. Core math/API, dependency graphs, pin/MSRV/no_std
and Python provenance contracts stay unchanged.

Update 2026-11-07: CodeQL was restored in PR #9. The hardened Sonar workflow is
present for a reviewed first run with organization telemetryworks and project
spatial-typestate in repository variables and SONAR_TOKEN as a secret. Sonar is
NOT restored until actual analyzer/import/gate evidence passes review. The
[probe delta](sonar_probe_plan.md) supersedes the historical owner-setup wait
below; user authorization permits the first real scanner attempt.

## Verified baseline and access boundary

- Clean main e22e269; CodeQL/Sonar workflows both disabled_inactivity.
- Last CodeQL analysis: 2026-03-02, old 2f8b4110 source, Rust only, 25 rules,
  zero results. No current-source or Python/Actions conclusion follows.
- Default CodeQL setup is not configured; use existing advanced workflow.
- Zero repository secrets/variables and zero organization secrets exposed to
  this repository. Organization secret administration returns HTTP 403.
- Public Sonar organization telemetryworks lists four projects, not this repo;
  expected TelemetryWorks_spatial-typestate returns HTTP 404. A different/private
  project cannot be ruled out without owner access. Old Sonar runs failed and
  logs expired; the unconditional scanner verification after gated installation
  is a configuration bug inferred from the file, not from recovered logs.

Historical setup requirement: Sonar is **not restored** until the owner confirms/imports the actual project,
its key/organization, grants project-scoped Execute Analysis capability and
securely configures SONAR_TOKEN in GitHub Actions. Project/org identifiers are
non-secret configuration; use repository variables SONAR_PROJECT_KEY and
SONAR_ORGANIZATION. Prefer a project-restricted scoped organization token if the
plan supports it, otherwise a dedicated least-privilege account token restricted
to this project's analysis. Never send tokens in chat or reuse another repo's.
Do not add the token while main still contains the old workflow. Leave
sonarcloud.yml disabled permanently and delete it in the first PR. A hardened
successor must use a new filename/workflow ID; never reactivate the old definition.
Owner must confirm CI analysis method (automatic analysis off), GitHub binding,
quality gate and PR-analysis availability. No billing/access-policy changes are
inferred. Missing access remains a visible blocker, not a passing analysis.

## Proposed CodeQL scope

Restore the existing workflow with verified full action SHAs; use the same
CodeQL commit for init/analyze. Matrix rust, python, actions, build-mode none and
security-extended queries. Rust's supported no-build extractor uses rust-analyzer
and can execute build scripts/macros: no Sonar credentials in that job. Install
explicit 1.99 on hosted runners with two workers. No autobuild or local install.
Use job-level contents:read/security-events:write (actions:read only if needed
for private-repository analysis, which this public repo does not require).
No broad source exclusions, shallow checkout sufficient. Preserve PR/main/manual/
weekly triggers; cancel obsolete PR runs only, preserving main/scheduled evidence.
Keep the existing Rust analysis category stable. Every checkout disables persisted
credentials; no pull_request_target or workflow_run secret processing is used.

Actual extraction evidence must cover src/ and separate python/native/src/ Rust,
the Python facade/backend/tests/examples, and workflow files. Retain SARIF and
database/source inventories, SARIF baseline artifacts and extractor diagnostics
so archived-file counts are not confused with successful semantic resolution.
Count rules across driver and pack extensions; retain per-language results and
all execution/configuration notifications. Record rustc -vV, set RUSTUP_TOOLCHAIN
to override the checkout pin, and install rust-src for rust-analyzer on the runner;
query alerts/analysis metadata at the exact commit. If the Rust extractor misses
the second manifest, correct extraction configuration rather than assume coverage.

The pinned action uses diff-informed analysis for pull_request events: PR finding
results cover changed lines, even when the complete source archive was extracted.
They are not a whole-source baseline. Require a manual full run on the exact PR
head before security-restoration approval, and confirm its SARIF incrementalMode
is not diff-informed. Main pushes, schedules and manual runs provide full scans;
retain their evidence separately from the PR's changed-line results.

## Proposed Sonar scope and trust boundaries

This is a blocked follow-up, not a scan implemented by the first PR. Use three
jobs: configuration check, token-free reports, and scanner. Report
generation runs repository tests/build code without SONAR_TOKEN; scanner runs on
a fresh runner, checks out source with persist-credentials:false, downloads
same-run artifacts to a dedicated directory outside the checkout, copies only
an explicit allowlist of named report files, and does not run
repository scripts. No cross-branch target/cache restore. Token exists only on
the pinned official scanner step (and a narrowly trusted API verification step
if needed), never job/workflow env. Fixed official host URL, project key/org and
qualitygate.wait on owned PRs as well as main/manual runs. Fork PRs get an explicit
notice named "analysis unavailable (fork; not a scan)"; never count it as PASS.
Dependabot PRs also lack repository secrets and get that explicit unavailable
status. Missing configuration on other same-repo/main runs fails. Presence checks
must not echo values. Never use pull_request_target or workflow_run with secrets
on PR data. Same-repository writers can edit workflows: this boundary protects
forks and accidental exposure, not a malicious authorized writer.

Pass the official host https://sonarcloud.io explicitly through the scanner's
command-line -Dsonar.host.url (highest scanner configuration precedence) and
SONAR_HOST_URL. No checked-in property file may set host/proxy/redirection. Keep
scannerBinariesUrl at its official default and skipSignatureVerification false;
verify the pinned action and scanner precedence before enabling the successor.

Use pinned official Sonar action v8 (verified scanner integrity via GPG), replacing
the unchecked scanner zip. Do not install floating sonar-tools or upgrade pip.
Approved: keep Sonar's complete findings/gate authoritative in Sonar, retain API
issue/metric evidence, and use native CodeQL SARIF for GitHub alerts; retire the
unconfigured community SARIF duplication/export path. Sonar findings will no
longer appear in GitHub's Security tab; they live in the Sonar project, with full
issue and security-hotspot inventories retained as evidence. CodeQL findings
remain in GitHub Security. Sonar needs neither security-events:write nor
pull-requests:read; PR decoration uses Sonar's GitHub app (verify project binding).
This must not filter, dismiss or lose issues/hotspots or treat export as a scan.

Analyze repository source (including .github workflows) and classify Rust/Python
test directories explicitly; no rule suppression, broad source exclusions or
Accept/dismissal. Exclude only generated target/coverage/scanner output where
necessary, documenting each pattern; no checked-in source subtree is excluded.
Generated Clippy JSON from both manifests is imported, not disabled. Current
official Cloud Rust docs describe report import rather than automatic Clippy.

Generate actual LCOV for core std/all-features and real no_std, and separate
native manifest tests; verify report file paths include each production source.
The coordinator approved a pinned/hash-locked CI-only Python coverage tool for packaging
controls and installed-wheel facade tests, with explicit path mapping. Native
Rust unit coverage is not claimed to measure every Python-driven FFI call: an
ordinary provenance wheel is not silently replaced with an instrumented/bypassed
backend. Report uncovered binding paths honestly. Verify imported server coverage,
source counts/languages, full issue/hotspot inventory and actual quality gate;
until owner access exists, server-side coverage/gate remain NOT RUN.

## Evidence and delivery

The reviewer approved this scope and retiring the SARIF exporter; the coordinator
approved independent delivery. First PR: restore CodeQL and delete the disabled,
unsafe old Sonar definition. No successor scan or Sonar PASS is claimed. Enable
only CodeQL through a recorded GitHub action; run current source/reviewed head. YAML parse
before push. Focused workflow/source fixes must address actual findings without
weakening policies; unchanged core/Python workflows need no edit.

Record workflow activation, exact run/commit, scanner versions/query counts,
extracted paths/file counts, alerts/issues and coverage. All active/external
checks plus independent exact-head review must pass before merge, followed by
post-merge verification. Sonar access does not hold up the independent CodeQL PR;
state Sonar NOT restored until real analysis and gate evidence pass review.
The successor now proceeds under explicit first-run authorization; record actual
Cloud provisioning/access errors rather than assume Server behavior.
Never manufacture green. No releases/version changes.

Public scheduled workflows can be disabled after 60 inactive days. Document a
maintainer check of workflow activation/last analysis before merging or declaring
security readiness; manual re-enable and a real current-source run are required
after inactivity. No synthetic activity commits or new scheduled service is added.

Primary references: [CodeQL Rust build mode](https://docs.github.com/en/code-security/reference/code-scanning/codeql/build-options-for-compiled-languages),
[CodeQL supported languages](https://codeql.github.com/docs/codeql-overview/supported-languages-and-frameworks/),
[Sonar Rust](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/languages/rust),
[Sonar GitHub action/integrity](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/ci-based-analysis/github-actions-for-sonarcloud),
[Sonar analysis scope](https://docs.sonarsource.com/sonarqube-cloud/managing-your-projects/project-analysis/setting-analysis-scope/setting-initial-scope).

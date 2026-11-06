# Hardened Sonar successor: local design and draft

Status: design checkpoint, not deployed, not a scan. Sonar is **NOT restored**.
Based on clean main 53685087860332e38a6f6553f879b2e9c4399750 after PR #9.
No project/org identity or credential is configured. This work stays uncommitted
locally until the coordinator reviews the publication boundary. No branch,
CodeQL, core/native API, dependency, pin/MSRV, package or release changes.

## Scope and event policy

New file `.github/workflows/sonar-analysis.yml`, never the removed legacy name.
Use pull_request (main/develop), push main, manual and weekly triggers, without
pull_request_target or workflow_run. Only PR runs may cancel older runs. Every
checkout has persist-credentials:false; scanner checkout needs full Git history
for SCM attribution. Reports and scanner use the same explicit PR head (otherwise
github.sha), with its commit recorded. Main must remain current before delivery.

Fork and Dependabot PRs get a job named "Sonar analysis unavailable (not a scan)"
with an explicit summary. Its green completion means notification only and must
not be counted as an analysis PASS. Trusted main/manual/other owned PR events
must fail if configuration is absent, invalid, analysis fails or the gate fails.
No secret or configuration fallback to another project.

## Four jobs and credential boundary

1. Configuration: inline, no checkout. Validate repository variables
   SONAR_PROJECT_KEY and SONAR_ORGANIZATION against a bounded nonempty safe
   identifier alphabet (no whitespace, slash, URL/query or newlines). GitHub
   evaluates `${{ secrets.SONAR_TOKEN != '' }}` into a boolean presence flag;
   this job receives only that boolean, never the token. Missing values fail
   before heavy work. Do not print the token or expose it in job outputs.
2. Reports: repository code may run, but no SONAR_TOKEN is available. Explicit
   Rust 1.99.0 / two workers / warning denial; generated reports live outside the
   checkout. Run focused offline pipeline controls here as well.
3. Scanner: fresh hosted runner, no checked-out executable scripts/actions. Use
   only pinned official actions and reviewed inline validation/configuration.
   SONAR_TOKEN is passed only to the pinned official scanner step, never to a
   shell command, job environment or API collector. No shared target/cache.
4. Public server evidence: separate token-free job, so inventory collection
   cannot accidentally inherit scanner credentials. Query only the fixed public
   Sonar host. If the project/API is not publicly readable, evidence is blocked,
   not silently omitted; request a reviewed access decision before widening the
   credential scope. Run on gate failures too when a report-task artifact exists.

The extra evidence job strengthens separation relative to the earlier three-job
outline. Official action v8.4.1 only warns when SONAR_TOKEN is absent; therefore
its warning is NOT our configuration gate. The boolean presence check above is
required. Forks/Dependabot are classified before that check.

Classify Dependabot from the PR author/head repository, not github.actor (which
changes on re-runs). Missing/expired configuration fails loudly once deployed;
the project owner is responsible for token renewal. Do not publish this scheduled
fail-closed draft while setup is missing: a red Monday run is not useful evidence.

Same-repository writers can edit workflows. This protects forks and accidental
exposure, not a malicious authorized writer. No workflow can change that trust
model by checking its own source. No new GitHub write permission is needed:
top-level and jobs use contents:read; Sonar PR decoration uses its GitHub app.

## Cargo execution: unresolved runtime prerequisite, fail-closed draft

Sonar documents Cargo on PATH as a prerequisite. It does not document the exact
analyzer invocation, and no real server run is available yet. Cargo may execute
repo-influenced configuration (including rustc-wrapper); neutral CARGO_HOME and
RUSTUP_TOOLCHAIN alone do not neutralize checkout .cargo/config.toml. Do not
claim the scanner never executes repository code merely because it imports
Clippy rather than running Clippy.

The local draft proposes a conservative first-run diagnostic guard: explicitly
select 1.99.0 with automatic installation off, use neutral Cargo/Rustup homes and
a restricted scanner PATH prefixed by reviewed inline deny stubs for cargo,
rustc, rustup and Clippy. The stubs never invoke repository code and record only
the tool name/allowlisted command words, not environment values or arbitrary
arguments. Explicit CARGO/RUSTC variables also point to these guards. No checkout
Cargo configuration is deleted or excluded from indexing. No tool bypass fallback.
Any observed guarded-tool invocation fails the job even if the scanner ignores it.

This deliberately does NOT satisfy the documented Cargo prerequisite and might
fail or degrade Rust analysis. It is an unproven diagnostic profile, not approved
production analysis. The first reviewed real run must establish what the analyzer
actually calls, inspect debug diagnostics and per-file Rust analysis/imports,
and test the Cargo-unavailable profile. If Cargo is required, stop for a reviewed
isolation/allowed-command decision; do not silently restore unrestricted Cargo
beside the token. No restoration claim until this is resolved. Local negative
fixtures prove the guard blocks a planted wrapper, not analyzer compatibility.
PATH/frontdoor guards are not a sandbox: absolute tool paths and unknown hooks
can bypass them. The draft audits known absolute Cargo/Rustup tool locations and
blocks token-bearing execution when such paths remain accessible. It also has
an unconditional local-draft execution hold; removing that hold is a separate
reviewed change, not an owner variable or an automatic fallback. No installed
local tools are renamed/deleted. Behind the hold, a separate reviewed-inline
HOSTED-DISPOSABLE-ONLY plan removes only literal /home/runner/.cargo,
/home/runner/.rustup and cargo/rustc/rustup files in /usr/bin and /usr/local/bin.
It checks GitHub-hosted Linux identity, the expected workspace/temp root, every
resolved target and known absolute tool from the audit before any deletion, then
asserts none of those known paths remain. Unexpected locations/symlinks fail
instead of broadening deletion. This plan is not executed locally or while the
hold exists. Removing known tools still is not an arbitrary-process sandbox;
scanner/analyzer children inherit the scanner environment, including its token.
Practical Java/GPG/Git and scanner
bootstrap behavior still require hosted proof before lifting the hold.
First-run conditions include no denied-tool attempt, no Rust warning in scanner
logs and server-side Rust counts/coverage matching the submitted inventory.
None alone proves a comprehensive execution boundary.

## Scanner and data isolation

Verified upstream v8.4.1 is commit e805d875275f728fac1885b413934be6d7c63f65.
Pin it and scanner 8.3.1.16491; leave scannerBinariesUrl at its official default
and skipSignatureVerification=false (GPG verification). Pin checkout, toolchain,
Python setup and upload/download artifact actions to verified commit SHAs.

Download only this workflow run's uniquely named report artifact to RUNNER_TEMP,
outside the checkout. Require the exact allowlist below, regular files, no links,
bounded lengths, valid UTF-8 and appropriate LCOV/JSON/XML schemas. Reject XML
DTD/entities, foreign/absolute report source paths, traversal and unexpected
files. Reports contain measurements, never scanner settings or executable code.
The scanner copies only validated report bytes to its separate report directory.

Create project.settings outside the checkout from an inline allowlist. Never
load a checked-in sonar-project.properties or settings from report artifacts.
Use CLI overrides for fixed https://sonarcloud.io host, SonarCloud bootstrap/API
endpoints, key/org, source root, revision, report paths, PR metadata and gate wait.
Explicit host CLI arguments override configuration files and environment per
Sonar's documented hierarchy. Do not accept proxy/host/binary URLs or custom
certificates from repository variables or reports. Verify action defaults and
argument forwarding against the pinned source. Do not turn off TLS/signatures.

The scanner step explicitly clears SONARCLOUD_URL, SONAR_ROOT_CERT,
SONAR_SCANNER_JSON_PARAMS, scanner/JVM option variables and all proxy variables.
No preceding step writes GITHUB_ENV using untrusted data. A real planted
sonar-project.properties with a dead host must still be tested to prove external
settings/CLI precedence; offline fixtures cannot prove scanner behavior.

Event-derived values enter inline code only through environment/event JSON, never
direct `${{ github.head_ref }}` interpolation into shell or action args. Validate
the PR number as digits, revision as 40 lowercase hex, and head/base branch names
with a bounded ASCII alphabet (letters/digits/dot/underscore/slash/hyphen, no empty
or traversal segments/leading hyphen/whitespace). Non-ASCII names fail clearly
rather than being normalized. Build sonar.pullrequest.key/branch/base arguments
only from validated values; set sonar.scm.revision explicitly to the checked-out
head. Do not rely on auto-detection's merge-ref GITHUB_SHA for PRs.

Both owned PR and main/manual scans use sonar.qualitygate.wait=true and a bounded
timeout, with no continue-on-error. A failed gate remains a failed job even if
evidence upload succeeds. Retain only allowlisted scanner task metadata and logs
without credentials; report-task URLs must have the fixed host before any read.

## Token-free reports and honest coverage

Artifact file allowlist:

- core-std.lcov, core-no-std.lcov, native.lcov
- clippy-core-std.jsonl, clippy-core-no-std.jsonl, clippy-native.jsonl
- python-coverage.xml
- report-inventory.json (exact commit, tools, report hashes, paths, limitations)

Use cargo-llvm-cov 0.9.1, installed only on the hosted runner via version-pinned
cargo install --locked with two workers (crate checksums, no core dependency).
Generate all-feature core and real no-default/no_std coverage separately, and
native manifest coverage separately. Keep Clippy JSON for those same three
scopes; import with sonar.rust.clippyReport.reportPaths. For report collection
only, omit -D warnings and set RUSTFLAGS empty for that subprocess, intentionally
removing the checkout config's global warning-to-error promotion. No lint rule
is disabled and all warnings/errors are retained. The source/config and ci.yml
strict -D warnings gates are unchanged. Record the real Clippy exit separately:
recognized Clippy-only diagnostic exits may be imported as lint findings;
compiler errors, crashes, absent completion and other tool failures block report
transport. The scanner revalidates that classification against the JSON, not
only the supplied outcome. Never relabel a real lint as "not a finding" or hide
it because Clippy exited nonzero. ci.yml remains the independent lint gate.
Import LCOV via sonar.rust.lcov.reportPaths. Normalize only verified source-root
prefixes, preserving counters and rejecting paths outside the checkout. Check
each production source appears; zero hits remain visible rather than excluded.

Coverage.py 7.17.2 is a new, approved CI-only tool: hash-lock the CPython 3.11
Linux wheel and require binary-only/hash-verified install. No local installation,
runtime dependency or change to python.yml. Run existing packaging controls,
pipeline controls and installed-wheel tests under coverage, with branch counting
and explicit site-packages-to-checkout path mapping. Build the ordinary wheel
through the existing provenance backend; never instrument/bypass that backend.
The facade is measured from the installed wheel, not a source-tree import.

Rust native unit coverage does not measure every Python-driven FFI path, and
Python coverage cannot see native instructions. These remain uncovered unless
the measured native report actually covers them. Subprocess coverage is not
silently assumed. Report skipped optional interop cases and all uncovered paths.
Do not manipulate denominator/exclusions to reach a guessed threshold.
Report code on a trusted-writer PR can fabricate measurements. Schema/path/hash
validation prevents injection and accidental misassociation, not false numbers.

Request analysis of repository sources and offline controls. Hidden .github
paths may not be indexed by default; Sonar coverage of them is **unproven** until
the real server file list establishes it, and must be reported as not covered
if absent. Existing CodeQL Actions coverage is separate evidence, not Sonar proof.
Classify tests/**, python/tests/**, python/packaging_tests/** and pipeline test
scripts as tests, not omitted code. Their patterns are also explicit main-source
exclusions so source/test sets cannot overlap; tests remain indexed as tests.
Sonar's primary docs say test inclusions automatically become main exclusions;
the explicit mirror makes the boundary inspectable. Only generated target/scanner
output is otherwise excluded. No rule disables, issue filters, Accept or suppressions.
Sonar issues/hotspots stay in Sonar, not the retired GitHub SARIF duplicate.

## Server proof, offline checks and delivery boundary

Public API evidence must retain project key, revision/analysis/task identity,
language/source counts, per-file and aggregate coverage, gate conditions/status,
full paginated issue and hotspot inventories including resolved/reviewed states.
Detect incomplete pagination/limits; never call a partial listing complete.
Verify imported Rust/Python coverage and Clippy from real scanner/server results,
not merely successful report creation. Public API schema currently exposes issue
resolved/status filters and hotspot TO_REVIEW/REVIEWED; verify completeness with
actual totals rather than relying on defaults. No server PASS is possible yet.

The current public hotspot-search schema advertises neither a PR nor branch
parameter. Coordinator decision: PR/non-main evidence is explicitly PARTIAL;
the real quality gate decides the PR, while complete hotspot inventories are
main-only. Partial evidence can succeed with a real OK gate but is never labeled
complete or a restoration proof. It stops if public task/measure APIs require
access. No token scope is widened to work around this. Optional organization in
report-task.txt is checked against configured identity; fixed-host URL checks
remain. The complete real metadata field set still needs a real-file check.

Offline tests: event eligibility (including Dependabot), missing/invalid config,
boolean-only secret presence, action SHA/signature/host/permission invariants,
strict artifact allowlist/path/size/link/schema rejection, coverage mapping and
counter preservation, XML entity rejection, complete pagination and gate failure.
Use deterministic fixtures and existing local tools. YAML must parse before any
publication. No local tools/targets are installed; no real token is used in tests.

Local design/draft approval is not hosted evidence. Coordinator must review the
delivery boundary before any intentionally red configuration is published. Owner
must confirm/import project/key/org, automatic analysis off, GitHub app binding,
gate and PR-plan support. Configure an expiring least-privilege analysis token
securely only when the hardened successor is reviewed. No credentials in chat.
Actual scans, complete findings/hotspots, coverage import and all returned checks
plus exact-head review are required before declaring Sonar restored or merging.

## Nonsecret owner checklist

1. Confirm an existing project or import this GitHub repository into the intended
   Sonar organization. Supply the exact nonsecret project/organization keys;
   the guessed project key returning 404 is not proof no private project exists.
2. Confirm the GitHub app/repository binding, CI analysis (automatic analysis off),
   quality gate and PR-analysis plan availability. Do not weaken rules/gates or
   accept issues to make onboarding green.
3. Set SONAR_PROJECT_KEY and SONAR_ORGANIZATION in GitHub repository Settings /
   Secrets and variables / Actions / Variables. No placeholder or other project's
   identity is substituted.
4. Wait for the execution-boundary/delivery review before configuring credentials.
   Then create an expiring least-privilege analysis token (project-restricted
   scoped organization token if available, otherwise dedicated project-limited
   account with Execute Analysis). Store it only as the SONAR_TOKEN Actions
   secret through GitHub settings, never chat or a local credential search.
   The owner records expiry and handles renewal; expiry must fail loudly.
5. Resolve the Cargo diagnostic boundary, real settings-precedence probe and
   evidence/access limitations with the reviewer/coordinator. No throwaway
   project/probe is authorized. Approve
   exact-head hosted probes, not an unrestricted Cargo fallback.
6. Only after reviewed real analysis/import/gate evidence should a separately
   approved publication make this scheduled workflow active. Nothing here
   configures a project, adds a secret, changes support or authorizes a release.

Local availability at drafting: cargo-llvm-cov 0.6.21 exists, but the reviewed
runner pin is 0.9.1; selected Rust 1.99 lacks local LLVM coverage tools and
coverage.py is not installed. No local installation was performed. Offline
fixtures do not establish real report generation, scanner/bootstrap/GPG behavior,
settings precedence, hosted analysis, coverage import or quality-gate status.

Primary sources: [scanner action v8.4.1](https://github.com/SonarSource/sonarqube-scan-action/tree/v8.4.1),
[configuration precedence](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/analysis-parameters/configuration-overview),
[Rust report import](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/languages/rust),
[Python coverage](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/test-coverage/python-test-coverage),
[source/test pattern semantics](https://docs.sonarsource.com/sonarqube-cloud/managing-your-projects/project-analysis/setting-analysis-scope/excluding-files-based-on-patterns),
[public API schema](https://sonarcloud.io/api/webservices/list).

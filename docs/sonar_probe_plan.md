# Sonar probe delta: design only

Updated 2026-11-07. User now authorizes actual reviewed deployment/scan with
organization telemetryworks and project spatial-typestate. Both nonsecret
repository variables are verified; redundant identity secrets were removed only
after verification, and SONAR_TOKEN is untouched. The implementation replaces
the saved hold with the probe/tool gates below, subject to exact-delta review
before publication or execution. No new owner dashboard/URL wait is imposed.
Sonar remains **NOT restored** pending real evidence. No visibility scanner
property is invented; Cloud project creation/visibility is not inferred from
Server behavior. Record actual first-run provisioning/errors and public API
result, and review any documented public-creation API boundary if needed.

The following records the original 2026-11-06 design and its accepted boundaries.

## Configuration facts and launch gate

- Explicitly labeled GitHub metadata: zero repository variables; three Actions
  secrets named SONAR_ORGANIZATION, SONAR_PROJECT_KEY and SONAR_TOKEN.
- No secret value was read. A mistaken attempt to read a nonexistent token
  variable failed before any value was obtained; no configuration changed.
- Public organization search returns key telemetryworks and display name
  Telemetry Works; the uppercase search has no matching organization.
- Public component lookups for spatial-typestate and
  TelemetryWorks_spatial-typestate return 404. This does not distinguish an
  absent project from an inaccessible/private one. No actual project URL or
  visibility is confirmed. Do not create/import one as a scanner side effect.

Owner must provide the actual Sonar project URL and public/private status, and
confirm exact project/organization keys, GitHub binding, CI analysis method,
quality gate and PR capability. Only then set the two nonsecret repository
variables, verify them, and remove redundant identity secrets. Do not read identity
secrets to work around missing variables or send them through masked job outputs.
SONAR_TOKEN stays an Actions secret, untouched. No token request in chat.

## Proposed reviewed execution delta

1. **Approval before publication.** Reviewer and coordinator approve the exact
   identity, launch event, source SHA and hold-removal diff before a same-repo
   branch/PR or probe is published. Publishing a PR can run its workflow with
   secrets. Do not assume a new manual workflow is already dispatchable. The
   launch mechanism depends on the confirmed project/PR baseline and GitHub
   workflow registration; do not merge merely to initialize a scanner.
2. **Cargo remains absent.** Keep the disposable-hosted-runner/literal-target
   removal guards. Add a privileged, metadata-only filesystem walk after removal,
   without executing or reading candidate binaries. Check cargo/rustc/rustup and
   Clippy executable regular files and symlinks by name, outside only the exact
   diagnostic stub directory; non-executable completion files do not count.
   Propose adding only the literal /etc/skel/.cargo and /etc/skel/.rustup template
   roots to the existing deletion allowlist, subject to the same resolved-target
   review. No runtime expansion. Unexpected remnants fail.
   Record scan roots, explicitly skipped virtual filesystems (/proc, /sys, /dev,
   /run), unreadable paths, timeout and matches. Unreadable nonvirtual subtrees,
   timeout (180 seconds) or an incomplete scan fail closed. Do not follow
   directory symlinks. No broad /usr, /opt or tool-cache deletion.
   A future implementation must state those limits instead of calling this an
   unrestricted whole-machine proof. No local removal or scan of user tools.
3. **No sandbox claim.** Known tool removal and frontdoor stubs do not prove an
   arbitrary-process boundary: renamed binaries, interpreter paths and other
   analyzers' children remain outside that claim. Scanner children inherit its
   token. Retain the attempt-file check even when the scanner swallows a failure.
   If Cargo is required, a Rust warning appears, files are skipped or coverage
   degrades, stop for reviewed isolation/support decisions. No tool-restoration
   fallback, rule suppression or reduced-Rust success claim.
4. **Token-free settings precedence probe first.** After a network safety review, plant a temporary
   untracked sonar-project.properties containing a distinct bogus project/org,
   sonar.host.url, sonar.scanner.sonarcloudUrl and sonar.scanner.apiBaseUrl at an
   HTTP endpoint in TEST-NET-1 (192.0.2.1). Before any token exists in a step,
   install and verify an outbound REJECT rule for that exact IP on the disposable
   runner; absence of the firewall tool or failed verification blocks the probe.
   Do not rely on a reserved address alone to protect a credential. Keep the
   trusted settings file outside checkout and fixed official host/bootstrap/API
   CLI arguments. Run the same pinned scanner with SONAR_TOKEN absent first;
   classify only the expected authentication failure, not a successful anonymous
   analysis or an unrelated error, as a probe outcome. Require readable REJECT
   counters equal to zero before and after, and observable official-host/settings
   evidence. Otherwise stop before the token step. Keep the firewall rule for
   both invocations and check it again afterward. Later require the confirmed
   authenticated server project/org/revision. This proves only the planted keys
   for which evidence exists; never infer unobserved effective settings. This is
   a proposed narrow probe rule, not an approved
   egress sandbox. No packet contents or authentication headers are captured.
5. **Final token/log boundary.** Use the pinned official action
   token-free with `args: --version` to install/GPG-verify the pinned CLI; verify
   its installed path/version/hash. Reviewed inline Python may invoke that same
   CLI ONLY for the token-free authentication probe, permitting expected-failure
   classification without continue-on-error. It must preserve all WARN/ERROR
   evidence and confirm INFO format with no DEBUG output or sensitive settings
   before any credential-bearing step. If that evidence is insufficient, stop.
   The token-bearing scan stays on the pinned official action with normal INFO
   logs; no custom credential-owning wrapper, buffering or warning filter.
   SONAR_TOKEN stays only in that official step's environment. No checked-out
   script runs with it. No token argv/file, shell
   trace, environment dump, scanner-context dump or HTTP header logging. Force
   RUNNER_DEBUG=0, sonar.log.level=INFO and sonar.verbose=false; retain the existing
   cleared proxy/certificate/JSON/JVM settings. Recheck the pinned action's token
   handling and scanner logging contract before executing; never use GitHub
   "re-run with debug logging" for this workflow. The token-free probe confirms
   the log level/format; do not add an in-job token-bearing wrapper merely to
   inspect the authenticated log. Keep all unexpected Rust/Cargo WARN/ERROR lines
   reviewable in the official action log. The earlier proposed DEBUG post-check
   is replaced by token-free confirmation plus forced step-level debug-off.
   GitHub masking is secondary to INFO/no dumps/no credential argv and verified
   vendor handling. Unexpected token-like output blocks the run and evidence
   retention; the owner rotates the token before retry. Do not paste the output
   or request a replacement credential in chat.
6. **Retain allowlisted evidence, not raw debug logs.** Upload only validated
   task metadata, tool/removal/scan summaries, report hashes and public server
   responses for 14 days. No raw scanner debug log artifact, full scanner context,
   process environment or unrestricted .scannerwork archive. GitHub's platform
   job-log retention is separate and is not changed or claimed as 14 days here.
   Review required log facts without echoing credentials. INFO/raw platform logs
   are not pre-certified secret-free: do not publish excerpts if a leak is suspected.
7. **Actual analysis evidence.** Require successful signature verification,
   correct task/source identity, no denied tools or Rust/Cargo warning, server
   Rust/Python indexed paths, imported per-file coverage, Clippy diagnostics and
   gate conditions/status. Source/test sets remain disjoint; .github analysis is
   unproven until the server shows it. Retain full issue inventories and complete
   main-branch hotspots. PR/non-main evidence stays explicitly PARTIAL and the
   real gate decides the PR. Private APIs needing access require a new reviewed
   evidence-access boundary, not another token scope silently added to scripts.

## Offline work and remaining decisions

The preserved executable draft still has its reviewed hold and known-path-only
audit. The filesystem walk, network rule, settings probe and hold removal above
are proposals, not implemented or tested behavior. No credentials are needed to
review them. Before code changes, reviewer/coordinator must settle the exact
filesystem plan, narrow firewall mechanism, token-free probe and launch event
after the owner confirms identity/visibility. There is no throwaway-project
authorization and no permission to weaken CI or accept findings. Reviewer launch
proposal, not yet approved: a reviewed PR probe with PARTIAL evidence, explicit
merge authorization under "Sonar NOT restored", then first full main analysis
and restoration decision from that evidence. If PR analysis requires an initial
main baseline, return for a decision. A fail-closed main/scheduled analysis must
remain red on real failure; owner/coordinator must accept that delivery boundary.
Private-project evidence access is a separate unresolved decision.

Local review can validate target/scan planning and failure cases with temporary
fixtures only. Real Cargo-free quality, GPG/bootstrap behavior, settings precedence,
metadata fields, hidden indexing, coverage import and the quality gate remain
**NOT RUN**. A green workflow alone never closes these checks.

Primary references: [mandatory token and logging parameters](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/analysis-parameters/parameters-not-settable-in-ui),
[scanner settings precedence](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/analysis-parameters/configuration-overview),
[TEST-NET address reservation (RFC 5737)](https://www.rfc-editor.org/rfc/rfc5737),
[preserved local draft design](sonar_successor.md).

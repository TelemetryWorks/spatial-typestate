# Main branch protection audit: 2026-11-08

## Decision and observed baseline

Applied once to `main` at repository revision `75c89c441e230c54d94b3bcb553750839188c7d9`.
Before application: clean local/origin/live refs; public repository, admin permission;
classic protection returned 404, GraphQL listed no classic rules, and repository/
inherited rulesets and active ruleset rules on main were empty. Merge-commit,
squash and rebase methods were already enabled and are unchanged.

- [Before snapshot](2026-11-08-main-protection-before.json).
- [LF-normalized approved request snapshot](2026-11-08-main-protection-request.json), SHA256
  `ebf511c7ddfcb9608a71dab2925624f4e355d7657121e24b6bc123ba0ec056f3`.
  The original applied CRLF payload had SHA256
  `eb06c1532e1b45f7e684c4a7cce7abeaa9e01bc60a9c4fe2f648066bbd230da2`.
  The normalized file is JSON-equal to those original bytes; only line endings
  differ. The original payload was preserved locally and was not sent again.
- [Actual GET after application](2026-11-08-main-protection-after.json).

The one request was `PUT /repos/TelemetryWorks/spatial-typestate/branches/main/protection`.
Readback confirmed the exact context/app pairs and flags. GitHub omits the null
`restrictions` field in its response; GraphQL explicitly confirmed
`restrictsPushes=false`, `requiresApprovingReviews=true`, approval count 0, and
only the pattern `main`. The first local readback expected a literal null field
and raised after the successful PUT; it was corrected by a read-only GraphQL
verification. No second PUT or policy relaxation occurred.

## Required policy

Require a PR with **zero human approvals**, so the sole maintainer can merge an
owned PR after the required checks. Enforce the policy for admins. Require strict
up-to-date checks; disallow force pushes and branch deletion. No push/team
restrictions, code-owner/last-push/stale-review requirements, signed commits,
linear history, conversation resolution or merge queue were added. No other
branch, workflow, source, dependency, secret, severity setting or merge method changed.

The 27 exact required pairs are below. Empty matrix flags and spaces are literal;
in particular, do not trim `Library (1.85.0, )` or `Library (1.91.1, )`.

| Required context | App ID |
| --- | --- |
| `CodeQL` | 57789 |
| `CodeQL (actions)` | 15368 |
| `CodeQL (python)` | 15368 |
| `CodeQL (rust)` | 15368 |
| `Library (1.85.0, )` | 15368 |
| `Library (1.85.0, --all-features)` | 15368 |
| `Library (1.85.0, --no-default-features)` | 15368 |
| `Library (1.91.1, )` | 15368 |
| `Library (1.91.1, --all-features)` | 15368 |
| `Library (1.91.1, --no-default-features)` | 15368 |
| `Public Sonar evidence (no scanner token)` | 15368 |
| `Python (ubuntu-latest, 3.11)` | 15368 |
| `Python (ubuntu-latest, 3.14)` | 15368 |
| `Python (windows-latest, 3.11)` | 15368 |
| `Python (windows-latest, 3.14)` | 15368 |
| `Sonar eligibility/configuration (not an analysis)` | 15368 |
| `Sonar scanner` | 15368 |
| `Tests (ubuntu-latest, all-features)` | 15368 |
| `Tests (ubuntu-latest, default)` | 15368 |
| `Tests (ubuntu-latest, no-std)` | 15368 |
| `Tests (windows-latest, all-features)` | 15368 |
| `Tests (windows-latest, default)` | 15368 |
| `Tests (windows-latest, no-std)` | 15368 |
| `Token-free Sonar reports (not a server analysis)` | 15368 |
| `bare-metal` | 15368 |
| `quality (--all-features)` | 15368 |
| `quality (--no-default-features --features no_std)` | 15368 |

26 contexts come from `github-actions` (15368), and `CodeQL` comes from
`github-advanced-security` (57789). App binding prevents a different integration
from satisfying a same-named context. It does not stop a trusted writer editing
an Actions workflow; source review remains necessary.

Require all four Sonar contexts, including eligibility/configuration and token-free
reports. If either fails, downstream jobs may skip; requiring only the scanner
would be fail-open. Only `Sonar analysis unavailable (fork/Dependabot; not a scan)`
is omitted. The three CodeQL language jobs prove execution; the separate `CodeQL`
service check gates alert results, so it is required too.

GitHub documents a default CodeQL check failure at severity error or security
severity high/critical. The repository uses advanced setup; GET default-setup is
`not-configured` and does not expose an advanced-check severity override. No
documented REST read of that override was available. The threshold above is the
**documented default, not a verified repository override**. Existing severity
settings were not changed; the actual service check must pass whatever they are.

## Twenty event cases

Read-only replay against the exact proposed required pairs: 15 real final PR
heads, 3 real failed PR #14 heads, and 2 explicitly modeled untrusted events.
No actual fork or Dependabot PR exists among the 15 observed PRs; modeled rows
are not claimed as live runs. Historical PRs were merged before this policy;
the replay does not mean protection existed then.

| Case | Event/head | Observed check runs | Missing / nonpassing required pairs | Replay / limit |
| --- | --- | --- | --- | --- |
| PR #15 | same-repo human `9600feec2b1d` | 28 | 0 / 0 | Satisfies status predicates |
| PR #14 | same-repo human `9bda000c44a8` | 28 | 0 / 0 | Satisfies status predicates |
| PR #13 | same-repo human `979fbd91de26` | 28 | 0 / 0 | Satisfies status predicates |
| PR #12 | same-repo human `14e607872db4` | 28 | 0 / 0 | Satisfies status predicates |
| PR #11 | same-repo human `77d7378c246a` | 28 | 0 / 0 | Satisfies status predicates |
| PR #10 | same-repo human `95781207cc6c` | 28 | 0 / 0 | Satisfies status predicates |
| PR #9 | same-repo human `1d6f52efafe6` | 26 | 4 / 0 | Would block; predates current workflows |
| PR #8 | same-repo human `bbc8223ff293` | 19 | 8 / 0 | Would block; predates current workflows |
| PR #7 | same-repo human `a64fad6b8154` | 19 | 8 / 0 | Would block; predates current workflows |
| PR #6 | same-repo human `952ff6ba6503` | 19 | 8 / 0 | Would block; predates current workflows |
| PR #5 | same-repo human `660c8e1e347d` | 15 | 12 / 0 | Would block; predates current workflows |
| PR #4 | same-repo human `c15709022bd6` | 15 | 12 / 0 | Would block; predates current workflows |
| PR #3 | same-repo human `09c86d90577e` | 15 | 12 / 0 | Would block; predates current workflows |
| PR #2 | same-repo human `57c099e8c66b` | 15 | 12 / 0 | Would block; predates current workflows |
| PR #1 | same-repo human `faacd3aa33d8` | 15 | 12 / 0 | Would block; predates current workflows |
| PR #14 failed head | `fd160cdbbc61` | 28 | 0 / 2 | Blocks on real failure/cancellation |
| PR #14 failed head | `48e2eddbff53` | 28 | 0 / 9 | Blocks on real failure/cancellation |
| PR #14 failed head | `abcff657032c` | 28 | 0 / 2 | Blocks on real failure/cancellation |
| Modeled fork PR | foreign head repository, no Sonar token | CodeQL/other checks assumed allowed and passing; Sonar config succeeds, three downstream jobs skip | 0 / 0 once all other checks report | Technically satisfies GitHub; no Sonar analysis |
| Modeled Dependabot PR | PR author is Dependabot, including maintainer rerun | Same Sonar ineligible path | 0 / 0 once all other checks report | Technically satisfies GitHub; no Sonar analysis |

The six latest owned PRs (#10-15) emit all 27 required pairs with the right apps;
their intentional fork notice is skipped. PR #9 predates Sonar; #6-8 predate
CodeQL restoration; #1-5 also predate Python packaging. These old closed PRs are
not affected retroactively. Failed heads `fd160cd` and `abcff65` fail Sonar gate/
evidence, while `48e2edd` has real Python failures and canceled checks.

Additional dependency analysis (no fault injection): configuration failure must
block even if reports/scanner/evidence skip; report failure must block even if
scanner/evidence skip; scanner gate failure must block; `CodeQL` service failure
must block even if all three language jobs succeed. A same-named check from the
wrong app cannot replace a required app-bound pair. Missing checks block too.

## Head versus merge-ref and fork limits

Core CI and CodeQL use the PR merge ref. Python artifact CI and Sonar use the
exact PR head. For real PR #15, CodeQL analyzed merge commit
`3abc2c843f54705e75538870b37d7d5ccbd8a2a3`, parents `c047c12` and `9600fee`;
its tree equals the head tree. Strict up-to-date protection avoids treating a
stale head-only Python/Sonar result as validation against a newer main. A branch
update requires fresh checks on the new head.

GitHub treats success, skipped and neutral as satisfying required checks. Fork/
Dependabot PRs therefore can satisfy this policy with **no Sonar scan**; they
may also wait for workflow approval or an unreported check. The accepted
operational requirement is to review/port the contribution to an owned branch
and obtain a real Sonar gate/evidence run before merging. Do not merge the
untrusted PR merely because its skipped checks look green. No fork-blocking
workflow, secret exposure or `pull_request_target` path was added.

## Operations and verification boundaries

- Renaming a job/matrix entry requires a coordinated protection update in the
  same change; an obsolete required context can block every PR. Preserve app IDs.
- A SonarCloud outage or missing/expired/revoked token blocks all merges. Repair
  the service/configuration or renew the token securely. An admin editing
  protection is an explicit, recorded emergency step, not an automatic bypass.
- `enforce_admins` prevents routine bypass; an admin can still edit/remove the
  policy itself. No policy can prevent that same administrator changing settings.
- No direct-push, force-push or deletion probe was performed. Their configured
  prohibitions were verified by REST/GraphQL; destructive tests are not justified.
- No builds/tests were run locally for this policy-only task. Hosted workflows
  run normally on the audit PR under the new required-check policy.

## Observed PR enforcement

[Audit PR #16](https://github.com/TelemetryWorks/spatial-typestate/pull/16) was
created from an owned branch. The [captured pre-merge observation](2026-11-08-main-protection-pr16-pending.json)
records head `09cb2e531afcbbff84af7ba2df98347317a9c4bf`, base `75c89c4`,
`mergeStateStatus=BLOCKED`, and `mergeable=MERGEABLE`: conflict-free is not permission
to merge. GitHub's `pr checks --required` reported 24 required jobs, including
queued/in-progress ones. The other three configured contexts (Sonar scanner,
public evidence and CodeQL results) had not yet reported; no missing context was
removed from the policy. The expected fork notice was not required.

This is a dated pre-merge observation, not a claim that checks had passed.
The final normal merge must use no admin bypass or temporary policy reduction;
its outcome and post-merge runs are recorded in the PR's permanent description
and timeline. Read the actual merged state and commit-bound checks there rather
than inferring success from this earlier blocked-state snapshot.

## Primary references

- [Protected branches, strict checks, apps and skip semantics](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
- [Protected-branch REST fields](https://docs.github.com/en/rest/branches/branch-protection).
- [Required status troubleshooting](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).
- [Code scanning results and default severity](https://docs.github.com/en/code-security/how-tos/manage-security-alerts/manage-code-scanning-alerts/triage-alerts-in-pull-requests).
- [PR CodeQL upload permissions for Dependabot](https://docs.github.com/en/code-security/reference/code-scanning/troubleshoot-analysis-errors/resource-not-accessible).

# Owner-approved Sonar issue dispositions

Decision date: 2026-11-08 UTC. This follow-up supersedes the pending owner
decision in the [historical 2026-11-07 inventory](2026-11-07-sonar-main-triage.md).
The original OPEN snapshots remain historical evidence, not rewritten outcomes.

The owner explicitly approved exactly these three decisions after source and
independent review at main `318562fecb0086776cefa4390b2e3390910d95cb`:

| Issue | Rule and source | Approved modern status | Reason |
|---|---|---|---|
| `AaG4bQRmnDi6kOcnr-BC` | `pythonsecurity:S8705`, `scripts/performance_study.py:158` | `FALSE_POSITIVE` | The existing leading-dash guard and argparse validation prevent option injection before file access or child execution. Regression tests exercise `--list`, `--sample-size=1`, `-x`, and supported regex filters. |
| `AaG4bQQrnDi6kOcnr-A7` | `pythonsecurity:S8707`, `python/examples/lab_workflow.py:23` | `ACCEPTED` | Intentional read-only CSV input selected by a trusted local operator; strict header before data use. Untrusted forwarding could probe existence/readability or open unintended files with that principal's rights. |
| `AaG4bQO8nDi6kOcnr-Ap` | `pythonsecurity:S8707`, `python/benchmark.py:178` | `ACCEPTED` | Intentional arbitrary-write output selected by the invoking principal. Do not expose to untrusted callers or forward untrusted output paths under broader OS rights. |

The accepted risks remain real; acceptance does not add a path restriction or
sandbox. The filter finding is different: the relevant validation already
prevents the flagged option injection. No numeric API, source implementation,
historical reproduction command, rule, gate, threshold or exclusion changes.
The 24 maintainability findings are outside this decision and remain backlog.

## Execution boundary (pending actual execution)

A temporary PR-13-only workflow also requires a unique one-time repository
variable. It has no checkout, runs isolated inline Python, and takes the existing
token only in that step's environment, removes it from the environment, and uses
it only in an HTTPS Authorization header. It never prints bodies or credentials,
puts credentials in arguments, or saves them in files/artifacts.

Before any write, anonymous reads verify the public project/organization/main
identity, main's reviewed analysis revision, and the exact three issue keys,
rules, components, source lines and hashes. Modern status must be OPEN or exactly
the intended prior target. An authenticated read must advertise the exact allowed
transition for every OPEN issue; a missing capability stops all writes and
reports the required Administer Issues permission. Project administration alone
is not assumed sufficient.

Each OPEN issue gets one literal `issues/do_transition` POST with its fixed
transition and audit comment in the same request. No wildcard, reopen,
`add_comment`, rule change or fourth issue is available. The fixed host rejects
redirects, ignores proxies, verifies TLS normally, and caps time and response
size. Partial failures stop; reruns skip a target only when its exact approved
comment and one matching changelog transition are already present. Target status
without this audit fails instead of inventing an audit after the fact.

Anonymous final reads must confirm each modern status, exactly one matching
literal comment, and one matching transition in its changelog. Legacy resolution
is recorded separately: `FALSE-POSITIVE` corresponds to `FALSE_POSITIVE`, and
`WONTFIX` may accompany modern `ACCEPTED`; there is no legacy `ACCEPTED` resolution.
No success is inferred from an HTTP acknowledgement alone.

After verified success, remove the helper/tests and delete its activation variable
immediately. The final PR retains documentation only. Independent review of the
public histories, a natural main analysis, the unchanged new-code gate, full
evidence and all actual CI checks closes this work.

The live [Sonar Cloud Web API](https://sonarcloud.io/web_api/api/issues/do_transition)
documents `falsepositive`, `accept`, their Administer Issues permission, and the
optional atomic `comment` parameter. Deprecated `wontfix` is not used.

## Exact public audit comments

The following fixed comments are part of the reviewed transition payloads.
Actual run IDs and verified outcomes will be added after execution.

### AaG4bQRmnDi6kOcnr-BC

2026-11-08 UTC owner-approved false positive: the leading-dash guard in scripts/performance_study.py and its argparse validation prevent a filter from becoming a Criterion option before I/O or execution. Regression tests cover --list, --sample-size=1 and -x; normal regex filters remain supported. See docs/evals/2026-11-07-sonar-main-triage.md. This decision applies only to this sanitised finding.

### AaG4bQQrnDi6kOcnr-A7

2026-11-08 UTC owner-approved accepted risk: --input is a read-only file chosen by a trusted local operator, with a strict CSV header checked before data use. Absolute paths and run-anywhere operation are intentional. Do not forward untrusted file choices under broader OS rights; existence/readability probing remains possible. See docs/evals/2026-11-07-sonar-main-triage.md. This is accepted operator risk, not a false positive or a sandbox guarantee.

### AaG4bQO8nDi6kOcnr-Ap

2026-11-08 UTC owner-approved accepted risk: --out is an intentional arbitrary-write interface for a trusted local operator and can overwrite any file that principal may write. Do not expose it to untrusted callers or forward untrusted output paths under broader OS rights. See docs/evals/2026-11-07-sonar-main-triage.md. Preserve the documented reproduction interface; this is accepted operator risk, not a false positive or a sandbox guarantee.

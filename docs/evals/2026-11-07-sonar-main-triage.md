# Main Sonar analysis and CLI boundary review

Checked 2026-11-07 against main `32db7a10f32945c9743c89980a26bfb84499fb37`.
Analysis `92b0daf3-ff23-48ec-9815-01cfa7c5d1ca`, push run
[42426773113](https://github.com/TelemetryWorks/spatial-typestate/actions/runs/42426773113).
Public inventory was re-read with exact revision/analysis identity. There are
28 open issues: four vulnerabilities and 24 pre-existing code smells; zero bugs
and zero main hotspots. Both the first and second main gate returned `NONE`,
with no conditions: no new-code definition was configured. The initial
assumption that a second scan alone would establish it was disproved. `NONE`
is not an OK result. The built-in Sonar way gate has only new-code conditions.
No threshold/rule change is proposed. Sonar restoration remains incomplete.

Follow-up `f620882` fixed S5443 and implemented the tested leading-hyphen filter
guard. Sonar still reports S8705 because its taint model does not recognise that
validation. Three pre-existing vulnerability findings and 24 smells remain OPEN;
no issue disposition has been changed.

The coordinator chose the documented Cloud Specific Date new-code definition:
`2026-11-07`, before deployment analysis `32db7a1` at 23:51 UTC that day. This
includes deployment and PR #11 changes; it is not a rolling reset to the latest
analysis. It scopes the new-code gate without hiding the overall backlog.
The three older vulnerability findings remain outside that new-code window
and visibly OPEN. A passing new-code gate must never be described as an
overall-clean project. Exact setup requires independent review before execution.

Cloud's [documented configuration API](https://docs.sonarsource.com/sonarqube-cloud/managing-your-projects/project-analysis/configuring-new-code-calculation)
uses two project-scoped settings writes: `sonar.leak.period=2026-11-07`, then
`sonar.leak.period.type=date`. No Server-only new-code endpoint or scanner
property is assumed. The temporary helper permits only unset or already-exact
values, refuses foreign/partial state, and verifies both keys. It changes no
gate, rule, threshold or issue status. Real verification still requires a
nonempty period and real conditions on a subsequent main analysis.

Reviewed one-time setup run [42429835320](https://github.com/TelemetryWorks/spatial-typestate/actions/runs/42429835320)
at `7992202` succeeded: fixed date `2026-11-07`, type `date`, statuses
`[200, 200, 200, 204, 204, 200]`. The authenticated pre-read was unset;
exact readback verified both project values. No inherited/foreign override was
needed. The helper/tests were removed in the next commit and its activation
variable deleted. No gate, threshold, rule, issue status or organization setting
was changed. The subsequent natural main scan must still prove the period and
gate; helper success is not analysis evidence.

## Four security findings and decisions

- `AaG4bQQtnDi6kOcnr-A9`, `python:S5443`, `python/package_ci.py:91`:
  the runtime container starts in shared `/tmp`. Another process in that
  directory could plant a relative-path/import target. Existing pinned images
  and tests are not a hostile-user exploit demonstration. The configuration
  itself is reproducible from the current Docker argv. Fix: start Python with
  `-I` in `/`, then create a fresh `tempfile.TemporaryDirectory` and enter it
  before pip/test work. The per-container temporary directory is securely created
  (POSIX mode 0700), not a predictable shared working directory. No wheel bytes,
  runtime hash, image, Python/glibc assertion or test selection changes.
- `AaG4bQQrnDi6kOcnr-A7`, `pythonsecurity:S8707`,
  `python/examples/lab_workflow.py:23`: `argparse --input` flows to a read-only CSV
  open. The invoking local operator deliberately chooses a readable file;
  absolute paths and running outside the checkout are documented and tested.
  Strict headers precede data use, and diagnostic text does not echo file data.
  An agent forwarding untrusted input could still probe existence/readability
  or open unintended files with its own OS rights. This is a real flow, not a
  false positive or a sandbox. Preserve the interface. Reviewer classifies it as
  an operator-trust risk; owner disposition is pending and the Sonar issue stays
  OPEN. No Accept/false-positive status mutation is authorized.
- `AaG4bQO8nDi6kOcnr-Ap`, `pythonsecurity:S8707`, `python/benchmark.py:178`:
  `argparse --out` reaches a filesystem write. The local invoking principal can
  overwrite any writable output it selects. The historical reproduction command
  `--out target/python-study.json` remains valid. Never expose this CLI to
  untrusted callers, or forward untrusted output paths under broader OS rights.
  This is an intentional arbitrary-write interface with real operator risk,
  not a false positive. Preserve it; owner disposition is pending, the issue
  remains OPEN, and no status mutation is authorized.
- `AaG4bQRmnDi6kOcnr-BC`, `pythonsecurity:S8705`,
  `scripts/performance_study.py:150`: `--filter` flows as a bare argv element
  into Criterion. No shell is used, but a leading `-` becomes a child option.
  Reproduced with the existing prepared binary: `--list` listed benchmark IDs
  (exit 0), while `--sample-size=1` changed Criterion configuration and triggered
  its sample-size assertion (exit 101). Neither command collected timings.
  Fix: reject leading-hyphen filters both during CLI parsing and at `run` entry,
  before manifest access, execution or preparation. Normal regex filters,
  `^amortization`, built-in SUBSET and the two-worker option remain supported.
  A literal leading hyphen can be expressed as a regex such as `^-x`.

The manifest executable and dataset paths remain local operator-owned inputs;
this runner is not a service or an arbitrary-process/hostile-filesystem sandbox.
No CLI input/output path restrictions, source exclusions, issue acceptances or
historical performance-evidence edits are made.

## Real CLI checks (no timings)

Twelve real Python CLI parser invocations used `--run --configs=invalid` to
stop valid filters before manifest/build/measurement work. Every result exited
2 at its intended validation stage, with no BUILD or MEASURE output. These are
argument-boundary tests, not successful benchmark runs or performance evidence.

Independent unit fixtures additionally preserve built-in SUBSET and reject
`-x`, `--list`, and `--sample-size=1` before file access or child execution.
The private-workdir test captures both image commands, executes only the real
stdlib startup prefix in an isolated child (no local Docker/pip/native work),
verifies distinct directories and cleanup, and on POSIX verifies mode 0700.
Actual manylinux 2.28/Bookworm 2.36 wheel imports/tests still run in package CI.

Primary references: [Python 3.11 tempfile](https://docs.python.org/3.11/library/tempfile.html),
[subprocess argv and shell semantics](https://docs.python.org/3.11/library/subprocess.html),
[argparse type validation](https://docs.python.org/3.11/library/argparse.html).

## Coverage and exact initial issue inventory

The tables below record initial observations, not a current PASS claim. Server
percentages are overall coverage, not new-code gate values or promises. Rust
ncloc is 2477, with all 47 tracked Rust files indexed (17 main, 30 test).
Python has 17 files including tests. Workflows/scripts under .github are indexed
and the Actions sensor ran. All three imported Clippy reports have verified
exit 0, zero errors and zero warnings. Overall coverage is 57.8%.

The native `lib.rs` 3.9% is the documented ordinary-wheel/PyO3 glue limitation:
Python exercise does not generate Rust FFI counters. It is visible, not excluded
or inflated. Core lib/frame/macros and test files without a denominator do not
receive an invented percentage. Benchmark/study tools with 0% remain in the
denominator; focused new tests will improve their tested paths.

The 24 old smells remain visible backlog. This task does not refactor the core,
packaging design, benchmark measurements or numerical implementation to clear a
style dashboard.

## Reproduction binary and parser cases

Existing binary `spatial-55d8a535fd98928a.exe`, SHA256 `762bd077344e372dba9f1ef4dc3589c87ca360639d6265a2e7240fe1c8df86cc`.

| Filter | Observed result |
|---|---|
| `None` | filter accepted; invalid profile stopped execution |
| `''` | filter accepted; invalid profile stopped execution |
| `'^amortization'` | filter accepted; invalid profile stopped execution |
| `'point.*valid$'` | filter accepted; invalid profile stopped execution |
| `'quaternion/(normal|near_unit)'` | filter accepted; invalid profile stopped execution |
| `'^--literal'` | filter accepted; invalid profile stopped execution |
| `'with space'` | filter accepted; invalid profile stopped execution |
| `'?.*'` | filter accepted; invalid profile stopped execution |
| `'--list'` | rejected option-like filter |
| `'--sample-size=1'` | rejected option-like filter |
| `'--test'` | rejected option-like filter |
| `'-x'` | rejected option-like filter |

## Imported per-file coverage

| File | Coverage % | Lines to cover | Uncovered |
|---|---:|---:|---:|
| `.github/scripts/codeql_evidence.py` | 89.4 | 33 | 4 |
| `.github/scripts/sonar_evidence.py` | 90.5 | 180 | 14 |
| `.github/scripts/sonar_reports.py` | 96.1 | 163 | 6 |
| `.github/scripts/test_codeql_evidence.py` | no denominator | - | - |
| `.github/scripts/test_sonar_draft.py` | no denominator | - | - |
| `python/benchmark.py` | 0.0 | 133 | 133 |
| `python/build_backend.py` | 70.3 | 374 | 105 |
| `python/check_package_metadata.py` | 33.0 | 61 | 35 |
| `python/examples/lab_workflow.py` | 67.8 | 90 | 27 |
| `python/native/src/kernels.rs` | 92.7 | 218 | 16 |
| `python/native/src/lib.rs` | 3.9 | 358 | 344 |
| `python/package_ci.py` | 0.0 | 88 | 88 |
| `python/packaging_tests/test_backend.py` | no denominator | - | - |
| `python/src/spatial_typestate/__init__.py` | 71.4 | 5 | 1 |
| `python/tests/test_batches.py` | no denominator | - | - |
| `python/tests/test_lab_workflow.py` | no denominator | - | - |
| `python/tests/test_provenance.py` | no denominator | - | - |
| `python/verify_artifacts.py` | 52.8 | 160 | 67 |
| `scripts/performance_study.py` | 0.0 | 146 | 146 |
| `src/errors.rs` | 100.0 | 8 | 0 |
| `src/frame.rs` | no denominator | - | - |
| `src/lib.rs` | no denominator | - | - |
| `src/macros.rs` | no denominator | - | - |
| `src/point.rs` | 90.6 | 32 | 3 |
| `src/quaternion.rs` | 97.1 | 102 | 3 |
| `src/transform.rs` | 98.6 | 211 | 3 |
| `src/units.rs` | 81.8 | 55 | 10 |
| `src/vector.rs` | 90.6 | 32 | 3 |

## All 28 initial issues

| Key | Type / rule | File:line | Message |
|---|---|---|---|
| `AaG4bQRjnDi6kOcnr-A-` | CODE_SMELL / `rust:S3776` | `benches/spatial.rs:427` | Refactor this function to reduce its Cognitive Complexity from 33 to the 30 allowed. |
| `AaG4bQRjnDi6kOcnr-A_` | CODE_SMELL / `rust:S3776` | `benches/spatial.rs:505` | Refactor this function to reduce its Cognitive Complexity from 72 to the 30 allowed. |
| `AaG4bQO8nDi6kOcnr-Ao` | CODE_SMELL / `python:S3776` | `python/benchmark.py:47` | Refactor this function to reduce its Cognitive Complexity from 23 to the 15 allowed. |
| `AaG4bQO8nDi6kOcnr-An` | CODE_SMELL / `python:S1854` | `python/benchmark.py:134` | Remove this assignment to local variable 'result'; the value is never used. |
| `AaG4bQQmnDi6kOcnr-At` | CODE_SMELL / `python:S1192` | `python/build_backend.py:44` | Define a constant instead of duplicating this literal "pyproject.toml" 3 times. |
| `AaG4bQQmnDi6kOcnr-Au` | CODE_SMELL / `python:S1192` | `python/build_backend.py:46` | Define a constant instead of duplicating this literal "Cargo.toml" 4 times. |
| `AaG4bQQmnDi6kOcnr-Av` | CODE_SMELL / `python:S3776` | `python/build_backend.py:60` | Refactor this function to reduce its Cognitive Complexity from 43 to the 15 allowed. |
| `AaG4bQQmnDi6kOcnr-Aw` | CODE_SMELL / `python:S3776` | `python/build_backend.py:142` | Refactor this function to reduce its Cognitive Complexity from 22 to the 15 allowed. |
| `AaG4bQQmnDi6kOcnr-Ax` | CODE_SMELL / `python:S3776` | `python/build_backend.py:170` | Refactor this function to reduce its Cognitive Complexity from 17 to the 15 allowed. |
| `AaG4bQQmnDi6kOcnr-Ay` | CODE_SMELL / `python:S1481` | `python/build_backend.py:250` | Replace the unused local variable "native" with "_". |
| `AaG4bQQmnDi6kOcnr-Az` | CODE_SMELL / `python:S1481` | `python/build_backend.py:250` | Replace the unused local variable "package" with "_". |
| `AaG4bQQmnDi6kOcnr-A0` | CODE_SMELL / `python:S9154` | `python/build_backend.py:336` | Combine these nested "with" statements into a single "with" with multiple contexts. |
| `AaG4bQQmnDi6kOcnr-A1` | CODE_SMELL / `python:S9154` | `python/build_backend.py:406` | Combine these nested "with" statements into a single "with" with multiple contexts. |
| `AaG4bQQmnDi6kOcnr-A2` | CODE_SMELL / `python:S9154` | `python/build_backend.py:442` | Combine these nested "with" statements into a single "with" with multiple contexts. |
| `AaG4bQQjnDi6kOcnr-Ar` | CODE_SMELL / `python:S1192` | `python/check_package_metadata.py:20` | Define a constant instead of duplicating this literal "*.whl" 4 times. |
| `AaG4bQQjnDi6kOcnr-As` | CODE_SMELL / `python:S3776` | `python/check_package_metadata.py:38` | Refactor this function to reduce its Cognitive Complexity from 19 to the 15 allowed. |
| `AaG4bQQtnDi6kOcnr-A8` | CODE_SMELL / `python:S1192` | `python/package_ci.py:75` | Define a constant instead of duplicating this literal "runtime-evidence.json" 3 times. |
| `AaG4bQQhnDi6kOcnr-Aq` | CODE_SMELL / `python:S5778` | `python/tests/test_batches.py:124` | Refactor this exception test to have only one invocation possibly throwing an exception. |
| `AaG4bQQpnDi6kOcnr-A4` | CODE_SMELL / `python:S8786` | `python/verify_artifacts.py:23` | Simplify this regular expression to reduce its runtime, as it has super-linear performance due to backtracking. |
| `AaG4bQQpnDi6kOcnr-A5` | CODE_SMELL / `python:S3776` | `python/verify_artifacts.py:49` | Refactor this function to reduce its Cognitive Complexity from 57 to the 15 allowed. |
| `AaG4bQQpnDi6kOcnr-A3` | CODE_SMELL / `python:S1192` | `python/verify_artifacts.py:56` | Define a constant instead of duplicating this literal ".dist-info/METADATA" 3 times. |
| `AaG4bQQpnDi6kOcnr-A6` | CODE_SMELL / `python:S3776` | `python/verify_artifacts.py:138` | Refactor this function to reduce its Cognitive Complexity from 18 to the 15 allowed. |
| `AaG4bQRmnDi6kOcnr-BA` | CODE_SMELL / `python:S1192` | `scripts/performance_study.py:91` | Define a constant instead of duplicating this literal "result.json" 3 times. |
| `AaG4bQRmnDi6kOcnr-BB` | CODE_SMELL / `python:S3776` | `scripts/performance_study.py:94` | Refactor this function to reduce its Cognitive Complexity from 31 to the 15 allowed. |
| `AaG4bQO8nDi6kOcnr-Ap` | VULNERABILITY / `pythonsecurity:S8707` | `python/benchmark.py:178` | Path Traversal via faulty LLM-supplied CLI arguments in benchmark.main() |
| `AaG4bQQrnDi6kOcnr-A7` | VULNERABILITY / `pythonsecurity:S8707` | `python/examples/lab_workflow.py:23` | Path Traversal via faulty LLM-supplied CLI arguments in lab_workflow.load_csv() |
| `AaG4bQQtnDi6kOcnr-A9` | VULNERABILITY / `python:S5443` | `python/package_ci.py:91` | Make sure publicly writable directories are used safely here. |
| `AaG4bQRmnDi6kOcnr-BC` | VULNERABILITY / `pythonsecurity:S8705` | `scripts/performance_study.py:150` | Command Argument Injection via faulty LLM-supplied CLI arguments in performance_study.run() |

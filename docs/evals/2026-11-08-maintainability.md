# Maintainability cleanup: 2026-11-08

Baseline: main `ce204c8e862599e63d39240869b877f8886d36f6`. The public Sonar main
inventory contained exactly 24 OPEN CODE_SMELL issues. This record tracks those
keys individually; it does not change their status through the API. The two
accepted operator risks and the sanitised filter false positive are unchanged.

## Scope and equivalence

- Packaging checks are split into ordered stages. Error messages, check order,
  frozen-source rules, source inventory keys, metadata, warning denial, remapping
  and archive contents remain unchanged. Old and new `inputs()` on the same tree
  produce identical paths and JSON. Against the pre-edit snapshot, only the
  `backend/build_backend.py` entry and its aggregate hash differ. This is an honest
  source-identity change, not byte-reproducibility evidence.
- Old and new verifiers return identical reports for the saved Windows wheel and
  source archive. Prefix scanning agrees on 30 positive/negative UTF-8/UTF-16 cases.
  The linear NEEDED parser is compared with the legacy expression on bounded
  malformed/bracket/duplicate inputs; Linux controls also compare real `readelf -d`
  output without changing the workflow. Missing or unparsed requirements still fail.
- Benchmark results remain alive through tracemalloc snapshots, traced-memory and
  RSS observations; a finalizer oracle checks release occurs afterwards. Timer
  reads, calibration/sample ordering and output fields remain the same. The study
  runner preserves command arguments, seed, reversal, thread settings and resume
  semantics, with no benchmark timing run.
- Rust changes move registration/setup only. The 25 measured `b.iter(...)`
  expressions match after whitespace normalization; the complete `--list` output
  matches (144 lines). Single-value closures retain their arithmetic and barriers.
  The harness smoke test passes. Helper boundaries change the source fingerprint
  and may change code generation; historical timing evidence is unchanged and is
  not presented as measurements of this revision.
- Endian fixture construction is outside the exception assertion, so construction
  failure cannot be mistaken for the buffer-rejection behavior under test.

## Original issue keys

Verified on 2026-11-08 at main
`c047c120fef3b96d2876cebd0101bd2f368b3947` (PR #14 merge), analysis
`54931d52-c22c-4927-91f9-204baa1bb29b` at 04:03:29 UTC. Every original key below
was queried individually: modern `FIXED`, legacy status `CLOSED`, resolution
`FIXED`. None was missing or replaced; the complete main issue-key set remained
the same 28 keys. These are observed results at that commit, not a promise about
future analyses.

| Key | Rule | Baseline location | Refactor | Main result |
| --- | --- | --- | --- | --- |
| `AaG4bQQjnDi6kOcnr-Ar` | python:S1192 | `python/check_package_metadata.py:20` | Static metadata comparison helper and wheel pattern | FIXED |
| `AaG4bQQmnDi6kOcnr-At` | python:S1192 | `python/build_backend.py:44` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-Au` | python:S1192 | `python/build_backend.py:46` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-Av` | python:S3776 | `python/build_backend.py:60` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-Aw` | python:S3776 | `python/build_backend.py:142` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-Ax` | python:S3776 | `python/build_backend.py:170` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-Ay` | python:S1481 | `python/build_backend.py:250` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-Az` | python:S1481 | `python/build_backend.py:250` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-A0` | python:S9154 | `python/build_backend.py:336` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-A1` | python:S9154 | `python/build_backend.py:406` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQmnDi6kOcnr-A2` | python:S9154 | `python/build_backend.py:442` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | FIXED |
| `AaG4bQQjnDi6kOcnr-As` | python:S3776 | `python/check_package_metadata.py:38` | Static metadata comparison helper and wheel pattern | FIXED |
| `AaG4bQQtnDi6kOcnr-A8` | python:S1192 | `python/package_ci.py:75` | Shared runtime evidence filename | FIXED |
| `AaG4bQQpnDi6kOcnr-A4` | python:S8786 | `python/verify_artifacts.py:23` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | FIXED |
| `AaG4bQQpnDi6kOcnr-A5` | python:S3776 | `python/verify_artifacts.py:49` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | FIXED |
| `AaG4bQQpnDi6kOcnr-A3` | python:S1192 | `python/verify_artifacts.py:56` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | FIXED |
| `AaG4bQQpnDi6kOcnr-A6` | python:S3776 | `python/verify_artifacts.py:138` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | FIXED |
| `AaG4bQO8nDi6kOcnr-Ao` | python:S3776 | `python/benchmark.py:47` | Memory/timing helpers and explicit retained-result release | FIXED |
| `AaG4bQO8nDi6kOcnr-An` | python:S1854 | `python/benchmark.py:134` | Memory/timing helpers and explicit retained-result release | FIXED |
| `AaG4bQQhnDi6kOcnr-Aq` | python:S5778 | `python/tests/test_batches.py:124` | Construct endian input before the exception assertion | FIXED |
| `AaG4bQRjnDi6kOcnr-A_` | rust:S3776 | `benches/spatial.rs:505` | Registration helpers, unchanged measured expressions | FIXED |
| `AaG4bQRmnDi6kOcnr-BB` | python:S3776 | `scripts/performance_study.py:101` | Per-profile execution helper and result filename | FIXED |
| `AaG4bQRjnDi6kOcnr-A-` | rust:S3776 | `benches/spatial.rs:427` | Registration helpers, unchanged measured expressions | FIXED |
| `AaG4bQRmnDi6kOcnr-BA` | python:S1192 | `scripts/performance_study.py:91` | Per-profile execution helper and result filename | FIXED |

## Verified main follow-up

Independent review confirmed all 24 exact-key results above. On 2026-11-08 at
`c047c12`, main had 0 OPEN Sonar issues: 25 FIXED (these 24 plus the earlier
S5443), 2 ACCEPTED operator risks and 1 FALSE_POSITIVE. The three security
dispositions retained their exact single comments and original timestamps.
Accepted risks are not eliminated risks; this is not a vulnerability-free claim.

The main collector reported `complete=true`, `partial=false`, bound to the merge
revision and analysis, with a complete hotspot inventory (0). All six gate
conditions passed: new reliability/security/maintainability A, new coverage 84.2%
(threshold 80%), duplication 0.0% and hotspots reviewed 100%. The new-code period
remained 2026-11-07T23:51:23Z. No baseline, threshold, rule or exclusion was
changed, and no manual issue disposition was used for this cleanup.

Post-merge push runs on that exact revision:

- [Sonar 42444900005](https://github.com/TelemetryWorks/spatial-typestate/actions/runs/42444900005): analysis and complete public evidence passed.
- [Rust 42444899959](https://github.com/TelemetryWorks/spatial-typestate/actions/runs/42444899959): 15/15 jobs passed.
- [Python 42444900024](https://github.com/TelemetryWorks/spatial-typestate/actions/runs/42444900024): 4/4 jobs passed, including real readelf comparison and source rebuild/runtime checks.
- [CodeQL 42444900000](https://github.com/TelemetryWorks/spatial-typestate/actions/runs/42444900000): 3/3 jobs passed; Rust/Actions/Python had 0 results with 28/23/50 rules and no errors.

The commit had 26 successful check runs and one expected fork-notice skip, with
no legacy contexts. The one temporary PR-only test finding, S3415
`AaG5RnKvT8I3H7DQeNVd`, was fixed by making the observed assertion tuple explicit
before merge; no new main issue key was introduced. Coverage failures during the
PR prompted the deterministic sampling/routing and metadata regression oracles;
failed runs remain failed history, with no gate or coverage-scope change.

## Validation boundaries

Local differential checks and control tests are distinct from hosted analysis.
The Linux readelf test ran on actual interpreter ELF output and retained a
captured fixture. Final local evidence included Rust all-feature tests and strict
all-target Clippy, harness smoke and registration/closure comparisons, 61 script
tests (4 platform skips), 30 packaging controls (2 Linux skips), and a fresh
wheel/source rebuild with metadata/license/RECORD/path/source parity and 20
installed-wheel runtime tests. Test-only follow-ups also passed with site
packages disabled. No benchmark timing study was run.

The historical security triage, disposition records and performance samples are
unchanged. Future analyses can introduce findings; check the current revision
and gate rather than interpreting this dated snapshot as a perpetual result.

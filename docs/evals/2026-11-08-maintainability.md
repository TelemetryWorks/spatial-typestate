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

Server status after analysis is pending. Completion requires every key below to
be CLOSED/FIXED on main, with no replacement keys, rather than a count-only check.

| Key | Rule | Baseline location | Refactor | Main result |
| --- | --- | --- | --- | --- |
| `AaG4bQQjnDi6kOcnr-Ar` | python:S1192 | `python/check_package_metadata.py:20` | Static metadata comparison helper and wheel pattern | Pending |
| `AaG4bQQmnDi6kOcnr-At` | python:S1192 | `python/build_backend.py:44` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-Au` | python:S1192 | `python/build_backend.py:46` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-Av` | python:S3776 | `python/build_backend.py:60` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-Aw` | python:S3776 | `python/build_backend.py:142` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-Ax` | python:S3776 | `python/build_backend.py:170` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-Ay` | python:S1481 | `python/build_backend.py:250` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-Az` | python:S1481 | `python/build_backend.py:250` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-A0` | python:S9154 | `python/build_backend.py:336` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-A1` | python:S9154 | `python/build_backend.py:406` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQmnDi6kOcnr-A2` | python:S9154 | `python/build_backend.py:442` | Ordered inventory/state/path helpers, shared manifest names, context-manager composition and unused binding removal | Pending |
| `AaG4bQQjnDi6kOcnr-As` | python:S3776 | `python/check_package_metadata.py:38` | Static metadata comparison helper and wheel pattern | Pending |
| `AaG4bQQtnDi6kOcnr-A8` | python:S1192 | `python/package_ci.py:75` | Shared runtime evidence filename | Pending |
| `AaG4bQQpnDi6kOcnr-A4` | python:S8786 | `python/verify_artifacts.py:23` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | Pending |
| `AaG4bQQpnDi6kOcnr-A5` | python:S3776 | `python/verify_artifacts.py:49` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | Pending |
| `AaG4bQQpnDi6kOcnr-A3` | python:S1192 | `python/verify_artifacts.py:56` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | Pending |
| `AaG4bQQpnDi6kOcnr-A6` | python:S3776 | `python/verify_artifacts.py:138` | Ordered verification helpers, metadata suffix and linear NEEDED parsing | Pending |
| `AaG4bQO8nDi6kOcnr-Ao` | python:S3776 | `python/benchmark.py:47` | Memory/timing helpers and explicit retained-result release | Pending |
| `AaG4bQO8nDi6kOcnr-An` | python:S1854 | `python/benchmark.py:134` | Memory/timing helpers and explicit retained-result release | Pending |
| `AaG4bQQhnDi6kOcnr-Aq` | python:S5778 | `python/tests/test_batches.py:124` | Construct endian input before the exception assertion | Pending |
| `AaG4bQRjnDi6kOcnr-A_` | rust:S3776 | `benches/spatial.rs:505` | Registration helpers, unchanged measured expressions | Pending |
| `AaG4bQRmnDi6kOcnr-BB` | python:S3776 | `scripts/performance_study.py:101` | Per-profile execution helper and result filename | Pending |
| `AaG4bQRjnDi6kOcnr-A-` | rust:S3776 | `benches/spatial.rs:427` | Registration helpers, unchanged measured expressions | Pending |
| `AaG4bQRmnDi6kOcnr-BA` | python:S1192 | `scripts/performance_study.py:91` | Per-profile execution helper and result filename | Pending |

## Validation boundaries

Local differential checks and control tests are distinct from hosted analysis.
The real Linux readelf check, four wheel jobs/source rebuild, CodeQL extraction,
Sonar issue tracking and the final main gate must be inspected at the reviewed
commit before this record can claim completion. No source exclusions, dismissals,
baseline changes, rule changes or new dependencies are part of this cleanup.

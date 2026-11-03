# Borrowed validation-amortization prototype

Status: isolated benchmark/test code only. No production public API is added or
approved. [The preceding study](performance.md) and all 600 estimates remain
unchanged. This increment compares caller-local validation hoisting with an
immutable borrowed prototype before choosing whether an API is worthwhile.

## Proposed invariant and supported scope

`benches/support/borrowed.rs` contains two private-field experimental types:

- BorrowedPoint borrows `&'a Transform<From,To,L>` and validates the twelve
  first-three-row affine entries at prepare time. It supports point application
  with the same frame/length tags, exact expression association, point/result
  checks, ignored bottom row and signed-zero behavior as public apply_point.
- BorrowedVector separately validates only the nine linear entries. It supports
  generic-unit vector application, preserving U independently of translation L.
  Translation/bottom rows remain ignored, including NaN/Inf. Requiring point
  preparation for vector-only work would incorrectly reject unused translation.

Neither checks rigidity: finite scaling/shear remains accepted. There is no
prepared composition, inversion, unit conversion, quaternion rewrite, mutation
accessor or unchecked mapping entry point. The scalar arithmetic helpers are
private and are reachable only after the appropriate matrix validation. Every
participating input/output still gets checked on each application.

The reference is stored privately and carries its lifetime and typed Transform.
Safe Rust cannot mutate the matrix through another reference while the prepared
value will be used again, or return a preparation that outlives the map. No
validation cache is attached to publicly mutable raw state, no unsafe is used,
and no matrix copy/allocation is needed. Non-lexical lifetimes can end the borrow
after the last use, even if the variable remains in scope. An update then requires
fresh preparation before further use. The borrow covers the whole Transform:
even a vector-only preparation conservatively prevents editing unused translation
or bottom-row fields while it is live. Ignored numeric values remain accepted;
this prototype is not a fine-grained mutable matrix view. That ergonomics limit
must be considered before a public API decision. The [Rust borrowing documentation](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)
is the language basis; compiler rejection tests are concrete evidence, not a
claim to prove every detail of Rust's aliasing model.

## Error timing is a deliberate pending API decision

An invalid used matrix coefficient returns NonFinite during preparation. A
non-finite input or arithmetic overflow returns NonFinite during application.
This moves matrix-error timing from ordinary calls to preparation and can reject
an invalid matrix even when there are no points. It does not change successful
scalar bits, but it is observably different control flow. The prototype may be
merged as evidence without approving that behavior as a new production API.

Recommended decision for discussion: make preparation explicitly fallible, keep
the current checked Transform methods unchanged, and use operation-specific
validation scopes. Names, visibility, convenience methods and whether both
point/vector prepared types are justified remain subject to review. Do not
promise that a single stronger validator preserves vector-only acceptance.

## Caller-local alternative and fixture protocol

The matched caller-local functions validate the matrix once in the caller loop,
then use the same private scalar input/math/output helpers as borrowed application.
They construct no wrapper and require no persistent API/invariant. This is a
serious alternative: if it matches the borrowed prototype, the performance
evidence supports hoisting, not necessarily a new public type.

For experiment fixtures only, input/output slices have equal lengths, mismatch
panics before writes, invalid matrix returns before writes, and a valid matrix
writes one Result for every input, including failed elements. Successful and
returned-error paths perform no explicit allocation. Deliberate fixture length
violations panic through the test/benchmark runtime; that is not a proposed
allocation-free public shape-error policy.
All benchmark variants use the same shape assertion, inputs, Result output slots,
barriers and per-element error handling. This fixture protocol is not a proposed
general public batch contract. Ordinary reference calls are measured alongside
an exact fully checked local-copy control, to expose codegen/inlining effects.

## Batch policy remains unimplemented

A future batch API would need explicit decisions, rather than inheriting fixture
behavior accidentally:

| Choice | Consequences requiring a decision |
| --- | --- |
| Stop at first failure | Return an index and error; specify whether successful prefix outputs remain and whether the failing/tail slots are untouched. A later bad input is not checked. |
| One Result per element | Every input is checked; caller gets all failures at stable indices. Caller-provided Result slots avoid allocation but consume more storage and writes. |
| Length mismatch | Define a separate shape error, an explicit checked precondition, or an exact-length output abstraction; never silently zip/truncate a public API. |
| Matrix failure / empty input | Decide preparation rejection before any element, including empty input, versus validating only when an element is evaluated. |
| Aliasing and output state | Use safe shared input/mutable output slices; specify partial writes. Point input/output frames may differ, so in-place mapping is a separate design. |
| Allocation | Prefer caller-owned storage for no-std use; no implicit Vec, boxing, unsafe initialization, or hidden allocation. |

This increment implements no general batch API and adds no production error
variant. Existing SpatialError stays exhaustive and unchanged.

## Validation and measurement plan

Focused tests compare finite component bits/error classes with current point and
vector methods across arbitrary bit patterns, every non-finite matrix/input
position, signed zeros, subnormals/MAX, overflow, ignored entries and raw nonrigid
maps. Borrow-checking/private-state/frame/unit rejection is reviewed separately.
Fixture tests check per-element failures, unchanged output on preparation failure,
empty input semantics and mutation/repreparation after last use.

Benchmarks measure N=1/8/64/1024 normal points, N=64 subnormal/point-error/overflow
cases, vector work and ignored non-finite translation, and preparation alone.
Compare ordinary calls, full-check local control, caller-local hoisting, preparing
per batch and reused borrowed preparation. Setup/allocation is outside timing;
end-to-end cases include validation. Keep matching barriers and output handling.
Inspect all emitted loops for calls, matrix-check placement and packed arithmetic.

Use three fresh repeats for std, actual no-std and no-LTO/cgu16 std, separate
from earlier evidence. Prebuild, arrange a quiet window, bound analysis workers,
retain medians/CIs/raw samples/spikes and record the exact source/environment.
Results are host/caller/profile-specific, not universal, embedded or worst-case
timing guarantees. No scalar rewrite, six-step normalization, new dependency,
tool installation, compiler-policy or release change is part of this increment.

## Results and recommendation

### Protocol and provenance

The separate 2026-11-03 study collected **423 estimates / 16,920 samples** in nine
fresh processes: three std/LTO, three actual no-std/LTO and three std/no-LTO/cgu16.
Each process measured only the 47 amortization/setup cases. Settings: 40 samples,
200 ms warmup, 700 ms measurement, 10,000 bootstrap resamples, default 95% intervals
and 3% Criterion noise threshold. Measured operations are serial; bootstrap
analysis is explicitly capped at two workers, and compilation used two jobs.
Binaries were prebuilt. Total process wall time was 449.0 seconds.

```powershell
python scripts/performance_study.py --prepare
python scripts/performance_study.py --run --study borrowed-host --filter '^amortization' --analysis-threads 2
```

Host: Ryzen 7 2700, 8 cores/16 logical processors, Windows 11 Pro build 26200,
rustc 1.99.0 (b940084d7, LLVM 23.1.1), generic x86-64. High performance plan was
already active; WMI reported nominal/current 3200 MHz, not an actual turbo trace.
Turbo/thermal state is unknown, affinity OS-default. Other agents paused heavy
work, but the pre-measurement CPU snapshot was **13%**, not an idle-machine claim;
background activity was not continuously excluded or monitored. No system
setting was changed. Fresh per-run metadata records compiler, source fingerprint,
commands, configuration/order, seed and worker cap.

Data: [all per-run medians and intervals](performance/2026-11-03-borrowed/estimates.csv),
[three-run summaries/CV](performance/2026-11-03-borrowed/summary.csv),
[raw samples](performance/2026-11-03-borrowed/samples.jsonl.gz),
[metadata](performance/2026-11-03-borrowed/metadata.json), and
[exact fingerprint source inputs](performance/2026-11-03-borrowed/source.tar.gz).
The old 600 estimates were not edited or pooled with these results. The new
harness writes per-element Results rather than unwrapping each success, so its
absolute timings must not be directly equated with the preceding valid-only
batch measurements. No repeated run was discarded.

N is a batch length, not independent concurrent work. Normal points cycle the
same 64 seeded fixture points for larger N. The fixed cyclic mixed-NaN N=64 case
contains five NaN points (7.81% realized density), not unpredictable independent
failures. Subnormal matrices are finite/nonrigid; overflow matrices are finite.
All matrix values used by the timed batch methods are valid for that method;
invalid-matrix preparation is measured separately. Preparation cost moves outside
the timer only for borrowed_reuse. Scalar arithmetic has no std-dependent branch;
no-std repetition confirms configuration behavior, not a separate algorithm gain.

All cells below are **ns per whole batch, median of three run medians [min,max]**.
Ranges are not confidence intervals; within-run 95% intervals remain in the CSV.
No pooled significance claim or universal break-even N is inferred.

### Normal points

| Profile / N | Public scalar loop | Full-check local copy | Caller hoisted once | Borrow prepare each batch | Borrow reused |
| --- | --- | --- | --- | --- | --- |
| lto-std / 1 | 14.67 [13.97, 15.59] | 13.97 [13.70, 14.37] | 15.35 [15.28, 17.47] | 12.76 [12.70, 14.04] | 8.46 [8.34, 8.46] |
| lto-std / 8 | 91.57 [90.79, 91.58] | 90.72 [90.45, 91.69] | 54.72 [54.54, 54.87] | 53.58 [53.19, 53.81] | 51.55 [50.76, 56.56] |
| lto-std / 64 | 710.45 [708.67, 710.93] | 714.52 [709.37, 715.03] | 382.46 [378.14, 385.48] | 393.94 [390.83, 395.07] | 401.63 [398.70, 417.53] |
| lto-std / 1024 | 11244.10 [11140.31, 11488.19] | 11234.25 [11139.66, 11634.12] | 5858.02 [5857.90, 5897.18] | 6169.89 [6147.58, 6222.23] | 6423.47 [6404.05, 6433.60] |
| lto-no-std / 1 | 14.00 [13.90, 14.27] | 13.81 [13.77, 13.98] | 14.71 [13.86, 14.81] | 12.68 [12.55, 12.72] | 8.36 [8.08, 8.48] |
| lto-no-std / 8 | 90.97 [90.53, 92.02] | 91.43 [90.99, 91.47] | 54.90 [53.59, 55.64] | 54.21 [52.92, 54.27] | 50.87 [50.55, 51.11] |
| lto-no-std / 64 | 710.75 [710.23, 717.30] | 712.59 [706.41, 713.07] | 381.88 [377.21, 386.87] | 392.35 [391.92, 393.33] | 398.35 [397.70, 402.09] |
| lto-no-std / 1024 | 11195.12 [11190.02, 11224.98] | 11480.98 [11170.59, 11546.34] | 5956.96 [5866.86, 6216.35] | 6147.72 [6135.46, 6299.64] | 6399.16 [6333.32, 6554.86] |
| nolto-std / 1 | 15.73 [15.49, 18.04] | 15.56 [15.51, 17.33] | 15.48 [15.38, 15.49] | 12.66 [12.57, 12.76] | 8.22 [8.18, 8.28] |
| nolto-std / 8 | 104.06 [103.97, 104.13] | 103.87 [103.63, 104.81] | 54.85 [54.51, 55.44] | 53.60 [53.04, 54.05] | 51.77 [51.18, 56.79] |
| nolto-std / 64 | 835.86 [820.67, 848.32] | 817.79 [817.05, 833.08] | 375.89 [375.49, 375.97] | 390.90 [390.46, 404.29] | 402.51 [397.98, 407.13] |
| nolto-std / 1024 | 12973.36 [12920.24, 13132.87] | 12984.21 [12983.89, 13019.69] | 5813.99 [5784.71, 5867.27] | 6167.52 [6143.86, 6171.16] | 6387.98 [6297.65, 6406.45] |

At N=64 the like-for-like caller-hoisted point medians are about 376–382 ns,
versus 391–394 ns with preparation included. N=8 is close; N=1 is largely fixed
harness/shape/validation/codegen cost and borrowed reuse excludes preparation.
At N=1024 the caller-local loop is also faster here. These are observations about
these callers, not proof that a wrapper always costs more or that one path is
optimal. Never add standalone preparation timing to a fused batch measurement:
materialization and optimizer context differ.

### Adversarial points and vector scope (N=64)

| Profile / case | Public | Caller hoisted once | Borrow prepare each batch | Borrow reused |
| --- | --- | --- | --- | --- |
| lto-std / point subnormal | 846.04 [731.58, 866.71] | 415.57 [413.24, 417.18] | 527.67 [519.23, 562.37] | 503.38 [482.80, 519.25] |
| lto-std / point mixed_nan | 661.64 [659.36, 662.35] | 360.46 [357.15, 361.21] | 374.28 [364.77, 376.65] | 385.16 [374.60, 448.40] |
| lto-std / point overflow | 652.66 [652.46, 673.39] | 362.42 [360.81, 362.82] | 367.12 [360.37, 371.63] | 367.43 [360.70, 369.07] |
| lto-std / vector valid | 819.98 [819.44, 820.36] | 357.73 [357.71, 359.77] | 366.04 [364.38, 372.57] | 384.47 [383.97, 386.54] |
| lto-std / vector ignored_translation | 828.98 [817.10, 878.83] | 357.58 [357.47, 358.91] | 368.85 [364.66, 370.65] | 382.81 [382.74, 385.23] |
| lto-no-std / point subnormal | 738.37 [738.07, 739.96] | 418.31 [408.23, 419.48] | 553.25 [552.48, 556.51] | 494.03 [491.35, 497.14] |
| lto-no-std / point mixed_nan | 666.55 [660.22, 667.33] | 360.06 [356.60, 360.31] | 365.21 [363.62, 386.97] | 374.14 [372.85, 376.20] |
| lto-no-std / point overflow | 656.65 [650.55, 662.95] | 351.40 [347.18, 352.67] | 364.57 [359.20, 369.79] | 363.00 [354.88, 375.55] |
| lto-no-std / vector valid | 849.10 [825.73, 861.24] | 372.69 [369.78, 372.83] | 372.60 [369.89, 404.05] | 392.86 [383.29, 398.24] |
| lto-no-std / vector ignored_translation | 829.01 [828.69, 846.25] | 373.57 [358.43, 390.11] | 366.27 [365.43, 379.06] | 381.03 [380.17, 381.40] |
| nolto-std / point subnormal | 819.33 [807.43, 839.17] | 404.66 [401.99, 407.56] | 545.87 [536.23, 566.21] | 553.34 [509.13, 623.91] |
| nolto-std / point mixed_nan | 827.33 [814.33, 838.99] | 353.78 [350.88, 370.55] | 404.16 [404.13, 406.22] | 412.40 [409.90, 415.49] |
| nolto-std / point overflow | 770.59 [766.36, 777.70] | 357.31 [355.20, 360.59] | 359.55 [357.55, 361.19] | 356.24 [356.22, 357.71] |
| nolto-std / vector valid | 673.93 [671.11, 675.61] | 351.37 [349.61, 352.54] | 368.85 [364.58, 370.87] | 381.33 [380.29, 384.05] |
| nolto-std / vector ignored_translation | 672.09 [670.69, 688.59] | 350.15 [349.76, 350.75] | 364.30 [364.04, 365.21] | 380.96 [380.55, 386.66] |

The caller-local alternative is competitive, frequently faster, including error
Results and vector work. The ignored-translation case accepts non-finite unused
translation and bottom rows; stronger point validation is not substituted.
Preparation/reuse is not a uniform latency win. Retained spikes include no-LTO
mixed-NaN full-local 815.77–1006.25 ns, no-LTO subnormal borrowed reuse
509.13–623.91 ns, and LTO/std mixed-NaN borrowed reuse 374.60–448.40 ns.
Their causes are not established, and small differences near those spreads are
not decisive. The largest between-run CV in these cases is about 10.2%.

### Preparation alone

| Profile | Point valid | Vector valid | Point bad translation | Vector bad linear entry |
| --- | --- | --- | --- | --- |
| lto-std | 9.71 [9.66, 9.73] | 9.02 [8.98, 9.08] | 8.07 [8.05, 8.11] | 9.00 [8.99, 9.02] |
| lto-no-std | 9.76 [9.65, 9.78] | 9.10 [9.01, 9.15] | 8.13 [8.06, 8.34] | 9.10 [9.09, 9.20] |
| nolto-std | 9.75 [9.60, 9.99] | 9.06 [9.04, 9.24] | 8.08 [8.05, 8.14] | 9.00 [8.99, 9.20] |

These standalone costs include returning/barriering the prototype Result, so they
are not additive components of a batch pipeline or a general amortization formula.

### Emitted loops

[Exact emission commands](performance/2026-11-03-borrowed/codegen-commands.json) use
the benchmark profile with assembly/LLVM IR output in all three configurations.
The [inspection index](performance/2026-11-03-borrowed/codegen-inspection.json)
records 27 timing-loop kernels plus two once-per-batch no-LTO caller helpers.
Full function excerpts are retained next to the index for independent review.
Static instruction counts include vector lanes/rolled loops; they are not dynamic
validation counts, scalar FLOPs or cycle models.

- Public/full-local point loops retain matrix checks on per-point paths. In the
  public LTO vector loop, three static matrix comparisons execute in a nested
  three-row loop: nine used coefficients per element, not merely three checks.
- Caller-local point/vector validation is before the element loop, as is
  prepare_each_batch validation. Borrowed reuse has no matrix validation inside
  timing. All retain three input and three output component checks per element.
- All mapping bodies inline for the LTO loops. In the no-LTO build, caller-local
  point/vector loops are called once per batch; their retained helpers contain
  the before-loop matrix check and per-element math/checks. This is not a call
  per element. The other mapping bodies inline.
- Point arithmetic packs independent lanes in prepare/reuse and no-LTO full-check
  loops, while the LTO full-check and caller-local point bodies are scalar here.
  Vector arithmetic is scalar. Inlining, alias information, loads and packing
  differ; the new timings cannot attribute every ns to validation alone. No
  fast-math, association rewrite or production inline hint is introduced.

### Recommended API decision for discussion

**Do not promote a public API from speed alone.** This study establishes a sound
borrowed invariant and a meaningful hoisting benefit at these call sites, but
caller-local hoisting is not slower overall and often wins. Its prototype uses
private math helpers; current application callers cannot obtain that speed simply
by validating a matrix and then calling today's scalar API, and copying private
math into applications is not recommended as a supported optimization.

If users need a validated capability spanning repeated scalar calls/functions,
the smallest option to review is an explicitly fallible point-preparation method
returning an immutable lifetime-bound mapper, with existing checked Transform
methods unchanged. Prepare rejects used matrix entries even for zero later calls;
application still returns Result for every point. Accept finite raw nonrigid maps.
A separate vector preparation scope is necessary to preserve unused-translation
acceptance if vector support is included. Names/visibility/value traits are not
chosen production contracts by this prototype. The whole-map borrow blocks even
unused-field updates until last use; that ergonomics cost must be accepted first.

If the need is only bulk throughput, a library-internal hoisted batch loop may be
simpler than a persistent type, but exposing it requires the failure/shape/partial
write decisions in the table above. Recommend no general batch API in the first
promotion. Coordinator/user should decide preparation error timing and whether
scalar prepared capability is actually needed; until then both options remain
experimental. Further caller/codegen/ergonomic evidence can precede promotion,
without extending this bounded study or weakening the existing checked methods.


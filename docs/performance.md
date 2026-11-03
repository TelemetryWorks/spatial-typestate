# Host performance study

This is a characterization of one host/compiler/profile, not a timing guarantee,
embedded measurement, proof of global optimality, or universal optimization.
The accompanying data retains independent runs and uncertainty. No library
optimization or new public API is justified merely by a faster isolated case.

## Reproduction and scope

The existing Criterion 0.5.1 dev dependency drives `benches/spatial.rs`. The
benchmark executable uses std in every configuration; disabling library defaults
selects the actual private no-std quaternion helper, not a relabeled std build.
There are no new dependencies or local tool installations. No version, MSRV,
toolchain pin, floating-point flags, or public math contract changes.

```powershell
$env:CARGO_BUILD_JOBS = '2'
cargo +1.99.0-x86_64-pc-windows-msvc bench --locked --jobs 2 --bench spatial -- --test
python scripts/performance_study.py --prepare
# Arrange a quiet window; preparation builds all configurations beforehand.
python scripts/performance_study.py --run --study host-study
```

The optional Python runner uses only its standard library. Its installed
toolchain selector is Windows-specific; the Criterion target itself is portable.
Individual groups can be selected without running the whole study:

```powershell
cargo +1.99.0-x86_64-pc-windows-msvc bench --locked --jobs 2 --bench spatial -- point_candidates
cargo +1.99.0-x86_64-pc-windows-msvc bench --locked --jobs 2 --bench spatial --no-default-features --features no_std -- quaternion
```

The runner records exact commands, compiler version, source fingerprint, seed,
order, raw Criterion samples and estimates under `target/performance-study/`.
Completed runs are preserved on resume; incomplete attempts receive a fresh
Criterion directory rather than mixing partial data. Do not benchmark while
other builds/tests or heavy CPU/I/O work run. One measured process at a time.

## Method and interpretation

- Three fresh processes each for LTO/std, LTO/no-std and a selected no-LTO/std
  subset: nine processes, not nine independent hosts. Feature order alternates
  and the second repeat reverses candidate registration. Input seed is fixed.
- The crate-profile runs use opt-level 3, LTO enabled, one codegen unit, generic
  x86-64 target. The downstream-like subset overrides bench LTO=false and
  codegen-units=16. A downstream application's own Cargo profile controls it;
  these two builds do not span every possible deployment configuration.
- Each case uses 40 samples, 200 ms warmup, 700 ms measurement, 10,000 bootstrap
  resamples, default 95% intervals, and a 3% Criterion noise threshold. Intervals
  describe samples within a process, not uncertainty across hosts or future runs.
  Multiple comparisons are exploratory, not corrected significance claims.
- Runtime fixture generation and allocation happen outside timing. Independent
  calls cycle indexed inputs and barrier both used inputs and results. The
  input-control case exposes part of the harness cost; it is not subtracted.
  Error paths can be mostly barrier/index/copy overhead. Nanosecond estimates
  come from aggregate iterations, not individual timer reads.
- Normal cases have 64 records. Seeded mixed failures use 4,096 records at
  approximately 1/8 density; this larger working set changes cache behavior.
  Compare candidates within that distribution, not its absolute cost to the
  smaller normal set. The sequence is deterministic/cyclic, not a claim of
  perfect branch unpredictability. Uniform late-NaN/overflow cases are predictable.
- Subnormal coordinates and off-diagonal matrix entries include arithmetic
  underflow. `inverse_subnormal` returns NonRigidTransform for its 0.5 diagonal,
  so it is not a valid subnormal-inverse arithmetic measurement. Vector mapping
  ignores translation. Shrinking foot conversion separately exercises underflow.
- Quaternion inputs include broad xyz/w=1, near-unit, MAX/subnormal, and alternating
  zero/NaN errors. The broad case is not a uniform distribution of orientations.
  Near-unit fixtures come from checked setup normalization in each library mode;
  small feature-dependent rounding differences are possible. Replay8 is checked
  bitwise against the actual no-std library, including errors; std public uses
  native sqrt, so a Newton replay is a different implementation there.
- Batch64 tests report time for the whole batch, with Elements(64) throughput.
  Dependent-chain64 is a serial critical path, not independent-call throughput.
  Sequential/composed workflows include explicit foot conversion. They can round
  differently and reject different intermediates; they are not interchangeable
  error/bit contracts. Timed output stores and Result handling are included.

## Environment and results

The 2026-11-03 host was an AMD Ryzen 7 2700 (8 cores/16 logical processors),
Windows 11 Pro build 26200, rustc 1.99.0 (b940084d7, LLVM 23.1.1), generic
x86_64-pc-windows-msvc. High performance power plan was already active; WMI
reported 3200 MHz nominal/current, not verified instantaneous frequency. Turbo
state and thermals are unknown; affinity was the OS default. A pre-measurement
snapshot showed 1% total CPU. Other agents paused heavy work, but unrelated
background activity was not continuously excluded or monitored. No system
settings were changed.

Nine processes completed in 539.5 measured-study wall seconds, producing 540
case estimates and 21,600 samples (plus an excluded short collector preflight).
Mixed placement had 505/4096 failures (12.33%). The record array is about 1.34 MiB
in mixed cases versus 21.5 KiB for 64 normal records; this is not a pure branch
prediction experiment.

Data: [every per-run median/mean and 95% bootstrap interval](performance/2026-11-03/estimates.csv),
[three-run summaries and between-run CV](performance/2026-11-03/summary.csv),
[compressed raw samples](performance/2026-11-03/samples.jsonl.gz), and
[environment, commands, orders and source fingerprint](performance/2026-11-03/metadata.json).
All successful repeats, including spikes, are retained. Numbers below are **ns per
iteration, median of three run medians [minimum, maximum run median]**, not
confidence intervals. The per-run intervals are in the CSV; repeats are not pooled.

| Checked operation, normal inputs | LTO/std | LTO/no-std | no-LTO/std, 16 CGUs |
| --- | --- | --- | --- |
| Point apply | 17.60 [17.60, 17.80] | 17.92 [17.68, 17.93] | 15.75 [15.70, 15.78] |
| Vector apply | 16.46 [16.43, 16.53] | 16.53 [16.52, 17.02] | 13.71 [13.70, 13.72] |
| Composition | 34.04 [33.89, 34.12] | 34.36 [33.54, 34.60] | 31.84 [31.68, 31.85] |
| Rigid inverse | 45.01 [44.81, 46.16] | 45.01 [44.95, 45.19] | 45.62 [45.43, 46.14] |
| Checked matrix construction | 12.87 [12.86, 12.90] | 12.89 [12.85, 12.90] | 12.96 [12.93, 12.99] |
| Normalize + construct + apply | 46.20 [46.14, 46.33] | 92.08 [91.68, 96.55] | not run |
| Quantity conversion | 8.37 [8.36, 8.37] | 8.39 [8.36, 8.40] | 8.37 [8.36, 8.62] |
| Point conversion | 8.69 [8.68, 8.73] | 8.69 [8.68, 8.69] | 8.07 [8.06, 8.28] |
| Vector conversion | 8.39 [8.38, 8.40] | 8.39 [8.34, 8.41] | 8.08 [8.05, 8.15] |
| Transform conversion | 18.94 [18.91, 18.95] | 19.86 [18.95, 23.14] | 27.69 [27.47, 27.93] |
| Quaternion normalization | 27.95 [27.91, 29.80] | 45.49 [45.46, 45.65] | 27.85 [27.66, 27.87] |
| Harness point/index control | 3.77 [3.77, 3.77] | 3.78 [3.77, 3.79] | not run |

These figures include the harness/copies/Result processing; do not subtract the
control or add isolated operation times to predict pipelines. Compiler fusion,
inlining, ABI and output materialization differ between whole functions.

| Point hypothesis / distribution | Reference | Eager checks | Row fusion |
| --- | --- | --- | --- |
| lto-std / valid | 17.72 [17.71, 17.73] | 13.73 [13.73, 13.74] | 16.56 [16.56, 16.61] |
| lto-std / mixed_1in8 | 18.55 [18.53, 18.58] | 15.93 [15.89, 15.96] | 16.92 [16.91, 17.01] |
| lto-std / late_nan | 13.15 [13.14, 13.31] | 10.12 [10.09, 10.13] | 13.86 [13.79, 13.95] |
| lto-std / overflow | 16.52 [16.50, 16.62] | 13.22 [13.21, 13.30] | 9.51 [9.51, 9.51] |
| lto-std / subnormal | 27.02 [26.98, 27.14] | 25.15 [25.11, 44.20] | 17.96 [17.90, 28.07] |
| lto-no-std / valid | 17.80 [17.68, 17.93] | 13.99 [13.75, 21.21] | 16.57 [16.48, 16.59] |
| nolto-std / valid | 15.76 [15.74, 16.01] | 14.40 [14.39, 14.44] | 16.46 [16.44, 16.73] |
| nolto-std / mixed_1in8 | 16.65 [16.59, 16.67] | 16.98 [16.91, 17.02] | 16.96 [16.94, 16.98] |
| nolto-std / subnormal | 16.51 [16.40, 16.55] | 32.52 [32.09, 33.21] | 20.78 [20.40, 20.87] |

**No point candidate is promoted.** Eager reduction's median LTO/std normal time
is about 22.5% lower, but its no-LTO subnormal median is about 97% higher; row
fusion also regresses in that profile. One LTO/no-std eager-normal run rose to
21.21 ns; one LTO/std eager-subnormal run reached 44.20 ns (versus other runs
near 25.1). These are real observations, not removed outliers or attributed to
a proven cause. A narrowly selected success benchmark would hide material risks.

| Batch or norm hypothesis | LTO/std | LTO/no-std | no-LTO/std |
| --- | --- | --- | --- |
| Checked batch, 64 points | 643.10 [642.68, 653.40] | 646.17 [645.56, 648.02] | 662.71 [662.15, 663.57] |
| Prepared reused batch, 64 points | 320.81 [319.65, 326.09] | 318.45 [317.92, 320.22] | 317.67 [317.66, 320.53] |
| Prepare each batch + 64 points | 322.45 [321.15, 328.74] | 320.66 [320.08, 320.95] | 320.53 [320.12, 325.12] |
| Preparation alone (128-byte result) | 30.40 [30.36, 30.55] | 30.43 [29.82, 30.48] | 13.98 [13.94, 14.00] |
| Prepare + one point | 17.93 [17.89, 18.18] | 17.92 [17.91, 18.13] | 17.39 [17.32, 17.42] |
| Sequential two-stage + feet, batch64 | 1208.85 [1208.33, 1214.65] | 1213.40 [1211.76, 1213.99] | not run |
| Compose per batch + feet, batch64 | 440.53 [439.46, 441.32] | 440.59 [438.23, 442.53] | not run |
| Same composition workflow, SoA input | 502.95 [502.95, 506.65] | 510.38 [508.54, 513.03] | not run |
| Dependent chain, 64 applications | 319.66 [318.80, 321.26] | 320.20 [320.07, 329.16] | not run |
| Newton replay8, broad quaternion | 44.09 [44.02, 71.61] | 43.88 [43.87, 44.13] | not run |
| Newton replay6, broad quaternion | 36.21 [35.91, 36.29] | 35.86 [35.84, 36.39] | not run |

Prepared end-to-end batches are about half the checked-batch time on these call
sites, including preparation per batch, but this delta is confounded by public
out-of-line calls versus inlined experiment code. It does not establish that
skipping matrix checks caused the gain or justify a new prepared API. Preparation alone materializes a large
result through black_box; its cost must not be arithmetically added to a fused
batch timing or used to infer a universal break-even point. The compiler is
allowed to hoist checks at ordinary inlined call sites too; this experiment
neither guarantees this benefit elsewhere nor rules out other hoisted cases.
There is no public prepared API in this change.

Composing once per valid batch is faster here than two sequential mappings,
but changes floating-point evaluation/intermediate-error behavior. SoA input
is slower than AoS in this measured workflow, not a generally better layout.
The serial chain is not independent throughput and can exploit invariant data.

Six versus eight Newton steps reduce the no-std **replay** median by about 18.3%.
Replay8 matches public no-std bits in the tests, but returns an array rather than
UnitQuat; codegen/ABI still differ from the public method. Under std the native
sqrt path is already faster than either replay. One std replay8 run spiked to
71.61 ns, while the other two were near 44; retained data prevents overconfidence.
The library still takes eight steps. No universal bit equivalence or floating
roundoff proof is inferred from the dense/random samples.

## Generated-code inspection

Actual Criterion targets were emitted with `cargo +1.99.0-x86_64-pc-windows-msvc
rustc --locked --profile bench --bench spatial --jobs 2 -- --emit=asm,llvm-ir`.
Repeat with CARGO_PROFILE_BENCH_LTO=false and
CARGO_PROFILE_BENCH_CODEGEN_UNITS=16 for the comparison build.
Artifacts stay under target; [selected kernel inspection](performance/2026-11-03/codegen-inspection.json)
records symbols, calls, barriers and instruction counts. Counts are IR
instructions, including vector lanes, not scalar operation counts or cycle models.

The inspected LTO timing closures retain four input/output barriers and actual
arithmetic, or call the retained public apply_point kernel; they are not empty
loops. Eager's LTO closure includes packed floating comparisons whereas row-local
checks are scalar. In this build the public point call remains out of line while
the two experimental bodies inline; no-LTO retains calls for all three, and the
public arithmetic packs independent coordinate lanes. Thus measured differences
include compiler inlining/packing choices, not just a pure check-count effect.
No blanket inline attribute or target-cpu=native flag is justified by this study.

Inspected point additions keep their association without reassoc/contract flags.
Some finite-input multiplications acquire compiler-inferred nnan after guards:
finite*finite cannot produce NaN, though overflow can still produce infinity.
Output checks remain. This is not a requested fast-math setting or permission
to drop input/output validation. Subnormal performance causality is not proven
by the IR alone; no hardware-assist counter was collected.

## Matched inlining/validation control study

Review identified that the initial single-point kernels mixed inline/out-of-line
code generation. The initial batch difference therefore could not be attributed
from those single-point kernels. A separate followup used an **exact full-check
copy** with the same inline hint, an exact full-check copy with a forced-inline
hint, the public method, and the prepared experiment. Nothing changed in the
library. Both copies are checked bitwise/classification-wise against the public
method. Forcing an experimental hint is a control, not a production recommendation.

Six additional fresh processes (three per std LTO/no-LTO profile), reversed
profile/candidate order in the second repeat, collected 60 estimates/2,400 samples.
The original 540 estimates were preserved. Same-host/plan context applies; the
original environment snapshot was not remeasured for turbo/CPU load in the followup.
The distinct source fingerprint and commands are in the
[control metadata](performance/2026-11-03/controls/metadata.json),
[per-run medians/CIs](performance/2026-11-03/controls/estimates.csv),
[summary](performance/2026-11-03/controls/summary.csv), and
[raw samples](performance/2026-11-03/controls/samples.jsonl.gz).
Exact fingerprint inputs are archived for the
[original harness](performance/2026-11-03/source.tar.gz) and
[control harness](performance/2026-11-03/controls/source.tar.gz).
The current harness includes the controls; extract the original snapshot into a
separate scratch checkout to reproduce exactly the original 78-case full passes.

```powershell
python scripts/performance_study.py --prepare --configs lto-std,nolto-std
python scripts/performance_study.py --run --study controls --configs lto-std,nolto-std --filter '^controls/'
```

Again, ns are median of three run medians [min,max], not confidence intervals.

| Control | LTO/std | no-LTO/std |
| --- | --- | --- |
| One normal point, public | 18.25 [17.74, 18.46] | 15.83 [15.74, 16.04] |
| One normal point, local exact copy | 17.92 [17.40, 18.01] | 15.98 [15.88, 16.19] |
| One normal point, forced inline copy | 17.70 [17.36, 17.85] | 18.70 [17.99, 20.05] |
| One subnormal point, public | 27.53 [27.16, 28.02] | 16.41 [16.33, 16.44] |
| One subnormal point, local exact copy | 23.43 [23.03, 23.84] | 18.59 [18.46, 18.67] |
| One subnormal point, forced inline copy | 23.86 [23.25, 24.36] | 19.51 [19.34, 19.62] |
| Batch64, public | 673.60 [653.95, 777.22] | 670.88 [668.37, 672.41] |
| Batch64, local exact copy | 655.40 [651.52, 800.60] | 667.85 [666.14, 682.56] |
| Batch64, forced inline full checks | 651.15 [647.67, 682.15] | 671.38 [665.58, 671.77] |
| Batch64, prepared reused | 325.91 [323.98, 333.04] | 319.84 [318.41, 321.08] |

The [four batch kernels in each profile](performance/2026-11-03/controls/codegen-inspection.json)
were inspected, with their exact function IR excerpts retained next to that file.
**All four batch applications inline in this followup**, including the public
method. Thus its batch timings are not 64 out-of-line calls. This differs from
the original single-call harness, and demonstrates why inlining cannot be
inferred from a different caller. The method is generic and monomorphized in the
benchmark crate; the inliner cost decision is not a crate-boundary restriction.

For public/local/forced full-check batches in both profiles, the twelve matrix
comparisons remain on inner per-point paths, not hoisted to the loop preheader.
All also retain three point checks and three output checks. Prepared has those
six per-point checks and no repeated matrix validation. The LTO full-check batch
arithmetic is scalar while prepared packs independent coordinate lanes. The
no-LTO build packs arithmetic in all four, but still retains repeated matrix
checks in the three full-check variants. No addition reassociation is introduced.
This supports repeated validation/code organization as a lever at these call
sites; it does not prove every nanosecond of the delta comes from comparisons
alone. Code shape, vectorization, barriers/alias information and compiler
heuristics still matter.

Forcing full-check inlining did not close the batch gap (651 vs 326 ns LTO;
671 vs 320 ns no-LTO). It did not give a broad single-point gain either. Some
followup LTO full-check batch runs spiked to 777/801 ns; they are retained. These
results resolve the specific out-of-line batch-call attribution concern, not
all possible compiler/harness alternatives. Ordinary callers with different
aliasing/barriers may hoist matrix validation successfully without a new API.

## Next focused candidate

Investigate **validation amortization at reused-transform call sites** before
changing scalar checks or global inline hints. An opt-in borrowed prepared
transform is a bounded design candidate, not an implemented API or a demonstrated
universal best solution. A shared immutable borrow can enforce a validation
lifetime without copying 128 bytes, retain frame/length tags and checked per-point
inputs/outputs, and require dropping the borrow before matrix/calibration updates.

First compare a caller-local validated loop versus a borrowed prepared prototype,
check whether simpler code organization permits ordinary LLVM hoisting, and
settle moved bad-matrix error timing. A batch API additionally needs failed-element/
partial-write semantics. A scalar prepared type in a caller loop is smaller than
inventing a batch-result API, but its benefit must survive matched full-check
controls and real downstream call sites. No new API is approved by this report.

Future acceptance: reference finite bits/errors, borrow-mutation rejection,
frame/unit mismatches, preparation plus N=1/8/64/1024 actual uses, both profiles
and std/no-std, code-size/caller effects and codegen inspection. The six-step norm
remains secondary: explicit algorithm approval, bounded floating-roundoff analysis,
adversarial validation and target measurements are needed before changing the
documented eight-step path. No production change is promoted in this study.

## Research and experimental decisions

[Criterion's same-group comparisons](https://bheisler.github.io/criterion.rs/book/user_guide/comparing_functions.html)
motivate paired candidates under identical data/harness. Its
[timing-loop guidance](https://bheisler.github.io/criterion.rs/book/user_guide/timing_loops.html)
motivates `iter` for allocation-free operations. Rust documents
[`black_box` as best-effort](https://doc.rust-lang.org/std/hint/fn.black_box.html),
so source barriers are accompanied by generated-code inspection rather than
treated as a proof against dead-code elimination.

The isolated candidates are hypotheses, not claims of scientific novelty:

1. Eager boolean finite-check reduction may expose independent comparisons to
   packing, trading away short circuiting. It retains every participating check
   and all arithmetic expression associations.
2. Row-local validation/computation/output checks may avoid a separate matrix
   scan but introduce branches and a different early-error schedule. All errors
   are still NonFinite and successful bits are compared to the public method.
3. Six Newton steps are compared to eight in full normalization replays. Existing
   convergence analysis suggests investigating fewer bounded iterations, but
   sampling is not an all-input bit/rounding proof. The documented eight-step
   library implementation remains in force.
4. Immutable preparation owns a private matrix copy, validating its first three
   rows once and each point/output on every use. The experiment measures preparation
   alone, per-point preparation, reused batches and preparation included per batch.
   Ordinary checked batch calls remain inlineable, allowing compiler hoisting;
   neither side gets an artificial per-element barrier advantage.
5. AoS versus SoA and composing once per batch test caller workflow organization.
   They are not new APIs or blanket recommendations to reorder floating-point work.

Rust's [code-generation reference](https://doc.rust-lang.org/reference/attributes/codegen.html)
describes inlining as a hint that can also hurt. We inspect code rather than
adding attributes indiscriminately. LLVM's
[fast-math flags](https://llvm.org/docs/LangRef.html#fast-math-flags) can relax
NaN/Inf, signed-zero and association semantics; none are enabled. There is no
FMA rewrite, reciprocal approximation, removed output check, unsafe path or
automatic unit conversion.

## Prepared/batch design boundary

A future immutable prepared type could retain frame/length tags and the exact
scalar arithmetic, own validated coefficients, and check every input/output.
Its matrix cannot remain publicly mutable: caching a successful check next to
the existing mutable Transform would become stale. Copy/ownership or borrowing
without mutation must enforce the validation lifetime. The experiment owns a copy.

Preparation changes where a bad matrix errors, so promotion requires an explicit
API decision. A batch API must also decide whether to stop at the first error or
write a Result for every element, and define index reporting, output length,
partial writes, aliasing and allocation policy. No such semantics are silently
introduced here. Batch results on valid inputs do not answer those questions.
Per-batch preparation includes the one-time cost; reuse timings exclude it.
If ordinary inlined calls already hoist checks, a small prepared delta applies
only to those tested call sites, not to opaque/non-inlined consumers.

## Correctness and limitations

`tests/performance_candidates.rs` compares success classification and finite
bits, including signed zeros, arbitrary bit patterns, non-finite positions,
ignored bottom rows, extremes and preparation ownership. Norm experiments use
the existing native-reference/residual/normalization allowances plus actual
no-std replay equivalence. They supplement the existing complete contract suite;
they are not formal proofs or new library guarantees.

No affinity, power, turbo, floating-point environment or system setting is changed.
Frequency/thermal/background activity is not fully controlled. This Windows host
cannot stand in for other CPUs, compilers, real-time systems or embedded devices.
Cross-compilation tests elsewhere establish compilation, not target timing.
See [requirements](requirements/requirements.md), [math](math_conventions.md),
and [unit limitations](units.md).

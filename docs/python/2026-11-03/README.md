# Python release-wheel measurements

Host observations only; no timing gate or native-parity claim. See [guide](../../PYTHON-GUIDE.md).

## Method

Installed CPython 3.12.10 x64 on Windows 11 build 26200, Ryzen 7 2700. Explicit
Rust 1.99.0, PyO3 0.29.2, maturin 1.16.0; binding release profile opt-level 3, thin
LTO, one codegen unit, unwind. The wheel was built from the source distribution
and installed in a local venv. Its actual extension hash is recorded in results.json.
High-performance plan was already active; pre-window CPU snapshot 6%, WMI current/
nominal 3200 MHz. Turbo/thermals/background load were not continuously controlled.
Standards work held its local jobs during the explicit timing window.

Run `python -I python/benchmark.py --out target/python-study.json` in that venv.
Each cell/repeat is a fresh process, three repeats with reversed cell order on
repeat 2. There are 102 timed cells x 9 samples = 918 samples, plus 6 fresh-process
memory cells (108 records total). Calibration targets 2 ms, capped at 4096 inner
calls; shortest reported total was 1.169 ms. Raw k/total/ns-per-call, calibration
and cold single calls are retained separately. No sample/spike was trimmed and no
confidence interval is inferred from this small study. Tables give all three
independent process medians in microseconds/call, not a pooled best case.

Preparation is outside clocks. Import snapshots an existing array; apply/conversion
consume existing immutable batches. First export uses a DIFFERENT unviewed batch
per inner call (prepared outside the clock); cached exports share bytes. Replacing
the previous result inside an inner loop includes its deallocation; the final
result is deleted outside the clock. GC collection and first-export input setup
are outside clocks. Python loop/function-call overhead remains, not subtracted.
Cold calls are labeled separately, not mixed into steady samples. Different
allocation/cache/working-set conditions mean isolated stages are NOT additive.
In particular first export keeps several prepared batch inputs alive whereas
end-to-end cycles a small live set, so do not sum those columns as a pipeline estimate.

End-to-end times import -> checked apply -> first export; returned view retains
bytes but the temporary batches can drop. Scalar calls intentionally perform
one checked one-row import/apply/export per point plus byte-view concatenation;
this is Python/FFI granularity context, not Rust native baseline or equal output
allocation strategy. Inputs are repeated finite triples (2,3,4), quarter-turn
rotation plus translation, not representative error/extreme-path timings.
Those paths have correctness tests, not a Python timing characterization here.

## Latency

| Rows | Stage | Repeat medians (microseconds/call) |
| --- | --- | --- |
| 1 | import | 0.553 / 0.567 / 0.569 |
| 1 | apply | 0.381 / 0.384 / 0.375 |
| 1 | convert | 0.378 / 0.371 / 0.371 |
| 1 | export_first | 1.315 / 1.280 / 1.257 |
| 1 | export_cached | 1.054 / 1.066 / 1.057 |
| 1 | end_to_end | 2.405 / 2.395 / 2.403 |
| 1 | scalar_calls | 3.562 / 3.597 / 3.577 |
| 64 | import | 0.751 / 0.728 / 0.731 |
| 64 | apply | 0.770 / 0.760 / 0.770 |
| 64 | convert | 0.677 / 0.683 / 0.674 |
| 64 | export_first | 2.788 / 2.070 / 2.062 |
| 64 | export_cached | 1.040 / 1.060 / 1.047 |
| 64 | end_to_end | 3.052 / 3.063 / 3.082 |
| 64 | scalar_calls | 194.991 / 196.245 / 191.282 |
| 4096 | import | 11.059 / 11.088 / 11.120 |
| 4096 | apply | 25.405 / 25.421 / 24.957 |
| 4096 | convert | 19.159 / 19.096 / 19.098 |
| 4096 | export_first | 96.385 / 100.746 / 102.210 |
| 4096 | export_cached | 1.038 / 1.080 / 1.062 |
| 4096 | end_to_end | 52.579 / 44.355 / 44.226 |
| 4096 | scalar_calls | 11922.500 / 12057.700 / 11891.500 |
| 65536 | import | 713.475 / 751.825 / 661.425 |
| 65536 | apply | 801.533 / 838.867 / 858.233 |
| 65536 | convert | 784.067 / 758.233 / 732.567 |
| 65536 | export_first | 681.400 / 687.075 / 652.300 |
| 65536 | export_cached | 1.057 / 1.184 / 1.066 |
| 65536 | end_to_end | 2418.800 / 2130.300 / 2099.700 |

Zero-row timings and setup timings remain in the raw data. Examples of variation:
N64 first-export process median 2.788 us versus 2.062-2.070 us in later repeats;
N4096 end-to-end 52.579 us versus 44.226-44.355 us. Large allocation/working-set
effects and background noise are not separated causally. These values support
batching/constant Python-object granularity, not universal speedup or real-time bounds.

## Memory and object granularity

A million rows is 24,000,000 payload bytes. Source arrays are allocated before
the memory baseline. Fresh-process peak working set in bytes:

| Batch state | Before | After | Increase |
| --- | --- | --- |
| memory_unviewed repeat 1 | 44859392 | 68927488 | 24068096 |
| memory_viewed repeat 1 | 44814336 | 92864512 | 48050176 |
| memory_viewed repeat 2 | 44806144 | 92856320 | 48050176 |
| memory_unviewed repeat 2 | 44589056 | 68636672 | 24047616 |
| memory_unviewed repeat 3 | 44978176 | 69025792 | 24047616 |
| memory_viewed repeat 3 | 44568576 | 92651520 | 48082944 |

The structural claim is private Vec + cached bytes after viewing (~2 payloads).
RSS observations support it here: import added about 24 MB; retained viewed import
about 48 MB above a baseline already containing the source array. High-water marks
are allocator/OS-dependent floors and not live-allocation instrumentation. Viewing
does not replace/free the Vec. Export uses one payload copy plus zero fill; later
views reuse bytes. Source -> imported batch -> output batch -> output view while
retaining all has about four payloads, not zero-copy end-to-end.

tracemalloc sees Python allocations, NOT Rust Vec storage. It saw only 72 retained
traced bytes for the unviewed memory case and about 24,000,513 for viewed cases.
That difference is evidence of the cached Python bytes, not absence of Rust memory.
Retained traced block count for apply/import/conversion was 7 at both N64 and
N65536 in repeat 1; first export/end-to-end was 11 at both sizes. Instrumentation
itself contributes blocks. This sampled constant granularity plus source review
supports no per-row Python result construction; it is not a universal allocation proof.

## Evidence and limits

`results.json` includes every final sample/cold call/calibration, extension hash,
platform and timer info. Source fingerprints use LF-normalized bytes; repository
line endings were normalized after measurement without changing values/code tokens. `pilot.json` retains the earlier pass whose initial
in-sample calibration groups were too short; it is not used in these tables.
An earlier smoke failure in scalar context used array.frombytes on a double view;
the harness now casts it to byte format, without payload copying. The aborted run
produced no complete table. `metadata.json`, environment/power files and the exact
benchmark source accompany these results. Historical 600 + 423 Criterion records
remain untouched and are not directly comparable to this FFI study.

No default/no_std speed comparison is made: the binding always uses std.
No NumPy import/compute time, free-threaded interpreter, native concurrent-writer
snapshot, other CPU/OS performance, wheel publication, or prepared API advantage
is established. The safe core operations are called for every row without validation
amortization promotion or altered arithmetic. End-to-end costs should guide callers
to import once and batch calls; use shared immutable buffers/views when practical.

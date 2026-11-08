"""Bounded release-wheel latency and high-water RSS study; no timing gate.

Run from the repository root with the interpreter containing the installed wheel:
python python/benchmark.py --out target/python-study.json
Each cell/repeat is a fresh process. Preparation is outside each timed call;
raw nanosecond samples and memory observations are retained, not trimmed.
"""
import argparse
import array
import ctypes
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc


def peak_rss():
    if sys.platform == "win32":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource
    amount = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return amount if sys.platform == "darwin" else amount * 1024


def memory_worker(stage, size, raw, source, points_type, unit):
    gc.collect()
    before = peak_rss()
    tracemalloc.start()
    result = points_type.from_buffer(raw, source, unit)
    view = result.view() if stage == "memory_viewed" else None
    current, peak = tracemalloc.get_traced_memory()
    after = peak_rss()
    tracemalloc.stop()
    return {"stage": stage, "rows": size, "peak_rss_before_bytes": before,
            "peak_rss_after_bytes": after, "python_traced_current_bytes": current,
            "python_traced_peak_bytes": peak, "payload_bytes": size*3*8,
            "viewed": view is not None}


def sample_calls(stage, raw, source, actions, cold_ns):
    from spatial_typestate import Points, METERS
    iterations = min(4096, max(1, math.ceil(2_000_000 / max(1, cold_ns))))
    calibration = []
    for _ in range(8):
        functions = ([Points.from_buffer(raw, source, METERS).view for _ in range(iterations)]
                     if stage == "export_first" else [actions[stage]] * iterations)
        started = time.perf_counter_ns()
        for fn in functions:
            result = fn()
        total = time.perf_counter_ns() - started
        calibration.append({"iterations": iterations, "total_ns": total})
        del result, functions
        if total >= 2_000_000 or iterations == 4096:
            break
        iterations = min(4096, max(iterations + 1, math.ceil(iterations * 2_000_000 / max(1, total))))
    samples, iteration_counts, totals = [], [], []
    for _ in range(9):
        # Independent first exports: calibration never warms a sample's cache.
        functions = ([Points.from_buffer(raw, source, METERS).view for _ in range(iterations)]
                     if stage == "export_first" else [actions[stage]] * iterations)
        gc.collect()
        started = time.perf_counter_ns()
        for fn in functions:
            result = fn()
        total = time.perf_counter_ns() - started
        samples.append(total / iterations)
        totals.append(total)
        iteration_counts.append(iterations)
        del result, functions
        # Bound memory/time while moving short samples toward >=1 ms.
        if total < 1_000_000:
            iterations = min(4096, iterations * 2)
    return samples, iteration_counts, totals, calibration


def retained_memory(fn):
    before = peak_rss()
    tracemalloc.start()
    snapshot = tracemalloc.take_snapshot()
    result = fn()
    difference = tracemalloc.take_snapshot().compare_to(snapshot, "traceback")
    retained_python_blocks = sum(item.count_diff for item in difference)
    python_current, python_peak = tracemalloc.get_traced_memory()
    after = peak_rss()
    tracemalloc.stop()
    # Release only after both tracemalloc and RSS observed the retained result.
    del result
    return {"peak_rss_before_bytes": before, "peak_rss_after_bytes": after,
            "retained_python_blocks": retained_python_blocks,
            "python_traced_current_bytes": python_current, "python_traced_peak_bytes": python_peak}


def worker(stage, size):
    from spatial_typestate import Frame, METERS, FEET, Points, Quaternion, Transform
    source, target = Frame("Sensor"), Frame("World")
    q = Quaternion(target, 0., 0., 1., 1.)
    transform = Transform.from_rotation_translation(source, target, METERS, q, (10., 20., 30.))
    # array repetition fills one contiguous payload; no retained Python float per row.
    raw = array.array("d", [2., 3., 4.]) * size
    if stage.startswith("memory_"):
        return memory_worker(stage, size, raw, source, Points, METERS)
    points = Points.from_buffer(raw, source, METERS)
    def scalar_calls():
        # Same checked FFI operation per row: intentionally many small batches.
        out = array.array("d")
        for _ in range(size):
            one = Points.from_buffer(array.array("d", [2., 3., 4.]), source, METERS)
            out.frombytes(transform.apply_points(one).view().cast("B"))
        return out
    def end_to_end():
        return transform.apply_points(Points.from_buffer(raw, source, METERS)).view()
    def setup():
        frame = Frame("Target")
        return Transform.from_rotation_translation(source, frame, METERS,
                    Quaternion(frame, 0., 0., 1., 1.), (10., 20., 30.))
    actions = {
        "import": lambda: Points.from_buffer(raw, source, METERS),
        "apply": lambda: transform.apply_points(points),
        "convert": lambda: points.convert_to(FEET),
        "export_cached": points.view,
        "end_to_end": end_to_end,
        "scalar_calls": scalar_calls,
        "setup": setup,
    }
    if stage == "export_cached":
        points.view()
    cold_fn = Points.from_buffer(raw, source, METERS).view if stage == "export_first" else actions[stage]
    started = time.perf_counter_ns()
    cold_result = cold_fn()
    cold_ns = time.perf_counter_ns() - started
    del cold_result, cold_fn
    samples, iteration_counts, totals, calibration = sample_calls(
        stage, raw, source, actions, cold_ns)
    # Fresh retained result, with before/after process high-water marks. RSS deltas
    # are floors obscured by allocator reuse; report absolute values as well.
    fn = Points.from_buffer(raw, source, METERS).view if stage == "export_first" else actions[stage]
    memory = retained_memory(fn)
    # Rust Vec allocations are NOT traced by tracemalloc. A batch keeps its Vec
    # and, after first view, its cached bytes until the batch is dropped.
    return {"stage": stage, "rows": size, "samples_ns": samples,
            "iterations_per_sample": iteration_counts, "sample_totals_ns": totals,
            "cold_single_call_ns": cold_ns, "calibration": calibration, "median_ns": statistics.median(samples), "min_ns": min(samples), "max_ns": max(samples),
            **memory}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", nargs=2)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker[0], int(args.worker[1]))))
        return
    if args.out is None:
        parser.error("--out is required")
    stages = ["import", "apply", "convert", "export_first", "export_cached", "end_to_end"]
    cells = [(stage, n) for n in [0, 1, 64, 4096, 65536] for stage in stages]
    cells += [("scalar_calls", n) for n in [1, 64, 4096]] + [("setup", 0)]
    cells += [(stage, 1_000_000) for stage in ["memory_unviewed", "memory_viewed"]]
    results = []
    for repeat in range(3):
        order = cells if repeat % 2 == 0 else list(reversed(cells))
        for stage, n in order:
            result = json.loads(subprocess.check_output(
                [sys.executable, "-I", __file__, "--worker", stage, str(n)], text=True))
            result["repeat"] = repeat + 1
            results.append(result)
    import spatial_typestate._native as native
    output = {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
              "wheel_extension_sha256": hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
              "timer": time.get_clock_info("perf_counter")._asdict() if hasattr(time.get_clock_info("perf_counter"), "_asdict") else str(time.get_clock_info("perf_counter")),
              "pid": os.getpid(), "results": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(results)} cells; all samples retained: {args.out}")


if __name__ == "__main__":
    main()

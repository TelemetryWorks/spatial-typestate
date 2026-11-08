"""Equivalence checks for artifact parsing and retained-memory observations."""
import importlib.util
import itertools
from email.parser import Parser
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import verify_artifacts as artifacts
import check_package_metadata as metadata

spec = importlib.util.spec_from_file_location("benchmark", PROJECT / "benchmark.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class NeededParserTests(unittest.TestCase):
    def compare_legacy(self, text):
        # The legacy expression is an oracle only on bounded test/tool output.
        self.assertLess(len(text), 100_000)
        legacy = re.findall(r"\(NEEDED\).*\[(.*?)\]", text)
        actual = artifacts.needed_libraries(text)
        self.assertEqual(actual, legacy)
        self.assertEqual(sorted(set(actual)), sorted(set(legacy)))

    def test_brackets_duplicates_and_non_newline_whitespace(self):
        for tokens in itertools.product(("", "[", "]", "x", "(NEEDED)", "\r"), repeat=5):
            self.compare_legacy("".join(tokens))
        self.compare_legacy("(NEEDED) [libc.so.6]\n(NEEDED) [libc.so.6]\n")
        self.compare_legacy("(NEEDED) [" + "x" * 20_000)

    def test_captured_dynamic_section(self):
        # Real readelf -d stdout: run 42442219792, Ubuntu CPython 3.11 control job.
        dynamic = (Path(__file__).parent / "fixtures/readelf-python311.txt").read_text(encoding="utf-8")
        self.compare_legacy(dynamic)
        self.assertEqual(artifacts.needed_libraries(dynamic), ["libpython3.11.so.1.0", "libc.so.6"])

    @unittest.skipUnless(sys.platform == "linux", "real readelf output checked on Linux CI")
    def test_real_interpreter_dynamic_section(self):
        dynamic = subprocess.check_output(["readelf", "-d", sys.executable], text=True)
        self.assertIn("(NEEDED)", dynamic)
        self.compare_legacy(dynamic)
        # Retain the real tool output in the existing control-test log.
        print("READELF_DYNAMIC_FIXTURE_BEGIN\n" + dynamic + "READELF_DYNAMIC_FIXTURE_END")


class RetainedMemoryTests(unittest.TestCase):
    def test_result_survives_every_snapshot_and_rss_observation(self):
        events = []

        class Result:
            def __del__(self):
                events.append("release")

        class Snapshot:
            def compare_to(self, previous, key):
                events.append("compare")
                return []

        def observe(name, value):
            self.assertNotIn("release", events)
            events.append(name)
            return value

        def create():
            events.append("result")
            return Result()

        with (patch.object(benchmark, "peak_rss", side_effect=lambda: observe("rss", 10)),
              patch.object(benchmark.tracemalloc, "start", side_effect=lambda: observe("start", None)),
              patch.object(benchmark.tracemalloc, "take_snapshot", side_effect=lambda: observe("snapshot", Snapshot())),
              patch.object(benchmark.tracemalloc, "get_traced_memory", side_effect=lambda: observe("traced", (20, 30))),
              patch.object(benchmark.tracemalloc, "stop", side_effect=lambda: observe("stop", None))):
            measurements = benchmark.retained_memory(create)
        self.assertEqual(events, ["rss", "start", "snapshot", "result", "snapshot", "compare",
                                  "traced", "rss", "stop", "release"])
        self.assertEqual(measurements, {"peak_rss_before_bytes": 10, "peak_rss_after_bytes": 10,
                                      "retained_python_blocks": 0, "python_traced_current_bytes": 20,
                                      "python_traced_peak_bytes": 30})

    def test_viewed_and_unviewed_payloads_are_observed_before_release(self):
        for stage in ("memory_viewed", "memory_unviewed"):
            events = []

            class Batch:
                def view(self):
                    events.append("view")
                    return self

                def __del__(self):
                    events.append("release")

            class Points:
                @staticmethod
                def from_buffer(raw, frame, unit):
                    events.append("import")
                    return Batch()

            with (patch.object(benchmark, "peak_rss", side_effect=[10, 20]),
                  patch.object(benchmark.tracemalloc, "start"),
                  patch.object(benchmark.tracemalloc, "get_traced_memory", return_value=(30, 40)),
                  patch.object(benchmark.tracemalloc, "stop",
                               side_effect=lambda: events.append("stop"))):
                result = benchmark.memory_worker(stage, 2, None, None, Points, None)
            self.assertEqual(events, ["import", "view", "stop", "release"] if stage == "memory_viewed"
                             else ["import", "stop", "release"])
            self.assertEqual(result["viewed"], stage == "memory_viewed")
            self.assertEqual(result["payload_bytes"], 48)
            self.assertEqual(result["python_traced_peak_bytes"], 40)


class SamplingTests(unittest.TestCase):
    def test_short_samples_increase_repetitions_with_exact_clock_normalization(self):
        durations = [500_000, 2_000_000, 500_000] + [1_000_000] * 8
        timestamps = list(itertools.chain.from_iterable((0, total) for total in durations))
        binding = ModuleType("spatial_typestate")
        binding.Points = unittest.mock.Mock()
        binding.METERS = object()
        with (patch.dict(sys.modules, {"spatial_typestate": binding}),
              patch.object(benchmark.time, "perf_counter_ns", side_effect=timestamps) as clock,
              patch.object(benchmark.gc, "collect") as collect):
            action = unittest.mock.Mock(return_value=None)
            samples, counts, totals, calibration = benchmark.sample_calls(
                "apply", None, None, {"apply": action}, 2_000_000)
        self.assertEqual(calibration, [{"iterations": 1, "total_ns": 500_000},
                                       {"iterations": 4, "total_ns": 2_000_000}])
        self.assertEqual(counts, [4] + [8] * 8)
        self.assertEqual(totals, durations[2:])
        self.assertEqual(samples, [125_000] * 9)
        self.assertEqual(action.call_count, 73)
        self.assertEqual(clock.call_count, 22)
        self.assertEqual(collect.call_count, 9)

    def test_first_exports_are_fresh_and_never_warmed_by_calibration(self):
        batches = []
        exports = []

        class Batch:
            def view(self):
                exports.append(self)
                return None

        def import_batch(*args):
            result = Batch()
            batches.append(result)
            return result

        binding = ModuleType("spatial_typestate")
        binding.Points = unittest.mock.Mock(from_buffer=import_batch)
        binding.METERS = object()
        with (patch.dict(sys.modules, {"spatial_typestate": binding}),
              patch.object(benchmark.time, "perf_counter_ns", side_effect=[0, 1000] + [0, 2_000_000] * 9),
              patch.object(benchmark.gc, "collect")):
            samples, counts, totals, calibration = benchmark.sample_calls(
                "export_first", None, None, {}, 1)
        self.assertEqual(calibration, [{"iterations": 4096, "total_ns": 1000}])
        self.assertEqual(counts, [4096] * 9)
        self.assertEqual(len(batches), 40960)
        self.assertEqual(exports, batches)
        self.assertEqual(len({id(batch) for batch in exports}), len(exports))
        self.assertEqual(totals, [2_000_000] * 9)
        self.assertEqual(samples, [2_000_000 / 4096] * 9)


def worker_binding():
    """Record FFI routing, not numeric math; installed-wheel tests cover the math."""
    observed = SimpleNamespace(views=[], conversions=[], events=[])

    class Batch:
        def __init__(self, raw):
            self.raw = raw

        def view(self):
            observed.views.append(self)
            observed.events.append("view")
            return memoryview(self.raw)

        def convert_to(self, unit):
            observed.conversions.append(unit)
            return self

    binding = ModuleType("spatial_typestate")
    binding.Frame = unittest.mock.Mock(side_effect=lambda name: name)
    binding.METERS, binding.FEET = object(), object()
    binding.Quaternion = unittest.mock.Mock(return_value="rotation")
    binding.Points = unittest.mock.Mock()
    binding.Points.from_buffer.side_effect = lambda raw, frame, unit: Batch(raw)
    observed.transform = unittest.mock.Mock()
    observed.transform.apply_points.side_effect = lambda points: points
    binding.Transform = unittest.mock.Mock()
    binding.Transform.from_rotation_translation.return_value = observed.transform
    return binding, observed


class WorkerRoutingTests(unittest.TestCase):
    def test_stage_routing_cold_calls_and_serialized_observations(self):
        # imports, maps, views, conversions, transform constructions, respectively.
        counts = {"import": (3, 0, 0, 0, 1), "apply": (1, 2, 0, 0, 1),
                  "convert": (1, 0, 0, 2, 1), "export_cached": (1, 0, 3, 0, 1),
                  "export_first": (3, 0, 2, 0, 1), "end_to_end": (3, 2, 2, 0, 1),
                  "scalar_calls": (5, 4, 4, 0, 1), "setup": (1, 0, 0, 0, 3)}
        for stage, expected in counts.items():
            with self.subTest(stage=stage):
                self.check_stage(stage, expected)

    def check_stage(self, stage, expected):
        binding, observed = worker_binding()
        memory = {"peak_rss_before_bytes": 1, "peak_rss_after_bytes": 2,
                  "retained_python_blocks": 3, "python_traced_current_bytes": 4,
                  "python_traced_peak_bytes": 5}

        def retained(fn):
            fn()
            return memory

        ticks = iter((100, 250))
        def clock_read():
            observed.events.append("clock")
            return next(ticks)

        with (patch.dict(sys.modules, {"spatial_typestate": binding}),
              patch.object(benchmark.time, "perf_counter_ns", side_effect=clock_read) as clock,
              patch.object(benchmark, "sample_calls", return_value=([20, 10], [1, 1], [20, 10], [])) as sample,
              patch.object(benchmark, "retained_memory", side_effect=retained)):
            result = benchmark.worker(stage, 2)
        self.assertEqual(result, {"stage": stage, "rows": 2, "samples_ns": [20, 10],
                                  "iterations_per_sample": [1, 1], "sample_totals_ns": [20, 10],
                                  "cold_single_call_ns": 150, "calibration": [],
                                  "median_ns": 15, "min_ns": 10, "max_ns": 20, **memory})
        self.assertEqual(clock.call_count, 2)
        self.assertEqual(sample.call_count, 1)
        self.assertEqual((binding.Points.from_buffer.call_count, observed.transform.apply_points.call_count,
                          len(observed.views), len(observed.conversions),
                          binding.Transform.from_rotation_translation.call_count), expected)
        for call in binding.Points.from_buffer.call_args_list:
            self.assertEqual(call.args[1:], ("Sensor", binding.METERS))
            self.assertEqual(list(call.args[0]), [2., 3., 4.] * (len(call.args[0]) // 3))
        self.assertTrue(all(unit is binding.FEET for unit in observed.conversions))
        initial = binding.Transform.from_rotation_translation.call_args_list[0]
        self.assertEqual(initial.args, ("Sensor", "World", binding.METERS, "rotation", (10., 20., 30.)))
        if stage == "export_cached":
            self.assertEqual(len({id(batch) for batch in observed.views}), 1)
            self.assertEqual(observed.events, ["view", "clock", "view", "clock", "view"])
        if stage == "export_first":
            self.assertEqual(len({id(batch) for batch in observed.views}), 2)

    def test_memory_stage_delegates_without_cold_or_timed_calls(self):
        binding, _ = worker_binding()
        for stage in ("memory_viewed", "memory_unviewed"):
            with (patch.dict(sys.modules, {"spatial_typestate": binding}),
                  patch.object(benchmark, "memory_worker", return_value={"fixture": stage}) as memory,
                  patch.object(benchmark.time, "perf_counter_ns") as clock,
                  patch.object(benchmark, "sample_calls") as samples):
                result = benchmark.worker(stage, 2)
            self.assertEqual(result, {"fixture": stage})
            args = memory.call_args.args
            self.assertEqual(args[:2], (stage, 2))
            self.assertEqual(list(args[2]), [2., 3., 4., 2., 3., 4.])
            self.assertEqual(args[3:], ("Sensor", binding.Points, binding.METERS))
            clock.assert_not_called()
            samples.assert_not_called()


class StaticMetadataTests(unittest.TestCase):
    @staticmethod
    def message(headers):
        return Parser().parsestr(headers + "\n\nfixture README\n")

    def test_only_declared_dynamic_headers_may_differ(self):
        source = self.message("Name: fixture\nDynamic: Classifier\nClassifier: source\nLicense-File: a\nLicense-File: b")
        built = self.message("Name: fixture\nClassifier: wheel\nLicense-File: b\nLicense-File: a")
        self.assertIsNone(metadata.compare_static_metadata(source, built))
        built.replace_header("Name", "other")
        with self.assertRaisesRegex(ValueError, "metadata mismatch: Name"):
            metadata.compare_static_metadata(source, built)

    def test_missing_static_header_and_readme_changes_are_rejected(self):
        source = self.message("Name: fixture\nLicense-File: a")
        built = self.message("Name: fixture")
        with self.assertRaisesRegex(ValueError, "metadata mismatch: License-File"):
            metadata.compare_static_metadata(source, built)
        built["License-File"] = "a"
        built.set_payload("changed README\n")
        with self.assertRaisesRegex(ValueError, "README mismatch"):
            metadata.compare_static_metadata(source, built)


if __name__ == "__main__":
    unittest.main()

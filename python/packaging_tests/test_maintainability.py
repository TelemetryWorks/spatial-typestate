"""Equivalence checks for artifact parsing and retained-memory observations."""
import importlib.util
import itertools
from email.parser import Parser
from pathlib import Path
import re
import subprocess
import sys
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
        with (patch.object(benchmark.time, "perf_counter_ns", side_effect=timestamps) as clock,
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
        import spatial_typestate
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

        points_type = unittest.mock.Mock(from_buffer=import_batch)
        with (patch.object(spatial_typestate, "Points", points_type),
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

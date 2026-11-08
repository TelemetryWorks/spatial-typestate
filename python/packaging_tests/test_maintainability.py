"""Equivalence checks for artifact parsing and retained-memory observations."""
import importlib.util
import itertools
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import verify_artifacts as artifacts

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

    def test_representative_dynamic_section(self):
        self.compare_legacy(
            "Dynamic section at offset 0x2dc8 contains 4 entries:\n"
            "  Tag                Type                 Name/Value\n"
            " 0x0000000000000001 (NEEDED)             Shared library: [libc.so.6]\n"
            " 0x0000000000000001 (NEEDED)             Shared library: [libgcc_s.so.1]\n"
            " 0x0000000000000000 (NULL)               0x0\n")

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


if __name__ == "__main__":
    unittest.main()

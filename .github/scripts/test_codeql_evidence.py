import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from codeql_evidence import inventory


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "db"
        self.results = self.root / "results"
        self.db.mkdir()
        self.results.mkdir()
        self.paths = ["src/transform.rs", "src/quaternion.rs",
                      "python/native/src/lib.rs", "python/native/src/kernels.rs"]
        self.write_archive()
        self.write_sarif([{"id": "example/rule"}])

    def write_archive(self):
        with zipfile.ZipFile(self.db / "src.zip", "w") as archive:
            for path in self.paths:
                archive.writestr("home/runner/work/project/" + path, "source")

    def write_sarif(self, rules):
        (self.results / "rust.sarif").write_text(json.dumps({"runs": [{
            "tool": {"driver": {"name": "CodeQL", "rules": rules}},
            "results": [{"ruleId": "example/rule"}]}]}), encoding="utf-8")

    def test_counts_and_separate_native_source(self):
        report = inventory("rust", self.db, self.results)
        self.assertEqual(report["source_files"], 4)
        self.assertEqual(report["runs"][0]["rules"], 1)
        self.assertEqual(report["runs"][0]["results"], 1)

    def test_missing_native_source_fails(self):
        self.paths = self.paths[:2]
        self.write_archive()
        with self.assertRaisesRegex(ValueError, "intended source missing"):
            inventory("rust", self.db, self.results)

    def test_grouped_rules_and_diagnostics_are_retained(self):
        path = self.results / "rust.sarif"
        sarif = json.loads(path.read_text(encoding="utf-8"))
        run = sarif["runs"][0]
        run["tool"]["driver"]["rules"] = []
        run["tool"]["extensions"] = [{"name": "rust/queries", "rules": [{"id": "rule"}]}]
        notice = {"level": "error", "message": {"text": "unresolved manifest"}}
        run["invocations"] = [{"executionSuccessful": False,
                               "toolExecutionNotifications": [notice]}]
        run["artifacts"] = [{"location": {"uri": "src/transform.rs"}, "properties": {"linesOfCode": 5}}]
        path.write_text(json.dumps(sarif), encoding="utf-8")
        report = inventory("rust", self.db, self.results)["runs"][0]
        self.assertEqual(report["rules"], 1)
        self.assertEqual(report["diagnostic_errors"], 1)
        self.assertEqual(report["diagnostics"], [notice])
        self.assertEqual(report["execution_successful"], [False])
        self.assertEqual(report["artifacts"], run["artifacts"])

    def test_absent_or_multiple_archives_fail(self):
        (self.db / "src.zip").unlink()
        with self.assertRaisesRegex(ValueError, "expected one source archive"):
            inventory("rust", self.db, self.results)
        self.write_archive()
        (self.db / "another").mkdir()
        (self.db / "another" / "src.zip").write_bytes((self.db / "src.zip").read_bytes())
        with self.assertRaisesRegex(ValueError, "expected one source archive"):
            inventory("rust", self.db, self.results)

    def test_missing_sarif_or_empty_rules_fail(self):
        self.write_sarif([])
        with self.assertRaisesRegex(ValueError, "no query rules"):
            inventory("rust", self.db, self.results)
        (self.results / "rust.sarif").unlink()
        with self.assertRaisesRegex(ValueError, "no SARIF"):
            inventory("rust", self.db, self.results)

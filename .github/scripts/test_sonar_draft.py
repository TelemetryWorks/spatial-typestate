"""Offline contracts only: these fixtures cannot prove analyzer compatibility."""

import copy
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

from sonar_evidence import collect, pages, task_properties
from sonar_reports import clippy_outcome, normalize_clippy, normalize_lcov, normalize_python, generate


WORKFLOW = Path(__file__).resolve().parents[1] / "workflows/sonar-analysis.yml"


def inline(name):
    text = WORKFLOW.read_text(encoding="utf-8")
    begin = "          # BEGIN " + name + "\n"
    end = "          # END " + name
    code = text.split(begin, 1)[1].split(end, 1)[0]
    namespace = {"__name__": "offline_contract"}
    exec(compile(textwrap.dedent(code), str(WORKFLOW) + ":" + name, "exec"), namespace)
    return namespace


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = inline("SONAR_POLICY")["policy"]
        self.pr = {"number": 12, "pull_request": {
            "user": {"login": "maintainer"},
            "head": {"repo": {"full_name": "owner/project"}, "ref": "fix/branch", "sha": "a" * 40},
            "base": {"ref": "main"}}}

    def call(self, event=None, **overrides):
        args = {"event_name": "pull_request", "event": event or self.pr,
                "repository": "owner/project", "sha": "b" * 40, "ref": "refs/pull/12/merge",
                "project": "owner_project", "organization": "owner", "token_present": "true"}
        return self.policy(**(args | overrides))

    def test_explicit_head_revision_and_pr_args(self):
        result = self.call()
        self.assertEqual(result["revision"], "a" * 40)
        self.assertIn("-Dsonar.pullrequest.key=12", result["scm_args"])
        self.assertIn("-Dsonar.scm.revision=" + "a" * 40, result["scm_args"])
        self.assertNotIn("b" * 40, result["scm_args"])

    def test_fork_and_dependabot_author_are_not_scans(self):
        for author, repo in [("maintainer", "fork/project"), ("dependabot[bot]", "owner/project")]:
            event = copy.deepcopy(self.pr)
            event["pull_request"]["user"]["login"] = author
            event["pull_request"]["head"]["repo"]["full_name"] = repo
            self.assertEqual(self.call(event, token_present="false"), {"eligible": "false"})

    def test_missing_or_redirecting_configuration_fails(self):
        for updates in ({"token_present": "false"}, {"project": ""}, {"organization": "https://evil"},
                        {"project": "p\n-Dsonar.host.url=evil"}, {"organization": "x y"}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                self.call(**updates)

    def test_ref_argument_injection_and_invalid_revision_fail(self):
        for value in ['x -Dsonar.host.url=evil', '"bad"', '-x', 'x/../y', 'x\nnext', 'café']:
            event = copy.deepcopy(self.pr)
            event["pull_request"]["head"]["ref"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.call(event)
        with self.assertRaises(ValueError):
            self.call(event_name="push", ref="refs/heads/main", sha="not-a-sha")

    def test_main_manual_schedule_and_unsupported_events(self):
        for name in ("push", "workflow_dispatch", "schedule"):
            self.assertEqual(self.call(event_name=name, ref="refs/heads/main")["revision"], "b" * 40)
        for name in ("pull_request_target", "workflow_run"):
            with self.assertRaises(ValueError):
                self.call(event_name=name)


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        (self.root / "src").mkdir()
        (self.root / "src/math.rs").write_text("fn example() {}\n")
        (self.root / "python").mkdir()
        (self.root / "python/example.py").write_text("value = 1\n")
        self.directory = Path(self.temp.name) / "reports"
        self.directory.mkdir()
        self.scope = inline("SONAR_ENVELOPE")
        self.validate = self.scope["validate"]
        for name in self.scope["REPORTS"][:3]:
            (self.directory / name).write_text("SF:src/math.rs\nDA:1,3\nend_of_record\n")
        for name in self.scope["REPORTS"][3:6]:
            (self.directory / name).write_text('{"reason":"build-finished","success":true}\n')
        self.xml = '<coverage><sources><source>.</source></sources><packages><package><classes><class filename="python/example.py"><lines><line number="1" hits="2"/></lines></class></classes></package></packages></coverage>'
        (self.directory / "python-coverage.xml").write_text(self.xml)
        self.rehash()

    def rehash(self):
        phases = ('core-std', 'core-no-std', 'native', 'clippy-core-std', 'clippy-core-no-std', 'clippy-native',
                  'wheel-build', 'wheel-install', 'python-packaging', 'python-pipeline', 'python-wheel', 'coverage-combine', 'coverage-xml')
        record = {"schema": 1, "revision": "a" * 40, "generation_exit_codes": dict.fromkeys(phases, 0),
                  "clippy_outcomes": {phase: {"exit_code": 0, "kind": "clean", "errors": 0, "warnings": 0} for phase in phases if phase.startswith("clippy-")},
                  "source_paths": {}, "tools": {}, "limitations": [],
                  "reports": {n: hashlib.sha256((self.directory / n).read_bytes()).hexdigest() for n in self.scope["REPORTS"]}}
        (self.directory / "report-inventory.json").write_text(json.dumps(record))

    def check(self):
        return self.validate(self.directory, self.root, "a" * 40)

    def test_valid_reports_preserve_bytes(self):
        result = self.check()
        self.assertEqual(result["python-coverage.xml"], self.xml.encode())
        self.assertIn(b"DA:1,3", result["core-std.lcov"])

    def test_extra_missing_or_hash_mismatch_fail(self):
        extra = self.directory / "sonar-project.properties"
        extra.write_text("sonar.host.url=evil")
        with self.assertRaises(ValueError):
            self.check()
        extra.unlink()
        (self.directory / "core-std.lcov").write_text("tampered")
        with self.assertRaises(ValueError):
            self.check()

    def test_unsafe_source_and_xml_entities_fail_even_when_rehashed(self):
        path = self.directory / "core-std.lcov"
        original = path.read_text()
        for value in ("/etc/passwd", "../outside.rs", "https://evil/source.rs"):
            path.write_text("SF:" + value + "\nend_of_record\n")
            self.rehash()
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check()
        path.write_text(original)
        (self.directory / "python-coverage.xml").write_text('<!DOCTYPE coverage [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + self.xml)
        self.rehash()
        with self.assertRaises(ValueError):
            self.check()

    def test_failed_generation_and_wrong_revision_fail(self):
        record_path = self.directory / "report-inventory.json"
        record = json.loads(record_path.read_text())
        record["generation_exit_codes"]["core-std"] = 1
        record_path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "transport failed"):
            self.check()
        self.rehash()
        with self.assertRaisesRegex(ValueError, "identity"):
            self.validate(self.directory, self.root, "b" * 40)

    def test_directory_and_oversize_reports_fail(self):
        path = self.directory / "core-std.lcov"
        path.unlink()
        path.mkdir()
        with self.assertRaises(ValueError):
            self.check()
        path.rmdir()
        with path.open("wb") as file:
            file.truncate(64 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(ValueError, "bounded regular"):
            self.check()

    def test_lcov_normalization_preserves_counters(self):
        path = self.directory / "core-std.lcov"
        path.write_text("SF:" + str(self.root / "src/math.rs") + "\nDA:1,3\nBRDA:1,0,0,2\nend_of_record\n")
        normalize_lcov(path, self.root)
        self.assertEqual(path.read_text(), "SF:src/math.rs\nDA:1,3\nBRDA:1,0,0,2\nend_of_record\n")

    def test_python_mapping_preserves_hits_and_rejects_entities(self):
        path = self.directory / "python-coverage.xml"
        path.write_text(self.xml.replace("python/example.py", "example.py"))
        self.assertEqual(normalize_python(path, self.root), ["python/example.py"])
        self.assertIn('hits="2"', path.read_text())
        path.write_text("<!DOCTYPE coverage>" + self.xml)
        with self.assertRaises(ValueError):
            normalize_python(path, self.root)

    def test_python_coverage_script_roots_and_ambiguity(self):
        for directory in ('scripts', '.github/scripts'):
            (self.root / directory).mkdir(parents=True)
        (self.root / 'scripts/study.py').write_text('value = 1\n')
        (self.root / '.github/scripts/pipeline.py').write_text('value = 1\n')
        path = self.directory / 'python-coverage.xml'
        path.write_text('<coverage><sources><source>.github/scripts</source><source>scripts</source></sources><packages><package><classes>'
                        '<class filename="study.py"><lines><line number="1" hits="3"/></lines></class>'
                        '<class filename="pipeline.py"><lines><line number="1" hits="2"/></lines></class>'
                        '</classes></package></packages></coverage>')
        self.assertEqual(normalize_python(path, self.root), ['.github/scripts/pipeline.py', 'scripts/study.py'])
        self.assertIn('hits="3"', path.read_text())
        (self.root / 'python/pipeline.py').write_text('duplicate = 1\n')
        path.write_text(self.xml.replace('python/example.py', 'pipeline.py'))
        with self.assertRaisesRegex(ValueError, 'ambiguous/unmapped'):
            normalize_python(path, self.root)

    def test_clippy_keeps_all_diagnostics_without_severity_filter(self):
        path = self.directory / "clippy-core-std.jsonl"
        rows = [{"reason": "compiler-message", "message": {"level": level,
                  "spans": [{"file_name": "src/math.rs"}], "children": []}}
                for level in ("warning", "error")]
        rows.append({"reason": "build-finished", "success": False})
        path.write_text("\n".join(map(json.dumps, rows)))
        normalize_clippy(path, self.root, self.root)
        self.assertEqual([json.loads(x)["message"]["level"] for x in path.read_text().splitlines()[:-1]], ["warning", "error"])

    def test_clippy_lint_exit_imports_but_compiler_failure_does_not(self):
        path = self.directory / "clippy-core-std.jsonl"
        for code, expected in [("clippy::example", "lint-findings"), ("E0382", "tool-error")]:
            rows = [{"reason": "compiler-message", "message": {"level": "error", "code": {"code": code},
                    "spans": [{"file_name": "src/math.rs"}], "children": []}},
                    {"reason": "build-finished", "success": False}]
            path.write_text("\n".join(map(json.dumps, rows)))
            outcome = clippy_outcome(path, 101)
            self.assertEqual(outcome["kind"], expected)
            self.assertEqual(outcome["exit_code"], 101)
            self.rehash()
            record_path = self.directory / "report-inventory.json"
            record = json.loads(record_path.read_text())
            record["generation_exit_codes"]["clippy-core-std"] = 101
            record["clippy_outcomes"]["clippy-core-std"] = outcome
            record_path.write_text(json.dumps(record))
            if expected == "lint-findings":
                self.assertIn("clippy-core-std.jsonl", self.check())
            else:
                with self.assertRaisesRegex(ValueError, "tool/compile failure"):
                    self.check()

    def test_warning_is_a_finding_without_failed_exit(self):
        path = self.directory / "clippy-core-std.jsonl"
        path.write_text(json.dumps({"reason": "compiler-message", "message": {"level": "warning", "code": {"code": "clippy::example"}, "spans": []}})
                        + '\n{"reason":"build-finished","success":true}\n')
        self.assertEqual(clippy_outcome(path, 0), {"exit_code": 0, "kind": "lint-findings", "warnings": 1, "errors": 0})

    def test_generation_records_failures_without_running_real_builds(self):
        output = Path(self.temp.name) / "failed-generation"
        with mock.patch("sonar_reports.subprocess.run", return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(RuntimeError, "report generation failed"):
                generate(self.root, output, "a" * 40)
        statuses = json.loads((output.parent / "generation-status.json").read_text())
        self.assertEqual(statuses["clippy-core-std"], 1)
        self.assertEqual(statuses["wheel-install"], 1)
        self.assertNotIn("report-inventory.json", [p.name for p in output.iterdir()])


class GuardAndWorkflowTests(unittest.TestCase):
    def test_github_env_keys_have_no_case_insensitive_duplicates(self):
        import re
        indent, keys = None, set()
        for line in WORKFLOW.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            width = len(line) - len(line.lstrip())
            if indent is not None and width <= indent:
                indent, keys = None, set()
            if line.strip() == 'env:':
                indent, keys = width, set()
            elif indent is not None and width == indent + 2:
                match = re.match(r'\s*([A-Za-z_][A-Za-z0-9_-]*):', line)
                self.assertIsNotNone(match)
                key = match[1].casefold()
                self.assertNotIn(key, keys, 'GitHub rejects case-insensitive env duplicates')
                keys.add(key)

    def test_removal_plan_is_hosted_only_and_literal_without_deleting(self):
        namespace = inline("SONAR_HOSTED_REMOVAL")
        environment = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "RUNNER_OS": "Linux",
                       "GITHUB_WORKSPACE": "/home/runner/work/project/project", "RUNNER_TEMP": "/home/runner/work/_temp"}
        with mock.patch("shutil.rmtree") as remove:
            homes, files = namespace["removal_plan"](environment, "Linux")
            self.assertEqual(homes, ["/home/runner/.cargo", "/home/runner/.rustup", "/etc/skel/.cargo", "/etc/skel/.rustup", "/home/packer/.cargo", "/home/packer/.rustup"])
            self.assertNotIn('/home/packer', homes)
            self.assertEqual(len(files), 6)
            remove.assert_not_called()
        for updates, system in [({"RUNNER_ENVIRONMENT": "self-hosted"}, "Linux"), ({}, "Windows"),
                                ({"RUNNER_TEMP": "/tmp"}, "Linux"), ({"GITHUB_WORKSPACE": "/home/runner/work/../private"}, "Linux")]:
            with self.subTest(updates=updates), self.assertRaises(RuntimeError):
                namespace["removal_plan"](environment | updates, system)

    def test_source_test_classification_has_no_overlap(self):
        import re
        text = WORKFLOW.read_text()
        tests = re.search(r'-Dsonar.test.inclusions=(\S+)', text)[1].split(',')
        exclusions = re.search(r'-Dsonar.exclusions=(\S+)', text)[1].split(',')
        self.assertTrue(set(tests).issubset(exclusions))
        for path in ('tests/test.rs', 'python/tests/test_api.py', 'python/packaging_tests/test_backend.py', '.github/scripts/test_sonar_draft.py'):
            self.assertTrue(any(fnmatch.fnmatchcase(path, pattern) for pattern in tests))
            self.assertTrue(any(fnmatch.fnmatchcase(path, pattern) for pattern in exclusions))
        self.assertFalse(any(fnmatch.fnmatchcase('src/transform.rs', pattern) for pattern in exclusions))

    def test_frontdoor_guard_records_and_never_invokes_planted_wrapper(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "checkout"
            (source / ".cargo").mkdir(parents=True)
            marker = root / "wrapper-executed"
            wrapper = root / "wrapper.py"
            wrapper.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('ran')")
            (source / ".cargo/config.toml").write_text('[build]\nrustc-wrapper="' + wrapper.as_posix() + '"\n')
            attempts = root / "attempts.txt"
            guard = root / "guard"
            inline("SONAR_GUARD")["guard_files"](guard, attempts)
            result = subprocess.run([sys.executable, str(guard / "cargo"), "metadata"], cwd=source, check=False)
            self.assertEqual(result.returncode, 126)
            self.assertEqual(attempts.read_text(), "cargo\n")
            self.assertFalse(marker.exists())
            # This does not prove PATH resolution, absolute-path denial or analyzer behavior.

    def test_secret_and_execution_gate_invariants(self):
        text = WORKFLOW.read_text()
        self.assertEqual(text.count("SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}"), 1)
        self.assertIn("TOKEN_PRESENT: ${{ secrets.SONAR_TOKEN != '' }}", text)
        self.assertNotIn("${{ github.head_ref }}", text)
        self.assertNotIn("pull_request_target:", text)
        self.assertNotIn("workflow_run:", text)
        self.assertNotIn("GITHUB_ENV", text)
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("scannerBinariesUrl:", text)
        self.assertIn("skipSignatureVerification: false", text)
        self.assertNotIn("LOCAL DRAFT: absolute-tool/isolation boundary unapproved", text)
        self.assertIn("Denied tool attempts remain failures", text)
        self.assertLess(text.index('Remove Rust tools (DISPOSABLE'), text.index('Token-free precedence and authentication probe'))
        self.assertLess(text.index('Token-free precedence and authentication probe'), text.index('Official credential-bearing scanner'))
        self.assertLess(text.index('planted.unlink()'), text.index('Official credential-bearing scanner'))
        self.assertIn('RUNNER_DEBUG: \'0\'', text)

    def test_probe_requires_auth_failure_precedence_and_zero_counters(self):
        policy = inline('SONAR_PROBE')['probe_result']
        log = 'INFO Project root configuration file: /tmp/settings\nERROR https://api.sonarcloud.io failed: HTTP 401\n'
        self.assertTrue(policy(1, log, '/tmp/settings', 0, 0)['expected_authentication_failure'])
        self.assertTrue(policy(1, log + 'ERROR Re-run with full debug logging.\n', '/tmp/settings', 0, 0)['expected_authentication_failure'])
        actual = ('23:12:00.123 INFO  Project root configuration file: /tmp/settings\n'
                  '23:12:02.494 INFO  Communicating with SonarQube Cloud\n'
                  '23:12:09.336 ERROR Fail to load the list of plugins installed on the server: '
                  'Not authorized or organization not found\n')
        self.assertTrue(policy(1, actual, '/tmp/settings', 0, 0)['expected_authentication_failure'])
        for invalid in (actual.replace('SonarQube Cloud', 'SonarQube Server'),
                        actual.replace('/tmp/settings', '/untrusted/settings'),
                        actual.replace('INFO  Communicating', 'ERROR Communicating')):
            with self.assertRaises(RuntimeError):
                policy(1, invalid, '/tmp/settings', 0, 0)
        for code, text, before, after in [(0, log, 0, 0), (1, log, 0, 1), (1, log, 1, 1),
                                          (1, log + 'DEBUG internal', 0, 0),
                                          (1, 'ERROR unrelated failure', 0, 0)]:
            with self.subTest(code=code, before=before, after=after), self.assertRaises(RuntimeError):
                policy(code, text, '/tmp/settings', before, after)

    def test_probe_counter_reads_extended_iptables_row(self):
        function = inline('SONAR_PROBE')['counter']
        output = 'Chain SPATIAL_SONAR_PROBE (1 references)\n pkts bytes target prot opt in out source destination\n 0 0 REJECT all -- * * 0.0.0.0/0 192.0.2.1 reject-with icmp-port-unreachable\n'
        with mock.patch('subprocess.check_output', return_value=output):
            self.assertEqual(function(), 0)

    @unittest.skipUnless(os.name == 'posix', 'native hosted POSIX find; no local tool installation')
    def test_filesystem_scan_ignores_nonexecutable_completion_and_stubs(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            guard = root / 'guard'
            guard.mkdir()
            (guard / 'cargo').write_text('guard')
            (root / 'cargo').write_text('nonexecuting completion')
            report = inline('SONAR_HOSTED_REMOVAL')['scan_tools'](root, guard)
            self.assertEqual(report['matches'], [])
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                inline('SONAR_HOSTED_REMOVAL')['scan_tools'](root, guard, timeout=-1)

    @unittest.skipUnless(os.name == 'posix', 'native hosted POSIX find')
    def test_native_scan_finds_executable_symlink_and_prunes_exactly(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            guard = root / 'guard'
            guard.mkdir()
            executable = root / 'cargo'
            executable.write_text('test executable metadata only')
            executable.chmod(0o755)
            (root / 'rustc').symlink_to(executable)
            for directory in ('proc', 'sys', 'dev', 'run', 'guard'):
                (root / directory).mkdir(exist_ok=True)
                (root / directory / 'cargo').symlink_to(executable)
            result = inline('SONAR_HOSTED_REMOVAL')['scan_tools'](root, guard)
            self.assertTrue(result['complete'])
            self.assertEqual(set(result['matches']), {str(root / 'cargo'), str(root / 'rustc')})
            self.assertEqual(result['exit_code'], 0)
            self.assertIn('find', result['versions'])

    @unittest.skipUnless(os.name == 'posix', 'native hosted POSIX find')
    def test_native_scan_error_and_timeout_are_incomplete(self):
        scope = inline('SONAR_HOSTED_REMOVAL')
        original = subprocess.run
        for status, error in [(1, b'Permission denied\n'), (124, b''), (137, b'')]:
            def fake(command, **kwargs):
                if command[0] != '/usr/bin/timeout' or command[1] == '--version':
                    return original(command, **kwargs)
                kwargs['stdout'].write(b'/partial/cargo\0')
                kwargs['stderr'].write(error)
                return subprocess.CompletedProcess(command, status)
            with tempfile.TemporaryDirectory() as name, mock.patch('subprocess.run', side_effect=fake):
                result = scope['scan_tools'](Path(name), Path(name) / 'guard')
                self.assertFalse(result['complete'])
                self.assertEqual(result['exit_code'], status)
                self.assertEqual(result['matches'], ['/partial/cargo'])


class PaginationTests(unittest.TestCase):
    def server(self, gate="OK"):
        def get(endpoint, params):
            if endpoint == "/api/ce/task":
                return {"task": {"status": "SUCCESS", "componentKey": "p", "analysisId": "id"}}
            if endpoint == "/api/qualitygates/project_status":
                return {"projectStatus": {"status": gate}}
            if endpoint == "/api/project_branches/list":
                return {"branches": [{"name": "main", "isMain": True}]}
            if endpoint == "/api/measures/component":
                return {"component": {"measures": [{"metric": "coverage", "value": "60"}]}}
            records = {"/api/measures/component_tree": ("components", []),
                       "/api/project_analyses/search": ("analyses", [{"key": "id", "revision": "a" * 40}]),
                       "/api/issues/search": ("issues", [{"key": "issue-" + params.get("resolved", "")}]),
                       "/api/hotspots/search": ("hotspots", [{"key": "hotspot-" + params.get("status", "")}])}
            field, items = records[endpoint]
            return {"paging": {"total": len(items), "pageIndex": 1}, field: items}
        return get

    def test_complete_main_inventory_keeps_all_states_and_real_gate(self):
        for gate in ("OK", "ERROR"):
            result = collect(self.server(gate), "p", "a" * 40, "id", "main")
            self.assertTrue(result["complete"])
            self.assertFalse(result["restoration_verified"])
            self.assertEqual(result["gate"]["projectStatus"]["status"], gate)
            self.assertEqual(len(result["issues"]), 2)
            self.assertEqual(len(result["hotspots"]), 2)

    def test_wrong_analysis_revision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "revision mismatch"):
            collect(self.server(), "p", "b" * 40, "id", "main")

    def test_complete_pages(self):
        def get(endpoint, params):
            return {"paging": {"total": 2, "pageIndex": params["p"]},
                    "issues": [{"key": str(params["p"])}]}
        self.assertEqual(len(pages(get, "/api/issues/search", {}, "issues", "key")), 2)

    def test_incomplete_duplicate_and_excessive_pages_fail(self):
        for total, items in [(1, []), (10001, []), (2, [{"key": "same"}])]:
            def get(endpoint, params):
                return {"paging": {"total": total, "pageIndex": params["p"]}, "issues": items}
            with self.subTest(total=total), self.assertRaises(ValueError):
                pages(get, "/api/issues/search", {}, "issues", "key")

    def test_task_host_redirection_fails(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "report-task.txt"
            path.write_text("projectKey=p\nserverUrl=https://sonarcloud.io\ndashboardUrl=https://evil/\nceTaskId=id\nceTaskUrl=https://sonarcloud.io/api/ce/task?id=id\n")
            with self.assertRaisesRegex(ValueError, "foreign task URL"):
                task_properties(path, "p")

    def test_task_organization_is_identity_not_redirect_configuration(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "report-task.txt"
            path.write_text("projectKey=p\norganization=org\nserverUrl=https://sonarcloud.io\ndashboardUrl=https://sonarcloud.io/dashboard?id=p\nceTaskId=id\nceTaskUrl=https://sonarcloud.io/api/ce/task?id=id\n")
            self.assertEqual(task_properties(path, "p", "org")["organization"], "org")
            with self.assertRaisesRegex(ValueError, "organization mismatch"):
                task_properties(path, "p", "other")

    def test_pr_hotspot_completeness_is_not_fabricated(self):
        def get(endpoint, params):
            if endpoint == "/api/ce/task":
                return {"task": {"status": "SUCCESS", "componentKey": "p", "analysisId": "id"}}
            if endpoint == "/api/qualitygates/project_status":
                return {"projectStatus": {"status": "OK"}}
            if endpoint == "/api/project_branches/list":
                return {"branches": [{"name": "main", "isMain": True}]}
            if endpoint == "/api/measures/component":
                return {"component": {}}
            return {"paging": {"total": 0, "pageIndex": 1}, "components": [], "issues": []}
        result = collect(get, "p", "a" * 40, "id", "main", "12")
        self.assertFalse(result["complete"])
        self.assertTrue(result["partial"])
        self.assertFalse(result["restoration_verified"])
        self.assertIn("PR/nonmain", result["hotspot_scope"])

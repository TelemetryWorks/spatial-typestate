"""Pre-upload failure tests: fake gh verification and upload sentinel, no registry writes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_pypi as q
import release_guard as g
from test_release_guard import ENV, V, C, package


class PypiStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / 'target/release-artifacts'
        package(self.payload)
        for name in ('core.cdx.json', 'python.cdx.json', 'linux-runtime.json',
                     'windows-consumer-3.11.json', 'windows-consumer-3.14.json'):
            g.write_json(self.payload / name, {'bomFormat': 'CycloneDX'})
        g.checksums(self.payload)
        self.python, self.names, self.bundles = q.files(V)
        for name in self.bundles:
            (self.payload / name).write_text('{}')
        self.output = self.root / 'pypi-dist'
        self.environment = patch.dict(os.environ, {**ENV, 'GITHUB_REF_TYPE': 'tag'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.sbom = json.dumps([{'verificationResult': {'statement': {'predicate': {'bomFormat': 'CycloneDX'}}}}])

    def test_verified_stage_creates_only_the_three_selected_files(self):
        with patch.object(q.subprocess, 'run') as provenance, \
                patch.object(q.subprocess, 'check_output', return_value=self.sbom) as sbom:
            q.stage(self.payload, self.output, V, C)
        self.assertEqual({p.name for p in self.output.iterdir()}, {
            f'spatial_typestate-{V}-cp311-abi3-manylinux_2_28_x86_64.whl',
            f'spatial_typestate-{V}-cp311-abi3-win_amd64.whl', f'spatial_typestate-{V}.tar.gz'})
        self.assertEqual({Path(call.args[0][3]).name for call in provenance.call_args_list}, self.names)
        self.assertEqual({Path(call.args[0][3]).name for call in sbom.call_args_list}, set(self.python))
        for call in provenance.call_args_list + sbom.call_args_list:
            args = call.args[0]
            self.assertIn('TelemetryWorks/spatial-typestate/.github/workflows/build-release.yml', args)
            self.assertIn('refs/tags/v' + V, args)
            self.assertIn(C, args)
        for path in self.output.iterdir():
            self.assertEqual(path.read_bytes(), (self.payload / path.name).read_bytes())
        with self.assertRaisesRegex(ValueError, 'must not already exist'):
            q.stage(self.payload, self.output, V, C)

    def test_each_bad_signature_blocks_pypi_upload_and_leaves_no_upload_directory(self):
        # Models the workflow's default-success sequence: stage, then official uploader.
        for failure, subject in [('provenance', name) for name in sorted(self.names)] + [('sbom', name) for name in self.python]:
            with self.subTest(failure=failure, subject=subject):
                uploader = Mock()
                def provenance(args, **kwargs):
                    if failure == 'provenance' and Path(args[3]).name == subject:
                        raise subprocess.CalledProcessError(1, args, stderr='bad signature')
                def sbom(args, **kwargs):
                    if failure == 'sbom' and Path(args[3]).name == subject:
                        raise subprocess.CalledProcessError(1, args, stderr='bad signature')
                    return self.sbom
                def publish_steps():
                    q.stage(self.payload, self.output, V, C)
                    uploader(self.output)
                with patch.object(q.subprocess, 'run', side_effect=provenance), \
                        patch.object(q.subprocess, 'check_output', side_effect=sbom):
                    with self.assertRaises(subprocess.CalledProcessError):
                        publish_steps()
                uploader.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_empty_or_different_signed_sbom_is_not_an_uploadable_stage(self):
        for result in ('[]', '[{"verificationResult":{"statement":{"predicate":{"other":true}}}}]'):
            with self.subTest(result=result), patch.object(q.subprocess, 'run'), \
                    patch.object(q.subprocess, 'check_output', return_value=result):
                with self.assertRaisesRegex(ValueError, 'SBOM predicate differs'):
                    q.stage(self.payload, self.output, V, C)
                self.assertFalse(self.output.exists())

    def test_payload_errors_precede_signature_or_upload_work(self):
        sums = (self.payload / q.SUMS).read_bytes()
        archive = self.payload / f'spatial-typestate-{V}.crate'
        original = archive.read_bytes()
        for mutation, error in [('duplicate', 'invalid checksum'), ('path', 'invalid checksum'),
                                ('bytes', 'checksum mismatch'), ('missing', 'unexpected or missing'),
                                ('extra', 'unexpected or missing'), ('directory', 'unsafe payload')]:
            with self.subTest(mutation=mutation):
                if mutation == 'duplicate':
                    (self.payload / q.SUMS).write_bytes(sums + sums.splitlines(keepends=True)[0])
                elif mutation == 'path':
                    (self.payload / q.SUMS).write_bytes(sums + b'a'*64 + b'  ../escape\n')
                elif mutation == 'bytes':
                    archive.write_bytes(b'changed')
                elif mutation == 'missing':
                    archive.unlink()
                elif mutation == 'extra':
                    (self.payload / 'extra').write_text('extra')
                elif mutation == 'directory':
                    archive.unlink()
                    archive.mkdir()
                with patch.object(q, 'verify_signatures') as verify:
                    with self.assertRaisesRegex(ValueError, error):
                        q.stage(self.payload, self.output, V, C)
                    verify.assert_not_called()
                    self.assertFalse(self.output.exists())
                if archive.is_dir():
                    archive.rmdir()
                archive.write_bytes(original)
                (self.payload / 'extra').unlink(missing_ok=True)
                (self.payload / q.SUMS).write_bytes(sums)

    def test_script_guard_blocks_non_tag_contexts_before_any_reads_or_uploads(self):
        for key, value in [('GITHUB_EVENT_NAME', 'pull_request'), ('GITHUB_EVENT_NAME', 'workflow_dispatch'),
                           ('GITHUB_REPOSITORY', 'fork/repo'), ('GITHUB_REF_TYPE', 'branch'),
                           ('GITHUB_REF', 'refs/tags/v1.2.3'), ('GITHUB_SHA', 'bad')]:
            with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value, 'PUBLISH': 'true'}), \
                    patch.object(q, 'check_payload') as check:
                with self.assertRaisesRegex(ValueError, 'independent original-repository version tag push'):
                    q.stage(self.payload, self.output, V, C)
                check.assert_not_called()
                self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError, 'version tag push'):
            q.require_publish('../bad', C)

    def test_version_digits_remain_ascii_only(self):
        for version in ('1٠.2.3', '1.2٠.3', '1.2.3٠'):
            with self.subTest(version=version), patch.dict(os.environ, {'GITHUB_REF': 'refs/tags/v' + version}):
                with self.assertRaisesRegex(ValueError, 'version tag push'):
                    q.require_publish(version, C)

    def test_isolated_script_has_no_checkout_import_dependency_and_cli_uses_fixed_paths(self):
        script = Path(q.__file__).resolve()
        result = subprocess.run([sys.executable, '-I', script, '--help'], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('stage', result.stdout)
        for event in ('pull_request', 'workflow_dispatch'):
            result = subprocess.run([sys.executable, '-I', script, 'stage'], cwd=self.root,
                                    env=dict(os.environ, GITHUB_EVENT_NAME=event), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('independent original-repository version tag push', result.stderr)
            self.assertFalse(self.output.exists())
        with patch.object(sys, 'argv', ['release_pypi.py', 'stage']), patch.object(q, 'stage') as stage:
            q.main()
            stage.assert_called_once_with(Path('target/release-artifacts'), Path('pypi-dist'), V, C)

    def test_workflow_authenticates_helper_before_execution_and_upload_cannot_bypass_failure(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/trusted-publishing.yml').read_text()
        builder = (root / '.github/workflows/qualify-release.yml').read_text()
        digest = hashlib.sha256(Path(q.__file__).read_bytes()).hexdigest()
        self.assertEqual(workflow.count("'" + digest + "'"), 2)
        job = workflow.split('\n  publish-pypi:\n')[1].split('\n  github-release:\n')[0]
        self.assertNotIn('actions/checkout', job)
        self.assertNotIn('contents:', job)
        self.assertNotIn('continue-on-error', job)
        self.assertNotIn('if: always', job)
        self.assertNotIn("python3 - <<", job)
        self.assertLess(job.index('sha256sum --check --strict'), job.index('python3 -I'))
        self.assertLess(job.index('python3 -I'), job.index('uses: pypa/gh-action-pypi-publish@'))
        self.assertIn('python3 -I "$RUNNER_TEMP/pypi-verifier/release_pypi.py" stage', job)
        self.assertIn('packages-dir: pypi-dist/', job)
        self.assertIn('name: pypi-preupload-verifier', builder)
        self.assertIn('path: .github/scripts/release_pypi.py', builder)


if __name__ == '__main__':
    unittest.main()

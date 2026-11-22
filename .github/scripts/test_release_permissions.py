"""Finite permission-probe contracts; real token capability is exercised by hosted CI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_pypi as q
from test_release_guard import C, ENV

REF = 'refs/pull/42/merge'


class PermissionProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / q.PROBE_FILE).write_bytes(q.PROBE_CONTENT)
        (self.root / q.PROBE_SBOM).write_bytes(q.PROBE_BOM)
        for name in q.PROBE_BUNDLES:
            (self.root / name).write_text('{}')
        self.env = patch.dict(os.environ, {**ENV, 'GITHUB_EVENT_NAME': 'pull_request',
                                         'GITHUB_REF_TYPE': 'branch', 'GITHUB_REF': REF})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.sbom = json.dumps([{'verificationResult': {'statement': {'predicate': json.loads(q.PROBE_BOM)}}}])

    def test_probe_runs_real_shared_provenance_and_sbom_path_without_staging(self):
        with patch.object(q.subprocess, 'run') as provenance, \
                patch.object(q.subprocess, 'check_output', return_value=self.sbom) as sbom, \
                patch.object(q, 'stage') as stage:
            q.verify_permissions(self.root, C, REF)
        self.assertEqual(provenance.call_count, 2)
        sbom.assert_called_once()
        stage.assert_not_called()
        self.assertEqual({Path(c.args[0][3]).name for c in provenance.call_args_list}, {q.PROBE_FILE, q.PROBE_SBOM})
        for call in provenance.call_args_list + sbom.call_args_list:
            self.assertIn(q.BUILDER, call.args[0])
            self.assertIn(C, call.args[0])
            self.assertIn(REF, call.args[0])
            self.assertIn('--deny-self-hosted-runners', call.args[0])
        self.assertEqual(set(p.name for p in self.root.iterdir()), {q.PROBE_FILE, q.PROBE_SBOM, *q.PROBE_BUNDLES})

    def test_probe_and_release_share_the_same_verification_implementation(self):
        with patch.object(q, 'verify_bundles') as verify:
            q.verify_permissions(self.root, C, REF)
            probe = verify.call_args
            q.verify_signatures(self.root, '1.2.3', C, ['wheel.whl'], {'wheel.whl'}, ('provenance', 'unused', 'sbom'))
            release = verify.call_args
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(probe.args[-1], q.signature_policy(C, REF))
        self.assertEqual(release.args[-1], q.signature_policy(C, 'refs/tags/v1.2.3'))
        # Every policy field is identical except the expected source ref.
        a, b = list(probe.args[-1]), list(release.args[-1])
        a[a.index('--source-ref')+1] = b[b.index('--source-ref')+1]
        self.assertEqual(a, b)

    def test_probe_accepts_branch_dispatch_but_rejects_tags_foreign_identity_and_events(self):
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/main'}), \
                patch.object(q, 'verify_bundles'):
            q.verify_permissions(self.root, C, 'refs/heads/main')
        cases = [('GITHUB_REPOSITORY', 'fork/repo'), ('GITHUB_EVENT_NAME', 'push'),
                 ('GITHUB_REF_TYPE', 'tag'), ('GITHUB_REF', 'refs/tags/v1.2.3'), ('GITHUB_SHA', 'bad')]
        for name, value in cases:
            with self.subTest(name=name), patch.dict(os.environ, {name: value}), patch.object(q, 'verify_bundles') as verify:
                with self.assertRaisesRegex(ValueError, 'PR or branch dry run'):
                    q.verify_permissions(self.root, C, REF)
                verify.assert_not_called()
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF_TYPE': 'tag',
                                     'GITHUB_REF': 'refs/tags/v1.2.3'}), patch.object(q, 'verify_bundles') as verify:
            with self.assertRaisesRegex(ValueError, 'PR or branch dry run'):
                q.verify_permissions(self.root, C, 'refs/tags/v1.2.3')
            verify.assert_not_called()

    def test_probe_rejects_non_fixture_payloads_and_verifier_errors_are_fatal(self):
        (self.root / q.PROBE_FILE).write_bytes(b'a real release artifact must not be signed here')
        with patch.object(q, 'verify_bundles') as verify:
            with self.assertRaisesRegex(ValueError, 'fixed non-release content'):
                q.verify_permissions(self.root, C, REF)
            verify.assert_not_called()
        (self.root / q.PROBE_FILE).write_bytes(q.PROBE_CONTENT)
        (self.root / 'extra.whl').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError, 'fixture files'):
            q.verify_permissions(self.root, C, REF)
        (self.root / 'extra.whl').unlink()
        for mode in ('provenance', 'sbom'):
            failure = subprocess.CalledProcessError(1, 'gh', stderr='permission denied')
            with self.subTest(mode=mode), patch.object(q.subprocess, 'run', side_effect=failure if mode=='provenance' else None), \
                    patch.object(q.subprocess, 'check_output', side_effect=failure):
                with self.assertRaises(subprocess.CalledProcessError):
                    q.verify_permissions(self.root, C, REF)

    def test_cli_selects_readonly_probe_with_fixed_paths_and_actual_identity(self):
        with patch.object(sys, 'argv', ['release_pypi.py', 'verify-permissions']), \
                patch.object(q, 'verify_permissions') as verify, patch.object(q, 'stage') as stage:
            q.main()
            verify.assert_called_once_with(Path('target/permission-probe'), C, REF)
            stage.assert_not_called()

    def test_workflow_probe_uses_publisher_permissions_no_checkout_or_environment(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/trusted-publishing.yml').read_text()
        probe = workflow.split('\n  publish-permissions-check:\n')[1].split('\n  publish-crates:\n')[0]
        publish = workflow.split('\n  publish-pypi:\n')[1].split('\n  github-release:\n')[0]
        def permissions(section):
            return section.split('    permissions:\n')[1].split('    steps:')[0].split('    env:')[0].strip()
        self.assertEqual(permissions(probe), permissions(publish))
        self.assertEqual(permissions(probe), 'id-token: write')
        self.assertNotIn('actions/checkout', probe)
        self.assertNotIn('environment:', probe)
        self.assertNotIn('pypa/gh-action-pypi-publish', probe)
        self.assertIn('gh --version', probe)
        self.assertIn('release_pypi.py" verify-permissions', probe)
        self.assertIn('dependabot[bot]', probe)
        self.assertIn("github.ref_type == 'branch'", probe)
        builder = (root / '.github/workflows/build-release.yml').read_text()
        fixture = builder.split('\n  permission-fixture:\n')[1].split('\n  sign:\n')[0]
        self.assertNotIn('actions/checkout', fixture)
        self.assertIn('!inputs.publish', fixture)
        self.assertIn('dependabot[bot]', fixture)
        self.assertIn("github.ref_type == 'branch'", fixture)
        self.assertNotIn('target/release-artifacts', fixture)
        self.assertIn('name: token-permission-fixture', fixture)
        # The actual release signer remains independently tag-only.
        release_signer = builder.split('\n  sign:\n')[1]
        self.assertIn("inputs.publish && github.event_name == 'push' && github.ref_type == 'tag'", release_signer)

    @unittest.skipIf(os.name == 'nt', 'fixture producer is a Linux shell step')
    def test_actual_fixture_generation_step_produces_only_fixed_non_release_data(self):
        builder = (Path(__file__).resolve().parents[1] / 'workflows/build-release.yml').read_text()
        run = builder.split('      - name: Generate fixed non-release permission fixture\n')[1].split('      - id: provenance')[0]
        script = textwrap.dedent(run.split('        run: |\n')[1])
        subprocess.run(['bash', '-euo', 'pipefail', '-c', script], env=dict(os.environ, RUNNER_TEMP=str(self.root)), check=True)
        actual = self.root / 'permission-probe'
        self.assertEqual((actual / q.PROBE_FILE).read_bytes(), q.PROBE_CONTENT)
        self.assertEqual((actual / q.PROBE_SBOM).read_bytes(), q.PROBE_BOM)
        self.assertEqual({p.name for p in actual.iterdir()}, {q.PROBE_FILE, q.PROBE_SBOM})


if __name__ == '__main__':
    unittest.main()

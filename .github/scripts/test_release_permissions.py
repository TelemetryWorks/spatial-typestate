"""Committed offline fixture contracts; hosted CI additionally disables networking."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_pypi as q

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / '.github/release-fixtures/permission-probe'


class PermissionProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'fixture'
        shutil.copytree(FIXTURE, self.root)
        self.record = json.loads((self.root / q.PROBE_RECORD).read_bytes())
        self.sbom = json.dumps([{'verificationResult': {'statement': {'predicate': json.loads(q.PROBE_BOM)}}}])

    def test_committed_record_and_every_file_match_pinned_digests(self):
        self.assertEqual(hashlib.sha256((self.root / q.PROBE_RECORD).read_bytes()).hexdigest(), q.PROBE_RECORD_SHA256)
        for name, digest in self.record['files'].items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(self.record['source_sha'], 'bf8faabc011092a5b2e0f7595aa2168fdcaa4380')
        self.assertEqual(self.record['run_id'], '45061133325')

    def test_shared_real_cli_path_uses_recorded_identity_not_current_pr(self):
        with patch.dict(os.environ, {'GITHUB_SHA': 'different-pr', 'GITHUB_REPOSITORY': 'fork/repo'}), \
                patch.object(q.subprocess, 'run') as provenance, \
                patch.object(q.subprocess, 'check_output', return_value=self.sbom) as sbom, \
                patch.object(q, 'stage') as stage:
            q.verify_permissions(self.root)
        self.assertEqual(provenance.call_count, 2)
        sbom.assert_called_once()
        stage.assert_not_called()
        for call in provenance.call_args_list + sbom.call_args_list:
            argv = call.args[0]
            for value in (self.record['source_sha'], self.record['source_ref'], self.record['signer_workflow'],
                          '--deny-self-hosted-runners', '--custom-trusted-root', str(self.root / q.PROBE_TRUST)):
                self.assertIn(value, argv)

    def test_fixture_and_release_share_verifier_but_keep_separate_signing_identities(self):
        with patch.object(q, 'verify_bundles') as verify:
            q.verify_permissions(self.root)
            fixture = verify.call_args
            q.verify_signatures(self.root, '1.2.3', 'a'*40, ['a.whl'], {'a.whl'}, ('prov', 'unused', 'sbom'))
            release = verify.call_args
        self.assertEqual(verify.call_count, 2)
        self.assertIn('--custom-trusted-root', fixture.args[-1])
        self.assertIn(self.record['signer_workflow'], fixture.args[-1])
        self.assertEqual(release.args[-1], q.signature_policy('a'*40, 'refs/tags/v1.2.3'))
        self.assertNotIn('--custom-trusted-root', release.args[-1])

    def test_record_or_any_file_tampering_stops_before_gh(self):
        for name in [q.PROBE_RECORD, *self.record['files']]:
            path = self.root / name
            raw = path.read_bytes()
            with self.subTest(name=name), patch.object(q, 'verify_bundles') as verify:
                path.write_bytes(raw + b' ')
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    q.verify_permissions(self.root)
                verify.assert_not_called()
            path.write_bytes(raw)

    def test_extra_file_rejected_and_signature_failures_propagate(self):
        extra = self.root / 'extra.whl'
        extra.write_bytes(b'not allowed')
        with self.assertRaisesRegex(ValueError, 'fixture files'):
            q.verify_permissions(self.root)
        extra.unlink()
        failure = subprocess.CalledProcessError(1, 'gh')
        for mode in ('provenance', 'sbom'):
            with self.subTest(mode=mode), \
                    patch.object(q.subprocess, 'run', side_effect=failure if mode == 'provenance' else None), \
                    patch.object(q.subprocess, 'check_output', side_effect=failure):
                with self.assertRaises(subprocess.CalledProcessError):
                    q.verify_permissions(self.root)

    def test_sbom_predicate_mismatch_fails_closed(self):
        raw = json.dumps([{'verificationResult': {'statement': {'predicate': {}}}}])
        with patch.object(q.subprocess, 'run'), patch.object(q.subprocess, 'check_output', return_value=raw):
            with self.assertRaisesRegex(ValueError, 'SBOM predicate differs'):
                q.verify_permissions(self.root)

    def test_cli_uses_fixed_committed_path_without_event_or_token_requirements(self):
        with patch.object(sys, 'argv', ['release_pypi.py', 'verify-permissions']), \
                patch.object(q, 'verify_permissions') as verify, patch.object(q, 'stage') as stage:
            q.main()
        verify.assert_called_once_with(Path('.github/release-fixtures/permission-probe'))
        stage.assert_not_called()

    def test_every_pr_verifies_offline_with_readonly_permissions_and_no_signing(self):
        workflow = (ROOT / '.github/workflows/verify-release-fixture.yml').read_text()
        self.assertIn('  pull_request:\n', workflow)
        self.assertNotIn('    paths:', workflow)
        self.assertNotIn('id-token:', workflow)
        self.assertNotIn('attestations:', workflow)
        self.assertNotIn('secrets:', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertIn('sudo unshare --net -- python3 -I .github/scripts/release_pypi.py verify-permissions', workflow)
        self.assertNotIn('actions/attest@', workflow)

    def test_pr_call_graph_never_delegates_oidc_or_attestation_writes(self):
        workflow = (ROOT / '.github/workflows/trusted-publishing.yml').read_text()
        builder = (ROOT / '.github/workflows/build-release.yml').read_text()
        qualifier = (ROOT / '.github/workflows/qualify-release.yml').read_text()
        self.assertNotIn('id-token:', qualifier)
        self.assertNotIn('attestations:', qualifier)
        self.assertNotIn('actions/attest@', qualifier)
        dry = workflow.split('\n  build-dry-run:\n')[1].split('\n  publish-path-check:\n')[0]
        self.assertIn('uses: ./.github/workflows/qualify-release.yml', dry)
        self.assertNotIn('id-token:', dry)
        self.assertNotIn('attestations:', dry)
        self.assertIn("needs.gate.outputs.publish != 'true'", dry)
        for section in (workflow.split('\n  build:\n')[1].split('\n  build-dry-run:\n')[0],
                        builder.split('\n  sign:\n')[1]):
            self.assertIn("github.event_name == 'push' && github.ref_type == 'tag'", section)
        self.assertNotIn('permission-fixture:', builder)
        self.assertNotIn('publish-permissions-check:', workflow)
        self.assertIn('sudo unshare --net -- python3 -I .github/scripts/release_pypi.py verify-permissions', workflow)


if __name__ == '__main__':
    unittest.main()

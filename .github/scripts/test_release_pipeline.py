"""Finite release safety regressions: no credentials, builds or registry mutations."""
from contextlib import ExitStack
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_pipeline as p
import release_guard as g
from test_release_guard import ENV, V, C, package


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'payload'
        self.record = package(self.directory)
        self.env = patch.dict(os.environ, {**ENV, 'GITHUB_REF_TYPE': 'tag'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def signed(self):
        for name in p.sidecars(V):
            (self.directory / name).write_text('{}')

    def test_dispatch_from_tag_and_forged_flag_have_no_publish_authority(self):
        p.require_publish()
        for field, value in [('GITHUB_EVENT_NAME', 'workflow_dispatch'), ('GITHUB_EVENT_NAME', 'pull_request'),
                             ('GITHUB_REPOSITORY', 'fork/repo'), ('GITHUB_REF_TYPE', 'branch'),
                             ('GITHUB_REF', 'refs/heads/main')]:
            with self.subTest(field=field, value=value), patch.dict(os.environ, {field: value, 'PUBLISH': 'true'}):
                self.assertFalse(p.publishing())
                with self.assertRaisesRegex(ValueError, 'independent'):
                    p.require_publish()

    def test_paginated_ci_has_no_success_filter_and_requires_intended_main_push(self):
        rows = [{'path': '.github/workflows/' + name, 'head_sha': C, 'head_branch': 'main',
                 'event': 'push', 'conclusion': 'success'} for name in ('ci.yml', 'python.yml', 'codeql.yml', 'sonar-analysis.yml')]
        first = {'workflow_runs': [{'path': 'unrelated', 'head_sha': C, 'head_branch': 'main',
                                   'event': 'push', 'conclusion': 'success'}] * 100}
        with patch.object(g, 'gh_json', side_effect=[first, {'workflow_runs': rows}]) as api:
            p.check_ci(C)
            self.assertIn('page=2', api.call_args.args[0])
            self.assertNotIn('status=', api.call_args.args[0])
        for field, value in [('head_sha', 'bad'), ('head_branch', 'other'), ('event', 'pull_request'), ('conclusion', 'failure')]:
            bad = copy.deepcopy(rows)
            bad[0][field] = value
            with patch.object(p, 'pages', return_value=bad):
                with self.assertRaisesRegex(ValueError, 'intended main CI'):
                    p.check_ci(C)
        with patch.object(g, 'gh_json', return_value=[{}] * 100):
            with self.assertRaisesRegex(ValueError, 'pagination'):
                p.pages('path')
        with patch.object(g, 'gh_json', return_value=[]):
            self.assertEqual(p.pages('path?x=1'), [])

    def test_remote_annotation_and_peeling_are_server_checks(self):
        commit = {'object': {'type': 'commit', 'sha': C}}
        with patch.object(g, 'gh_json', side_effect=[{'object': {'type': 'tag', 'sha': 'a'*40}}, commit]):
            p.remote_tag(V, C)
        with patch.object(g, 'gh_json', return_value=commit):
            with self.assertRaisesRegex(ValueError, 'annotated'):
                p.remote_tag(V, C)
        with patch.object(g, 'gh_json', side_effect=[{'object': {'type': 'tag', 'sha': C}}, {'object': {'type': 'commit', 'sha': 'bad'}}]):
            with self.assertRaisesRegex(ValueError, 'event SHA'):
                p.remote_tag(V, C)
        with patch.object(g, 'gh_json', return_value={'object': {'type': 'tag', 'sha': C}}):
            with self.assertRaisesRegex(ValueError, 'event SHA'):
                p.remote_tag(V, C)

    def notes_fixture(self):
        (self.root / 'docs/releases').mkdir(parents=True)
        (self.root / 'docs/releases' / f'v{V}.md').write_text('# Reviewed release\n\nTitle source.\n')
        (self.root / 'CHANGELOG.md').write_text(f'# Changes\n\n## [{V}] - 2026-11-22\n\nExact dated body.\n\n## [0.1.0] - 2026-11-08\nold\n')

    def test_dated_notes_missing_invalid_date_and_title_fail(self):
        self.notes_fixture()
        with patch.object(g, 'ROOT', self.root):
            self.assertEqual(p.notes(V), ('Reviewed release', 'Exact dated body.\n'))
            file = self.root / 'CHANGELOG.md'
            original = file.read_text()
            for value, error in [(original.replace('2026-11-22', 'Unreleased'), 'dated'),
                                  (original.replace('2026-11-22', '2026-99-22'), 'month')]:
                file.write_text(value)
                with self.assertRaisesRegex(ValueError, error):
                    p.notes(V)
            file.write_text(original)
            (self.root / 'docs/releases' / f'v{V}.md').write_text('no title')
            with self.assertRaisesRegex(ValueError, 'committed release notes'):
                p.notes(V)

    def test_gate_reports_on_pr_but_same_findings_block_tag_and_versions_always_fail(self):
        (self.root / 'Cargo.toml').write_text(f'[package]\nversion="{V}"\n')
        output = self.root / 'outputs'
        with patch.object(g, 'ROOT', self.root), patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), \
                patch.object(g, 'source_guard'), patch.object(p, 'remote_tag', side_effect=ValueError('annotation')), \
                patch.object(p, 'command'), patch.object(p, 'check_ci'), patch.object(p, 'notes'):
            with self.assertRaisesRegex(ValueError, 'tag release blocked'):
                p.gate()
            with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'pull_request'}):
                p.gate()
            self.assertIn('publish=false\n', output.read_text())
            self.assertIn('crates=spatial-typestate\n', output.read_text())
        with patch.object(g, 'ROOT', self.root), patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}), \
                patch.object(g, 'source_guard'), patch.object(p, 'remote_tag'), patch.object(p, 'command'), \
                patch.object(p, 'check_ci'), patch.object(p, 'notes'):
            p.gate()
            self.assertIn('publish=true\n', output.read_text())

    def test_sidecar_set_exact_and_frozen_payload_is_not_resealed(self):
        original = (self.directory / g.SUMS).read_bytes()
        self.assertEqual(p.payload(self.directory, V, C), self.record)
        self.signed()
        self.assertEqual(p.payload(self.directory, V, C, signed=True), self.record)
        self.assertEqual(original, (self.directory / g.SUMS).read_bytes())
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            p.payload(self.directory, V, C)
        (self.directory / p.sidecars(V)[0]).unlink()
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            p.payload(self.directory, V, C, signed=True)
        (self.directory / p.sidecars(V)[0]).mkdir()
        with self.assertRaisesRegex(ValueError, 'unsafe attestation'):
            p.payload(self.directory, V, C, signed=True)
        (self.directory / p.sidecars(V)[0]).rmdir()
        (self.directory / p.sidecars(V)[0]).write_text('{}')
        (self.directory / 'extra-directory').mkdir()
        with self.assertRaisesRegex(ValueError, 'unsafe payload'):
            p.payload(self.directory, V, C, signed=True)

    def test_failed_job_recovery_accepts_original_frozen_attempt_not_future_attempt(self):
        with patch.dict(os.environ, {'GITHUB_RUN_ATTEMPT': '2'}):
            self.assertEqual(p.payload(self.directory, V, C)['run_attempt'], 1)
        self.record['run_attempt'] = 3
        g.write_json(self.directory / g.MANIFEST, self.record)
        g.checksums(self.directory)
        with self.assertRaisesRegex(ValueError, 'run/source identity'):
            p.payload(self.directory, V, C)

    def test_signatures_require_builder_ref_sha_and_sbom_content_for_all_files(self):
        self.signed()
        for name in ('core.cdx.json', 'python.cdx.json'):
            g.write_json(self.directory / name, {'bomFormat': 'CycloneDX'})
        # Rebuild fixture sums excluding precisely the signature sidecar.
        for name in p.sidecars(V):
            (self.directory / name).unlink()
        g.checksums(self.directory)
        self.signed()
        result = json.dumps([{'verificationResult': {'statement': {'predicate': {'bomFormat': 'CycloneDX'}}}}])
        with patch.object(p, 'command') as verify, patch.object(g, 'run', return_value=result):
            self.assertEqual(p.signatures(self.directory, V, C)['version'], V)
            self.assertEqual(verify.call_count, len((self.directory / g.SUMS).read_text().splitlines()))
            argv = verify.call_args.args
            self.assertIn(g.REPOSITORY + '/.github/workflows/build-release.yml', argv)
            self.assertIn('refs/tags/v' + V, argv)
            self.assertIn(C, argv)
        with patch.object(p, 'command'), patch.object(g, 'run', return_value='[]'):
            with self.assertRaisesRegex(ValueError, 'SBOM predicate'):
                p.signatures(self.directory, V, C)

    def test_repackage_never_compiles_and_checks_actual_compiler_and_exact_bytes(self):
        target = self.root / 'target/package'
        target.mkdir(parents=True)
        archive = target / g.names(V)[0]
        archive.write_bytes((self.directory / archive.name).read_bytes())
        with patch.object(g, 'ROOT', self.root), patch.object(g, 'run', return_value='rustc 1.99.0 (hash)'), \
                patch.object(p, 'payload'), patch.object(g, 'crate_check'), patch.object(p, 'command') as cmd:
            p.compare_crate(self.directory, V, C, '1.99.0')
            cmd.assert_called_once_with('cargo', 'package', '--locked', '--no-verify', '--jobs', '2')
            archive.write_bytes(b'different')
            with self.assertRaisesRegex(ValueError, 'repackaged crate differs'):
                p.compare_crate(self.directory, V, C, '1.99.0')
            with self.assertRaisesRegex(ValueError, 'compiler mismatch'):
                p.compare_crate(self.directory, V, C, '1.100.0')

    def test_known_good_is_independent_pinned_fixture_not_two_downloads(self):
        fixture = self.root / '.github/release-fixtures'
        fixture.mkdir(parents=True)
        file = fixture / 'spatial-typestate-0.1.0.sha256'
        file.write_text(p.KNOWN_SHA + '  spatial-typestate-0.1.0.crate\n')
        with patch.object(g, 'ROOT', self.root), patch.object(g, 'public', return_value=b'bad') as download:
            with self.assertRaisesRegex(ValueError, 'registry archive mismatch'):
                p.known_good()
            download.assert_called_once_with(p.KNOWN_URL)
            with patch.object(g, 'public', return_value=b'x' * 64458), patch.object(p.hashlib, 'sha256') as sha:
                sha.return_value.hexdigest.return_value = p.KNOWN_SHA
                p.known_good()
            file.write_text('untrusted')
            download.reset_mock()
            with self.assertRaisesRegex(ValueError, 'fixture changed'):
                p.known_good()
            download.assert_not_called()

    def test_existing_registry_version_is_never_reuploaded_but_always_verified(self):
        for existing in (None, {'version': V}):
            with self.subTest(existing=existing), patch.object(p, 'signatures', return_value=self.record), \
                    patch.object(g, 'public_json', return_value=existing), patch.object(p, 'command') as upload, \
                    patch.object(g, 'crate_public') as verify:
                p.publish_crate(self.directory, V, C)
                self.assertEqual(upload.call_count, int(existing is None))
                if existing is None:
                    self.assertIn('--no-verify', upload.call_args.args)
                verify.assert_called_once()
        with patch.object(p, 'signatures', return_value=self.record), patch.object(g, 'public_json', return_value={}), \
                patch.object(p, 'command') as upload, patch.object(g, 'crate_public', side_effect=ValueError('mismatch')):
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                p.publish_crate(self.directory, V, C)
            upload.assert_not_called()

    def test_docsrs_pending_and_failure_are_never_pass(self):
        with patch.object(g, 'public_json', return_value={'doc_status': True, 'version': V}):
            p.docs_rs(V)
        for value in (None, {}, {'doc_status': False, 'version': V}, {'doc_status': True, 'version': 'other'}):
            with patch.object(g, 'public_json', return_value=value) as api, patch.object(p.time, 'sleep'):
                with self.assertRaisesRegex(ValueError, 'not successful at bounded deadline'):
                    p.docs_rs(V)
                self.assertEqual(api.call_count, 12)

    def test_release_lookup_includes_interrupted_drafts_and_latest_is_semantic(self):
        rows = [{'tag_name': 'v9.8.7', 'draft': True, 'prerelease': False},
                {'tag_name': 'v9.8.6', 'draft': False, 'prerelease': False},
                {'tag_name': 'v10.0.0-rc1', 'draft': False, 'prerelease': True}]
        with patch.object(p, 'pages', return_value=rows):
            self.assertEqual(p.find_release(V), rows[0])
            self.assertTrue(p.latest(V))
            self.assertFalse(p.latest('9.8.5'))
        with patch.object(p, 'pages', return_value=rows + [rows[0]]):
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                p.find_release(V)
        with patch.object(p, 'pages', return_value=[]):
            self.assertIsNone(p.find_release(V))
            self.assertTrue(p.latest(V))

    def asset_fixture(self):
        return {'tag_name': 'v' + V, 'name': 'Reviewed title', 'body': 'Reviewed body\n', 'draft': True,
                'assets': [{'name': x.name, 'size': x.stat().st_size, 'digest': 'sha256:' + g.digest(x)}
                           for x in self.directory.iterdir()]}

    def test_asset_sizes_digests_and_downloads_checked_before_any_mutation(self):
        release = self.asset_fixture()
        def fetch(*args):
            target = Path(args[args.index('--dir') + 1])
            name = args[args.index('--pattern') + 1]
            (target / name).write_bytes((self.directory / name).read_bytes())
        with patch.object(p, 'command', side_effect=fetch):
            self.assertEqual(p.verify_assets(release, self.directory, False), set())
        for field, bad in [('size', 0), ('digest', 'sha256:bad')]:
            value = copy.deepcopy(release)
            value['assets'][0][field] = bad
            with patch.object(p, 'command') as cmd:
                with self.assertRaisesRegex(ValueError, 'size/digest differs'):
                    p.verify_assets(value, self.directory, True)
                cmd.assert_not_called()
        def corrupt(*args):
            (Path(args[args.index('--dir') + 1]) / args[args.index('--pattern') + 1]).write_bytes(b'bad')
        with patch.object(p, 'command', side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                p.verify_assets(release, self.directory, False)
        bad = copy.deepcopy(release)
        bad['assets'].append(bad['assets'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            p.verify_assets(bad, self.directory, False)
        release['assets'] = []
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            p.verify_assets(release, self.directory, False)
        self.assertEqual(p.verify_assets(release, self.directory, True), {x.name for x in self.directory.iterdir()})

    def test_release_draft_resume_published_readonly_and_no_clobber(self):
        release = self.asset_fixture()
        final = {**release, 'draft': False}
        with patch.object(p, 'remote_tag'), patch.object(p, 'signatures'), \
                patch.object(p, 'notes', return_value=('Reviewed title', 'Reviewed body\n')), \
                patch.object(p, 'latest', return_value=True), patch.object(p, 'verify_assets', return_value={'SHA256SUMS'}), \
                patch.object(p, 'command') as commands, patch.object(p, 'find_release', side_effect=[None, release, release, final]):
            p.release_assets(self.directory, V, C)
            self.assertEqual([c.args[2] for c in commands.call_args_list], ['create', 'upload', 'edit'])
            self.assertTrue(all('--clobber' not in c.args for c in commands.call_args_list))
        with patch.object(p, 'remote_tag'), patch.object(p, 'signatures'), \
                patch.object(p, 'notes', return_value=('Reviewed title', 'Reviewed body\n')), \
                patch.object(p, 'verify_assets', return_value=set()), patch.object(p, 'find_release', return_value=final), \
                patch.object(p, 'command') as commands:
            p.release_assets(self.directory, V, C)
            commands.assert_not_called()
        with patch.object(p, 'remote_tag'), patch.object(p, 'signatures'), patch.object(p, 'notes', return_value=('bad', 'bad')), \
                patch.object(p, 'find_release', return_value=final), patch.object(p, 'command') as commands:
            with self.assertRaisesRegex(ValueError, 'title/body'):
                p.release_assets(self.directory, V, C)
            commands.assert_not_called()

    def test_final_verification_uses_fresh_registries_and_integrity_before_docsrs(self):
        with ExitStack() as stack:
            mocks = {name: stack.enter_context(patch.object(p, name)) for name in ('remote_tag', 'verify_assets', 'docs_rs')}
            stack.enter_context(patch.object(p, 'signatures', return_value=self.record))
            lookup = stack.enter_context(patch.object(p, 'find_release', return_value={'draft': False}))
            crate = stack.enter_context(patch.object(g, 'crate_public'))
            python = stack.enter_context(patch.object(g, 'pypi_public'))
            import release_integrity
            integrity = stack.enter_context(patch.object(release_integrity, 'verify'))
            p.verify(self.directory, V, C)
            crate.assert_called_once()
            python.assert_called_once()
            integrity.assert_called_once()
            mocks['docs_rs'].assert_called_once_with(V)
            lookup.return_value = {'draft': True}
            with self.assertRaisesRegex(ValueError, 'public GitHub release'):
                p.verify(self.directory, V, C)

    def test_cli_dispatch_and_check_mode_are_readonly(self):
        modes = {'gate': 'gate', 'known-good': 'known_good', 'check': 'payload', 'signatures': 'signatures',
                 'compare': 'compare_crate', 'publish-crate': 'publish_crate', 'assets': 'release_assets', 'verify': 'verify'}
        with ExitStack() as stack:
            mocks = {name: stack.enter_context(patch.object(p, name)) for name in modes.values()}
            for mode, name in modes.items():
                for mock in mocks.values():
                    mock.reset_mock()
                with patch.object(sys, 'argv', ['release_pipeline.py', mode]):
                    p.main()
                mocks[name].assert_called_once()

    def test_workflow_boundary_no_checkout_in_pypi_and_independent_guards(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/trusted-publishing.yml').read_text()
        builder = (root / '.github/workflows/build-release.yml').read_text()
        for job, end in [('publish-crates', 'publish-pypi'), ('publish-pypi', 'github-release'),
                         ('github-release', 'verify')]:
            section = workflow.split('\n  ' + job + ':\n')[1].split('\n  ' + end + ':\n')[0]
            self.assertIn("github.event_name == 'push' && github.ref_type == 'tag'", section)
        python = workflow.split('\n  publish-pypi:\n')[1].split('\n  github-release:\n')[0]
        self.assertNotIn('actions/checkout', python)
        self.assertNotIn('contents:', python)
        self.assertNotIn('attestations: write', python)
        self.assertIn('skip-existing: true', python)
        self.assertIn('attestations: true', python)
        self.assertIn("inputs.publish && github.event_name == 'push' && github.ref_type == 'tag'", builder)
        for text in (workflow, builder):
            self.assertNotIn('ref: ${{ needs.', text)
            self.assertNotIn('secrets:', text)
            self.assertNotIn('publish-0.1.0.yml', text)
        crate = workflow.split('\n  publish-crates:\n')[1].split('\n  publish-pypi:\n')[0]
        self.assertNotIn('attestations: write', crate)
        self.assertNotIn('cargo build', crate)
        self.assertNotIn('cargo test', crate)


if __name__ == '__main__':
    unittest.main()

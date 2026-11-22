"""Finite release fixtures only: no registry mutation, whole builds or credential requests."""
from contextlib import ExitStack
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch, Mock
import urllib.error
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import release_guard as g
import release_integrity as integrity

V = '9.8.7'
C = '1' * 40
ENV = {'GITHUB_REPOSITORY': 'TelemetryWorks/spatial-typestate', 'GITHUB_EVENT_NAME': 'push',
       'GITHUB_REF_TYPE': 'tag', 'GITHUB_REF': 'refs/tags/v9.8.7', 'GITHUB_REF_NAME': 'v9.8.7', 'GITHUB_RUN_ATTEMPT': '1',
       'GITHUB_SHA': C, 'GITHUB_RUN_ID': '42', 'RELEASE_VERSION': V, 'RELEASE_COMMIT': C}
URLS = {'Repository': 'https://github.com/TelemetryWorks/spatial-typestate',
        'Documentation': 'https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/PYTHON-GUIDE.md',
        'Issues': 'https://github.com/TelemetryWorks/spatial-typestate/issues'}
HEADER = 'Metadata-Version: 2.4\nName: spatial-typestate\nVersion: 9.8.7\nLicense-Expression: Apache-2.0\nLicense-File: LICENSE\n' + ''.join(f'Project-URL: {k}, {v}\n' for k, v in URLS.items())


def source():
    return {'git': {'base_commit': C, 'state': 'clean'}, 'versions': {'core': V, 'native': V, 'python': V},
            'sha256_lf': 'a' * 64, 'files': {}}


def package(directory):
    directory.mkdir(parents=True)
    for name in g.names(V):
        (directory / name).write_bytes(name.encode())
    record = {'version': V, 'commit': C, 'tag': 'v' + V, 'source': source(),
              'files': {n: g.digest(directory / n) for n in g.names(V)},
              'run_id': '42', 'run_attempt': 1, 'workflow': '.github/workflows/trusted-publishing.yml'}
    g.write_json(directory / 'release-manifest.json', record)
    g.checksums(directory)
    return record


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_tag_event_and_version_guards(self):
        g.context(V, C)
        for name, value in [('GITHUB_REPOSITORY', 'fork/repo'), ('GITHUB_EVENT_NAME', 'schedule'),
                            ('GITHUB_REF', 'refs/heads/main')]:
            with self.subTest(name=name), patch.dict(os.environ, {name: value}):
                with self.assertRaisesRegex(ValueError, 'original repository|version tag'):
                    g.context(V, C)
        for version in ('v1.2.3', '01.2.3', '1.2.3-rc1', '../1.2.3'):
            with self.assertRaisesRegex(ValueError, 'stable X.Y.Z'):
                g.names(version)
        with self.assertRaisesRegex(ValueError, 'original repository|version tag'):
            g.context(V, 'main')

    def source_fixture(self):
        for path, text in [('Cargo.toml', '[package]\nversion="9.8.7"\n'),
                           ('python/native/Cargo.toml', '[package]\nversion="9.8.7"\n'),
                           ('python/pyproject.toml', '[project]\nversion="9.8.7"\n'),
                           ('Cargo.lock', '[[package]]\nname="spatial-typestate"\nversion="9.8.7"\n'),
                           ('python/native/Cargo.lock', '[[package]]\nname="spatial-typestate"\nversion="9.8.7"\n')]:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        def git(*args, **kwargs):
            if args[1] == 'status':
                return ''
            if args[1] == 'ls-remote':
                return '2' * 40 + '\trefs/tags/v9.8.7\n' + C + '\trefs/tags/v9.8.7^{}'
            return C
        return git

    def test_source_versions_clean_tag_ancestry_and_inventory(self):
        git = self.source_fixture()
        with patch.object(g, 'ROOT', self.root), patch.object(g, 'run', side_effect=git), \
                patch.object(g.backend, 'source_record', return_value=(source(), 'checkout')), \
                patch.object(g.subprocess, 'run') as ancestry:
            self.assertEqual(g.source_guard(V, C), source())
            ancestry.assert_not_called()
            p = self.root / 'python/native/Cargo.toml'
            p.write_text('[package]\nversion="0.1.0"\n')
            with self.assertRaisesRegex(ValueError, 'match core, Python and native'):
                g.source_guard(V, C)
            p.write_text('[package]\nversion="9.8.7"\n')
            with patch.object(g, 'run', return_value='wrong'):
                with self.assertRaisesRegex(ValueError, 'clean triggering'):
                    g.source_guard(V, C)
            with patch.object(g.backend, 'source_record', return_value=(source(), 'sdist')):
                with self.assertRaisesRegex(ValueError, 'source inventory'):
                    g.source_guard(V, C)
            (self.root / 'Cargo.lock').write_text('[[package]]\nname="spatial-typestate"\nversion="1.0.0"\n')
            with self.assertRaisesRegex(ValueError, 'lockfile self-package'):
                g.source_guard(V, C)

    def test_manifest_checks_mutation_duplicates_paths_extra_files_and_run_identity(self):
        directory = self.root / 'release'
        record = package(directory)
        self.assertEqual(g.check(directory, V, C), record)
        for key, value in [('version', '1.0.0'), ('run_id', '43'), ('workflow', 'other.yml'),
                           ('files', {})]:
            bad = {**record, key: value}
            g.write_json(directory / g.MANIFEST, bad)
            g.checksums(directory)
            with self.assertRaises(ValueError):
                g.check(directory, V, C)
        g.write_json(directory / g.MANIFEST, record)
        g.checksums(directory)
        original = (directory / g.SUMS).read_text()
        for value in (original + original.splitlines()[0] + '\n', original + 'a' * 64 + '  ../escape\n'):
            (directory / g.SUMS).write_text(value)
            with self.assertRaisesRegex(ValueError, 'checksum manifest'):
                g.check(directory, V, C)
        (directory / g.SUMS).write_text(original)
        (directory / g.names(V)[0]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum/file set'):
            g.check(directory, V, C)
        g.checksums(directory)
        with self.assertRaisesRegex(ValueError, 'selected artifact differs'):
            g.check(directory, V, C)
        (directory / 'extra').mkdir()
        with self.assertRaisesRegex(ValueError, 'unsafe evidence'):
            g.checksums(directory)

    def test_public_urls_missing_bounds_and_no_redirect(self):
        for url in ['http://pypi.org/a', 'https://example.com/a', 'https://user@pypi.org/a',
                    'https://pypi.org:444/a', 'https://pypi.org/a#x']:
            with self.assertRaisesRegex(ValueError, 'unexpected public registry'):
                g.public(url)
        handler = g.NoRedirect()
        with self.assertRaisesRegex(ValueError, 'redirect refused'):
            handler.redirect_request(None, None, None, None, None, 'https://pypi.org/')
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"ok":true}'
        with patch.object(g.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(g.public_json('https://pypi.org/a'), {'ok': True})
            response.read.return_value = b'x' * 32_000_001
            with self.assertRaisesRegex(ValueError, 'exceeds bound'):
                g.public('https://pypi.org/a')
            opener.return_value.open.side_effect = urllib.error.HTTPError('https://pypi.org/a', 404, 'missing', None, None)
            self.assertIsNone(g.public_json('https://pypi.org/a', missing=True))
            with self.assertRaisesRegex(ValueError, 'HTTP status 404'):
                g.public('https://pypi.org/a')

    def test_absence_is_per_version_and_never_skip_existing(self):
        with patch.object(g, 'public_json', return_value=None) as read:
            g.absent(V)
            self.assertEqual(read.call_count, 2)
            self.assertTrue(all(V in c.args[0] for c in read.call_args_list))
        with patch.object(g, 'public_json', return_value={'files': []}):
            with self.assertRaisesRegex(ValueError, 'never republish'):
                g.absent(V, 'pypi')
        with patch.object(g, 'public_json', side_effect=[None, {'found': True}]), patch.object(g.time, 'sleep') as sleep:
            self.assertEqual(g.wait_json('https://pypi.org/a'), {'found': True})
            sleep.assert_called_once_with(5)
        with patch.object(g, 'public_json', return_value=None), patch.object(g.time, 'sleep') as sleep:
            with self.assertRaisesRegex(ValueError, 'never repeat upload'):
                g.wait_json('https://pypi.org/a')
            self.assertEqual(sleep.call_count, 5)

    def make_crate(self, changes=None):
        files = {'Cargo.toml': b'[package]\nversion="9.8.7"\n',
                 '.cargo_vcs_info.json': json.dumps({'git': {'sha1': C}}).encode(),
                 'Cargo.toml.orig': b'original', 'src/lib.rs': b'core'}
        files.update(changes or {})
        (self.root / 'Cargo.toml').write_bytes(b'original')
        (self.root / 'src').mkdir(exist_ok=True)
        (self.root / 'src/lib.rs').write_bytes(b'core')
        path = self.root / 'fixture.crate'
        with tarfile.open(path, 'w:gz') as archive:
            for name, raw in files.items():
                entry = tarfile.TarInfo('spatial-typestate-9.8.7/' + name)
                entry.size = len(raw)
                archive.addfile(entry, io.BytesIO(raw))
        return path

    def test_crate_identity_source_bytes_and_unsafe_archive(self):
        with patch.object(g, 'ROOT', self.root):
            g.crate_check(self.make_crate(), V, C)
            for change, message in [({'.cargo_vcs_info.json': json.dumps({'git': {'sha1': C, 'dirty': True}}).encode()}, 'identity'),
                                    ({'src/lib.rs': b'bad'}, 'source differs'),
                                    ({'src/extra.rs': b'bad'}, 'source set'),
                                    ({'../escape': b'bad'}, 'invalid crate')]:
                path = self.make_crate(change)
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    g.crate_check(path, V, C)

    def test_public_crate_checksum_trust_and_fresh_bytes(self):
        directory = self.root / 'release'
        record = package(directory)
        raw = (directory / g.names(V)[0]).read_bytes()
        data = {'checksum': record['files'][g.names(V)[0]], 'yanked': False,
                'trustpub_data': {'provider': 'github', 'repository': g.REPOSITORY, 'run_id': '42', 'sha': C}}
        index = json.dumps({'vers': V, 'cksum': data['checksum'], 'yanked': False}).encode()
        with patch.object(g, 'wait_json', return_value={'version': data}), patch.object(g, 'public', side_effect=[index, raw]):
            g.crate_public(directory, record)
        for key, value in [('checksum', 'bad'), ('yanked', True), ('trustpub_data', {})]:
            with patch.object(g, 'wait_json', return_value={'version': {**data, key: value}}):
                with self.assertRaisesRegex(ValueError, 'Trusted Publisher identity'):
                    g.crate_public(directory, record)
        with patch.object(g, 'wait_json', return_value={'version': data}), patch.object(g, 'public', return_value=b''):
            with self.assertRaisesRegex(ValueError, 'index mismatch'):
                g.crate_public(directory, record)
        with patch.object(g, 'wait_json', return_value={'version': data}), patch.object(g, 'public', side_effect=[index, b'bad']):
            with self.assertRaisesRegex(ValueError, 'published crate bytes'):
                g.crate_public(directory, record)

    def pypi_data(self, record):
        return {'info': {'name': 'spatial-typestate', 'version': V, 'license_expression': 'Apache-2.0', 'license_files': ['LICENSE'],
                         'project_urls': URLS, 'requires_python': '<3.15,>=3.11'},
                'urls': [{'filename': n, 'digests': {'sha256': record['files'][n]}, 'yanked': False,
                          'url': 'https://files.pythonhosted.org/' + n} for n in g.names(V)[1:]]}

    def test_pypi_public_all_three_files_metadata_hashes_and_integrity_objects(self):
        directory = self.root / 'release'
        record = package(directory)
        data = self.pypi_data(record)
        with patch.object(g, 'wait_json', side_effect=[data, {'proof': 1}, {'proof': 2}, {'proof': 3}]), \
                patch.object(g, 'public', side_effect=lambda u: (directory / u.rsplit('/', 1)[1]).read_bytes()):
            g.pypi_public(directory, record)
        self.assertEqual(len(list(directory.glob('*.pypi-provenance.json'))), 3)
        for key, value in [('license_expression', None), ('license_files', None), ('project_urls', None), ('requires_python', '>=3.10')]:
            bad = copy.deepcopy(data)
            bad['info'][key] = value
            with self.subTest(key=key), patch.object(g, 'wait_json', return_value=bad):
                with self.assertRaisesRegex(ValueError, 'file set or licence/URL'):
                    g.pypi_public(directory, record)
        for changes, error in [({'yanked': True}, 'digest/yanked'), ({'digests': {'sha256': 'bad'}}, 'digest/yanked')]:
            bad = copy.deepcopy(data)
            bad['urls'][0].update(changes)
            with patch.object(g, 'wait_json', return_value=bad):
                with self.assertRaisesRegex(ValueError, error):
                    g.pypi_public(directory, record)
        with patch.object(g, 'wait_json', return_value=data), patch.object(g, 'public', return_value=b'bad'):
            with self.assertRaisesRegex(ValueError, 'fresh PyPI file'):
                g.pypi_public(directory, record)

    def test_integrity_claims_exact_not_merely_repository(self):
        uri = 'https://github.com/TelemetryWorks/spatial-typestate'
        claims = {integrity.OID + key: value for key, value in {
            '8': 'https://token.actions.githubusercontent.com', '9': uri + '/' + g.WORKFLOW + '@refs/tags/v' + V,
            '10': C, '11': 'github-hosted', '12': uri, '13': C, '14': 'refs/tags/v' + V,
            '18': uri + '/' + g.WORKFLOW + '@refs/tags/v' + V, '19': C}.items()}
        integrity.verify_claims(claims, V, C)
        for key in claims:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'certificate issuer/repository'):
                integrity.verify_claims({**claims, key: 'bad'}, V, C)

    def test_integrity_cryptographic_verification_precedes_claims_and_never_accepts_other_predicate(self):
        wheel = Path(g.names(V)[1])
        publisher = {'repository': g.REPOSITORY, 'workflow': 'trusted-publishing.yml', 'environment': 'pypi'}
        att = Mock()
        att.verify.return_value = (integrity.PREDICATE, {})
        att.to_bundle.return_value.to_json.return_value = '{"verified":true}'
        group = types.SimpleNamespace(publisher=publisher, attestations=[att])
        library = types.SimpleNamespace(Distribution=Mock(), GitHubPublisher=lambda **k: k,
                                        Provenance=Mock())
        library.Provenance.model_validate.return_value.attestation_bundles = [group]
        with patch.dict(sys.modules, {'pypi_attestations': library}), patch.object(integrity, 'verify_claims') as claims:
            self.assertEqual(integrity.verify_file(wheel, {}, V, C), ['{"verified":true}'])
            att.verify.assert_called_once()
            claims.assert_called_once()
            att.verify.side_effect = ValueError('invalid signature')
            claims.reset_mock()
            with self.assertRaisesRegex(ValueError, 'invalid signature'):
                integrity.verify_file(wheel, {}, V, C)
            claims.assert_not_called()
            att.verify.side_effect = None
            att.verify.return_value = ('https://slsa.dev/provenance/v1', {})
            with self.assertRaisesRegex(ValueError, 'PEP 740 publish'):
                integrity.verify_file(wheel, {}, V, C)
            group.publisher = {'environment': 'other'}
            with self.assertRaisesRegex(ValueError, 'Publisher/environment'):
                integrity.verify_file(wheel, {}, V, C)
            library.Provenance.model_validate.return_value.attestation_bundles = []
            with self.assertRaisesRegex(ValueError, 'no bundles'):
                integrity.verify_file(wheel, {}, V, C)

    def test_each_integrity_file_retained_and_missing_file_fails(self):
        directory = self.root / 'release'
        package(directory)
        for name in g.names(V)[1:]:
            g.write_json(directory / (name + '.pypi-provenance.json'), {'proof': name})
        g.checksums(directory)
        with patch.object(integrity, 'verify_file', return_value=['{}']) as verify:
            result = integrity.verify(directory, V, C, offline=True)
            self.assertEqual(set(result), set(g.names(V)[1:]))
            self.assertEqual(verify.call_count, 3)
        g.checksums(directory)
        (directory / (g.names(V)[1] + '.pypi-provenance.json')).unlink()
        g.checksums(directory)
        with self.assertRaises(FileNotFoundError):
            integrity.verify(directory, V, C)

    def test_workflow_order_privileges_tag_only_and_compiler_pins(self):
        workflow = (HERE.parent / 'workflows/trusted-publishing.yml').read_text()
        self.assertIn("tags: ['v*']", workflow)
        for forbidden in ('password:', 'attestations: false', '--allow-dirty'):
            self.assertNotIn(forbidden, workflow)
        self.assertIn('needs: [gate, build, publish-crates]', workflow)
        self.assertIn('needs: [gate, publish-crates, publish-pypi]', workflow)
        self.assertEqual(workflow.count('id-token: write'), 4)
        self.assertEqual(workflow.count('contents: write'), 1)
        self.assertNotIn('set-default', workflow)
        self.assertIn('attestations: true', workflow)
        builder = (HERE.parent / 'workflows/build-release.yml').read_text()
        self.assertIn("toolchain: '1.99.0'", builder)
        self.assertIn('for compiler in 1.85.0 1.91.1', builder)

    def staged_fixture(self):
        incoming = self.root / 'incoming'
        for group in ('verified-crate', 'verified-python-ubuntu-latest-3.11',
                      'verified-python-windows-latest-3.11', 'windows-consumer-3.11', 'windows-consumer-3.14'):
            (incoming / group).mkdir(parents=True)
        shutil.copyfile(self.make_crate(), incoming / 'verified-crate' / g.names(V)[0])
        for index, group in [(1, 'ubuntu'), (2, 'windows')]:
            path = incoming / f'verified-python-{group}-latest-3.11' / g.names(V)[index]
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('spatial_typestate-9.8.7.dist-info/METADATA', HEADER)
                archive.writestr('spatial_typestate/_provenance.json', json.dumps({'source': source(), 'source_origin': 'checkout'}))
        path = incoming / 'verified-python-ubuntu-latest-3.11' / g.names(V)[3]
        with tarfile.open(path, 'w:gz') as archive:
            raw = json.dumps({'source': source()}).encode()
            entry = tarfile.TarInfo('spatial_typestate-9.8.7/python/spatial_typestate/_provenance.json')
            entry.size = len(raw)
            archive.addfile(entry, io.BytesIO(raw))
        linux = incoming / 'verified-python-ubuntu-latest-3.11'
        g.write_json(linux / 'runtime-evidence.json', [
            {'python': py + '.10 build', 'glibc': glibc, 'sha256': g.digest(linux / g.names(V)[1])}
            for py in ('3.11', '3.14') for glibc in ('2.28', '2.36')])
        windows = incoming / 'verified-python-windows-latest-3.11'
        for py in ('3.11', '3.14'):
            g.write_json(incoming / ('windows-consumer-' + py) / 'windows-consumer.json',
                         {'sha256': g.digest(windows / g.names(V)[2]), 'commit': C, 'python': py + '.10'})
        for name in ('core.cdx.json', 'python.cdx.json'):
            g.write_json(incoming / 'verified-crate' / name, {'bomFormat': 'CycloneDX'})
        return incoming

    def test_final_selection_checks_real_headers_source_canonical_names_and_runtime_receipts(self):
        incoming = self.staged_fixture()
        with patch.object(g, 'ROOT', self.root), patch.object(g, 'source_guard', return_value=source()), \
                patch.object(g.artifacts, 'wheel_report') as wheel, patch.object(g.artifacts, 'sdist_report') as sdist:
            destination = self.root / 'release'
            g.stage(incoming, destination, V, C)
            self.assertEqual(wheel.call_count, 2)
            sdist.assert_called_once()
            record = g.check(destination, V, C)
            self.assertEqual(set(record['files']), set(g.names(V)))
            runtime = incoming / 'verified-python-ubuntu-latest-3.11/runtime-evidence.json'
            data = json.loads(runtime.read_text())
            g.write_json(runtime, data[:3])
            with self.assertRaisesRegex(ValueError, 'four runtime records'):
                g.stage(incoming, self.root / 'bad-runtime', V, C)
            g.write_json(runtime, data)
            receipt = incoming / 'windows-consumer-3.14/windows-consumer.json'
            g.write_json(receipt, {'sha256': 'bad', 'commit': C, 'python': '3.14.10'})
            with self.assertRaisesRegex(ValueError, 'Windows consumers'):
                g.stage(incoming, self.root / 'bad-consumer', V, C)
            (incoming / 'verified-python-windows-latest-3.11' / g.names(V)[2]).unlink()
            with self.assertRaisesRegex(ValueError, 'selected artifact missing'):
                g.stage(incoming, self.root / 'missing-wheel', V, C)

    def test_final_selection_rejects_wrong_source_even_when_archive_validators_return_success(self):
        incoming = self.staged_fixture()
        wheel = incoming / 'verified-python-windows-latest-3.11' / g.names(V)[2]
        with zipfile.ZipFile(wheel, 'w') as archive:
            archive.writestr('spatial_typestate-9.8.7.dist-info/METADATA', HEADER)
            archive.writestr('spatial_typestate/_provenance.json', json.dumps({'source': {}, 'source_origin': 'checkout'}))
        with patch.object(g, 'ROOT', self.root), patch.object(g, 'source_guard', return_value=source()), \
                patch.object(g.artifacts, 'wheel_report'), patch.object(g.artifacts, 'sdist_report'):
            with self.assertRaisesRegex(ValueError, 'wheel source/version differs'):
                g.stage(incoming, self.root / 'bad', V, C)

    def test_installed_same_bytes_checked_before_install_both_suites_and_lab(self):
        directory = self.root / 'selected'
        directory.mkdir()
        wheel = directory / g.names(V)[2]
        wheel.write_bytes(b'wheel fixture')
        g.write_json(directory / 'artifact-inventory.json', [{'filename': wheel.name, 'sha256': g.digest(wheel)}])
        output = directory / 'consumer.json'
        probe = {'version': V, 'record': {'source': source()}}
        with patch.object(g.artifacts, 'wheel_report'), patch.object(g, 'run', return_value=json.dumps(probe)), \
                patch.object(g.subprocess, 'run') as commands:
            g.installed(wheel, V, C, output)
            self.assertEqual(json.loads(output.read_text())['sha256'], g.digest(wheel))
            self.assertEqual(sum('unittest' in c.args[0] for c in commands.call_args_list), 2)
            self.assertTrue(any('--demonstrate-errors' in c.args[0] for c in commands.call_args_list))
            self.assertTrue(all(Path(c.kwargs['cwd']).is_relative_to(Path(tempfile.gettempdir()))
                                for c in commands.call_args_list if 'cwd' in c.kwargs))
            with patch.object(g, 'run', return_value=json.dumps({**probe, 'version': 'bad'})):
                with self.assertRaisesRegex(ValueError, 'installed wheel identity'):
                    g.installed(wheel, V, C, output)
            wheel.write_bytes(b'altered')
            commands.reset_mock()
            with self.assertRaisesRegex(ValueError, 'hash differs from build inventory'):
                g.installed(wheel, V, C, output)
            commands.assert_not_called()

    def test_evidence_merge_requires_both_publications_and_all_per_file_proofs(self):
        incoming = self.root / 'incoming'
        for group in ('crates-evidence', 'pypi-evidence'):
            package(incoming / group)
        core = incoming / 'crates-evidence'
        python = incoming / 'pypi-evidence'
        for name in ('crates-public.json', 'crate.provenance.sigstore.json', 'crate.sbom.sigstore.json'):
            g.write_json(core / name, {})
        for name in ('pypi-public.json', 'pypi-integrity-verified.json', 'python.provenance.sigstore.json', 'python.sbom.sigstore.json'):
            g.write_json(python / name, {})
        for name in g.names(V)[1:]:
            for suffix in ('.pypi-provenance.json', '.publish-0.sigstore.json'):
                g.write_json(python / (name + suffix), {})
        for directory in (core, python):
            g.checksums(directory)
        g.merge_evidence(incoming, self.root / 'merged', V, C)
        g.check(self.root / 'merged', V, C)
        (python / 'pypi-integrity-verified.json').unlink()
        g.checksums(python)
        with self.assertRaisesRegex(ValueError, 'publication evidence incomplete'):
            g.merge_evidence(incoming, self.root / 'missing', V, C)
        for directory, raw in [(core, 'one'), (python, 'other')]:
            (directory / 'shared.json').write_text(raw)
            g.checksums(directory)
        with self.assertRaisesRegex(ValueError, 'conflicting evidence'):
            g.merge_evidence(incoming, self.root / 'conflict', V, C)

    def test_release_assets_draft_retains_identical_files_and_never_overwrites(self):
        directory = self.root / 'release'
        record = package(directory)
        existing = {'draft': True, 'assets': [{'name': 'SHA256SUMS'}]}
        created = False
        commands = []
        def api(path, missing=False):
            if '/git/ref/' in path:
                return {'object': {'type': 'tag', 'sha': '2' * 40}}
            if '/git/tags/' in path:
                return {'object': {'type': 'commit', 'sha': C}}
            return copy.deepcopy(existing) if created else None
        def command(args, **kwargs):
            nonlocal created
            commands.append(args)
            if args[2] == 'create':
                created = True
            elif args[2] == 'download':
                shutil.copyfile(directory / args[args.index('--pattern') + 1], Path(args[args.index('--dir') + 1]) / 'SHA256SUMS')
            elif args[2] == 'upload':
                existing['assets'].append({'name': Path(args[-1]).name})
        with patch.object(g, 'gh_json', side_effect=api), patch.object(g.subprocess, 'run', side_effect=command):
            g.release_assets(directory, record)
        self.assertEqual({a['name'] for a in existing['assets']}, {p.name for p in directory.iterdir()})
        self.assertTrue(any(c[2] == 'create' and '--draft' in c and '--verify-tag' in c for c in commands))
        self.assertEqual(commands[-1][2], 'edit')
        self.assertTrue(all('--clobber' not in c for c in commands))
        with patch.object(g, 'gh_json', return_value={'object': {'type': 'commit', 'sha': 'bad'}}), \
                patch.object(g.subprocess, 'run') as mutation:
            with self.assertRaisesRegex(ValueError, 'remote release tag differs'):
                g.release_assets(directory, record)
            mutation.assert_not_called()
        existing['assets'].append({'name': 'unreviewed'})
        with patch.object(g, 'gh_json', side_effect=api), patch.object(g.subprocess, 'run') as mutation:
            with self.assertRaisesRegex(ValueError, 'unexpected assets'):
                g.release_assets(directory, record)
            mutation.assert_not_called()
        existing['assets'].pop()
        def corrupt(args, **kwargs):
            if args[2] == 'download':
                (Path(args[args.index('--dir') + 1]) / args[args.index('--pattern') + 1]).write_bytes(b'bad')
        with patch.object(g, 'gh_json', side_effect=api), patch.object(g.subprocess, 'run', side_effect=corrupt) as mutation:
            with self.assertRaisesRegex(ValueError, 'existing release asset differs'):
                g.release_assets(directory, record)
            self.assertFalse(any(c.args[0][2] == 'upload' for c in mutation.call_args_list))

    def test_github_read_errors_never_masquerade_as_absence(self):
        with patch.object(g.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='{"ok":true}')):
            self.assertEqual(g.gh_json('path'), {'ok': True})
        for status in ('404', '503'):
            result = types.SimpleNamespace(returncode=1, stderr=f'gh: request failed (HTTP {status})')
            with patch.object(g.subprocess, 'run', return_value=result):
                if status == '404':
                    self.assertIsNone(g.gh_json('path', missing=True))
                else:
                    with self.assertRaisesRegex(ValueError, 'no release mutation'):
                        g.gh_json('path', missing=True)

    def test_cli_wiring_and_integrity_cli(self):
        output = self.root / 'outputs'
        output.touch()
        functions = ['source_guard', 'absent', 'check', 'stage', 'installed', 'checksums', 'merge_evidence',
                     'crate_public', 'pypi_public', 'release_assets']
        cases = {'source': 'source_guard', 'absent': 'absent', 'check': 'check', 'stage': 'stage',
                 'installed': 'installed', 'sums': 'checksums', 'merge': 'merge_evidence',
                 'crate-public': 'crate_public', 'pypi-public': 'pypi_public', 'assets': 'release_assets'}
        with ExitStack() as stack:
            mocks = {name: stack.enter_context(patch.object(g, name, return_value={})) for name in functions}
            stack.enter_context(patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}))
            for mode, called in cases.items():
                for m in mocks.values():
                    m.reset_mock()
                with patch.object(sys, 'argv', ['release_guard.py', mode, '--wheel', str(output)]):
                    g.main()
                mocks[called].assert_called_once()
        with patch.object(integrity, 'verify') as verify, patch.object(sys, 'argv',
                 ['release_integrity.py', str(self.root), '--version', V, '--commit', C, '--offline']):
            integrity.main()
            verify.assert_called_once_with(self.root, V, C, True)


if __name__ == '__main__':
    unittest.main()

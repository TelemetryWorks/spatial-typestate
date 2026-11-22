"""Independent historical PyPI pins and read-only known-good negative tests."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_pipeline as p
import release_guard as g

PINS = {
    'spatial_typestate-0.1.0-cp311-abi3-manylinux_2_28_x86_64.whl': 'e591cc87071cdc7db9e1ff162d11d661f1e6854ab1c6cfbf96473cde7e57ebd5',
    'spatial_typestate-0.1.0-cp311-abi3-win_amd64.whl': 'b59ead8787b870d28f0aba2b7bd8264a993e2dfa93ca3fa9d3a5d249254c12c8',
    'spatial_typestate-0.1.0.tar.gz': 'd94f841d8ab4368de4994b071f9d035fe5260feba2e50157200a9467d51e9448',
}


class PythonKnownGoodTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        directory = self.root / '.github/release-fixtures'
        directory.mkdir(parents=True)
        self.file = directory / 'spatial-typestate-python-0.1.0.sha256'
        self.raw = {name: ('fixture ' + name).encode() for name in PINS}
        self.expected = {name: hashlib.sha256(raw).hexdigest() for name, raw in self.raw.items()}
        self.file.write_text(''.join(f'{sha}  {name}\n' for name, sha in sorted(self.expected.items())))
        self.data = {'info': {'name': 'spatial-typestate', 'version': '0.1.0'}, 'urls': [
            {'filename': name, 'yanked': False, 'digests': {'sha256': self.expected[name]},
             'url': 'https://files.pythonhosted.org/packages/example/' + name} for name in PINS]}

    def test_actual_committed_pins_match_independently_reviewed_historical_bytes(self):
        self.assertEqual(p.KNOWN_PYTHON, PINS)
        text = (g.ROOT / '.github/release-fixtures/spatial-typestate-python-0.1.0.sha256').read_text()
        self.assertEqual(text, ''.join(f'{sha}  {name}\n' for name, sha in sorted(PINS.items())))

    def test_downloads_every_file_from_json_urls_and_checks_independent_digests(self):
        responses = {item['url']: self.raw[item['filename']] for item in self.data['urls']}
        with patch.object(g, 'ROOT', self.root), patch.object(p, 'KNOWN_PYTHON', self.expected), \
                patch.object(g, 'public_json', return_value=self.data) as api, \
                patch.object(g, 'public', side_effect=lambda url: responses[url]) as download, \
                patch.object(p, 'print') as output:
            p.known_good_python()
            api.assert_called_once_with('https://pypi.org/pypi/spatial-typestate/0.1.0/json')
            self.assertEqual({call.args[0] for call in download.call_args_list}, set(responses))
            self.assertEqual(download.call_count, 3)
            self.assertIn('PEP 740 NOT exercised', output.call_args.args[0])

    def test_changed_download_cannot_pass_matching_json_digest(self):
        for bad in self.raw:
            responses = {item['url']: self.raw[item['filename']] + (b'changed' if item['filename'] == bad else b'')
                         for item in self.data['urls']}
            with self.subTest(bad=bad), patch.object(g, 'ROOT', self.root), patch.object(p, 'KNOWN_PYTHON', self.expected), \
                    patch.object(g, 'public_json', return_value=self.data), patch.object(g, 'public', side_effect=lambda url: responses[url]):
                with self.assertRaisesRegex(ValueError, 'downloaded bytes mismatch'):
                    p.known_good_python()

    def test_json_identity_files_yanks_digests_and_host_fail_closed(self):
        for mutation, error in [('name', 'identity/file set'), ('version', 'identity/file set'),
                                ('missing', 'identity/file set'), ('duplicate', 'identity/file set'),
                                ('extra', 'identity/file set'), ('yanked', 'digest/yank'),
                                ('digest', 'digest/yank'), ('host', 'download host')]:
            data = copy.deepcopy(self.data)
            if mutation in ('name', 'version'):
                data['info'][mutation] = 'wrong'
            elif mutation == 'missing':
                data['urls'].pop()
            elif mutation == 'duplicate':
                data['urls'].append(data['urls'][0])
            elif mutation == 'extra':
                data['urls'].append(dict(data['urls'][0], filename='extra.whl'))
            elif mutation == 'yanked':
                data['urls'][0]['yanked'] = True
            elif mutation == 'digest':
                data['urls'][0]['digests']['sha256'] = '0'*64
            elif mutation == 'host':
                data['urls'][0]['url'] = 'https://attacker.invalid/file'
            with self.subTest(mutation=mutation), patch.object(g, 'ROOT', self.root), patch.object(p, 'KNOWN_PYTHON', self.expected), \
                    patch.object(g, 'public_json', return_value=data), patch.object(g, 'public') as download:
                with self.assertRaisesRegex(ValueError, error):
                    p.known_good_python()
                download.assert_not_called()

    def test_fixture_mutation_blocks_api_and_workflow_runs_python_known_good(self):
        self.file.write_text('untrusted')
        with patch.object(g, 'ROOT', self.root), patch.object(p, 'KNOWN_PYTHON', self.expected), patch.object(g, 'public_json') as api:
            with self.assertRaisesRegex(ValueError, 'trusted Python known-good fixture changed'):
                p.known_good_python()
            api.assert_not_called()
        workflow = (g.ROOT / '.github/workflows/trusted-publishing.yml').read_text()
        dry = workflow.split('\n  publish-path-check:\n')[1].split('\n  publish-crates:\n')[0]
        self.assertIn('python3 -I .github/scripts/release_pipeline.py known-good-python', dry)


if __name__ == '__main__':
    unittest.main()

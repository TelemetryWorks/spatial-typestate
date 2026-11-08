"""Publication guard, registry identity and no-substitution tests; no uploads."""
import copy
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import urllib.error


spec = importlib.util.spec_from_file_location("publication", Path(__file__).with_name("publish_qualified.py"))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def environment():
    return {"GITHUB_ACTIONS": "true", "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1",
            "PUBLICATION_GUARD": "approved-9974fd6-once", "CARGO_PRESENT": "true", "PYPI_PRESENT": "true"}


def release():
    return {"info": {"name": p.PROJECT, "version": "0.1.0", "requires_python": ">=3.11,<3.15"},
            "urls": [{"filename": n, "digests": {"sha256": h}, "yanked": False,
                      "url": "https://files.pythonhosted.org/packages/fixture/" + n}
                     for n, h in p.PYTHON_FILES.items()]}


class GuardTests(unittest.TestCase):
    def test_matching_cargo_guard_validates_archive_then_rechecks_clean_source(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with (mock.patch.object(p.q, "validate_source") as clean,
                  mock.patch.object(p.q, "execute") as execute,
                  mock.patch.object(p.q, "sha", return_value=p.CRATE_SHA),
                  mock.patch('tarfile.open'),
                  mock.patch.object(p.q, "archive_files", return_value={".cargo_vcs_info.json": b'{"git":{"sha1":"fixture"}}'}),
                  mock.patch.object(p.q, "validate_crate") as validate):
                self.assertEqual(p.package_guard(root, root)['sha256'], p.CRATE_SHA)
            self.assertEqual(clean.call_count, 2)
            validate.assert_called_once()
            self.assertEqual(execute.call_args.args[0][:5], ['cargo', p.q.TOOLCHAIN, 'package', '--locked', '--jobs'])

    def test_every_dispatch_and_credential_presence_gate(self):
        with mock.patch.dict(os.environ, environment(), clear=True):
            p.gate()
        for key in environment():
            values = environment()
            values[key] = "wrong"
            with mock.patch.dict(os.environ, values, clear=True):
                with self.assertRaises(ValueError):
                    p.gate()

    def test_existing_registry_version_or_owner_blocks_before_staging(self):
        owner = {"users": [{"login": p.OWNER}]}
        for data in ({"versions": [{"num": "0.1.0"}]}, {"versions": [{"num": "0.0.1"}]}):
            with mock.patch.object(p, "public_json", side_effect=[data, {"users": [{"login": "foreign"}]}]):
                with self.assertRaises(ValueError):
                    p.rust_absent()
        with mock.patch.object(p, "public_json", side_effect=[{"versions": [{"num": "0.0.1"}]}, owner, None]):
            p.all_absent()
        with mock.patch.object(p, "public_json", side_effect=[{"versions": []}, owner, {}]):
            with self.assertRaisesRegex(ValueError, "PyPI project exists"):
                p.all_absent()

    def test_selected_filenames_and_hashes_checked_before_destination_creation(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            destination = root / "publish-dist"
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                p.stage_python(root, destination)
            self.assertFalse(destination.exists())
            payloads = {n: n.encode() for n in p.PYTHON_FILES}
            for n, raw in payloads.items():
                path = root / ("source-windows" if n == p.q.WHEEL else "source-ubuntu") / n
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(raw)
            expected = {n: hashlib.sha256(b).hexdigest() for n, b in payloads.items()}
            with mock.patch.object(p, "PYTHON_FILES", expected):
                p.stage_python(root, destination)
            self.assertEqual({f.name for f in destination.iterdir()}, set(payloads))
            for n, raw in payloads.items():
                self.assertEqual((destination / n).read_bytes(), raw)

    def test_cargo_guard_hash_mismatch_cannot_be_treated_as_publishable(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            archive = root / "publication-cargo-target/package" / p.CRATE
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"not the qualified archive")
            with mock.patch.object(p.q, "validate_source"), mock.patch.object(p.q, "execute") as execute:
                with self.assertRaisesRegex(ValueError, "do not publish"):
                    p.package_guard(root, root)
            self.assertNotIn("publish", execute.call_args.args[0])
            self.assertIn("--locked", execute.call_args.args[0])
            self.assertNotIn("--allow-dirty", execute.call_args.args[0])


class PublicTransportTests(unittest.TestCase):
    def test_foreign_host_scheme_userinfo_port_and_redirect_fail(self):
        for url in ("http://pypi.org/x", "https://evil.example/x", "https://user@pypi.org/x",
                    "https://pypi.org:444/x", "https://pypi.org/x#fragment"):
            with mock.patch.object(p.urllib.request, "build_opener") as opener:
                with self.assertRaises(ValueError):
                    p.public(url)
                opener.assert_not_called()
        with self.assertRaisesRegex(ValueError, "redirect"):
            p.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://pypi.org/x")

    def test_response_cap_missing_and_error_statuses(self):
        for raw, expected in ((b"public", b"public"), (b"x" * 4_000_001, None)):
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = raw
            opener = mock.Mock()
            opener.open.return_value = response
            with mock.patch.object(p.urllib.request, "build_opener", return_value=opener):
                if expected is None:
                    with self.assertRaisesRegex(ValueError, "too large"):
                        p.public(p.PYPI)
                else:
                    self.assertEqual(p.public(p.PYPI), expected)
        for code in (401, 403, 404, 500):
            error = urllib.error.HTTPError(p.PYPI, code, "private body", {}, io.BytesIO(b"do not echo"))
            opener = mock.Mock()
            opener.open.side_effect = error
            with mock.patch.object(p.urllib.request, "build_opener", return_value=opener):
                if code == 404:
                    self.assertIsNone(p.public(p.PYPI, missing=True))
                else:
                    with self.assertRaisesRegex(ValueError, str(code)):
                        p.public(p.PYPI, missing=True)
        with mock.patch.object(p, "public", return_value=b'{"public":true}'):
            self.assertEqual(p.public_json(p.PYPI), {"public": True})
        with mock.patch.object(p, "public", return_value=None):
            self.assertIsNone(p.public_json(p.PYPI, missing=True))


class RegistryEvidenceTests(unittest.TestCase):
    def test_installed_bytes_come_from_public_download_in_clean_venv(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            raw = b'public wheel fixture'
            digest = hashlib.sha256(raw).hexdigest()
            for platform, filename in [('win32', p.q.WHEEL), ('linux', p.LINUX)]:
                with (mock.patch.object(p.sys, 'platform', platform),
                      mock.patch.object(p, 'wait_python', return_value={filename: {'url': 'https://files.pythonhosted.org/fixture'}}),
                      mock.patch.object(p, 'public', return_value=raw),
                      mock.patch.object(p, 'PYTHON_FILES', {filename: digest}),
                      mock.patch.object(p.venv, 'EnvBuilder') as builder,
                      mock.patch.object(p.q, 'copy_test_assets'),
                      mock.patch.object(p.q, 'execute') as execute,
                      mock.patch.object(p.q, 'installed_probe', return_value={'fixture': True}),
                      mock.patch.object(p.q, 'installed_suite') as suite):
                    result = p.installed(root, root)
                self.assertEqual(result['sha256'], digest)
                builder.assert_called_once_with(with_pip=True, system_site_packages=False)
                self.assertEqual(execute.call_args.args[0][1:-1], ['-m','pip','--isolated','install','--no-deps'])
                self.assertEqual(execute.call_args.args[0][-1].name, filename)
                self.assertEqual(suite.call_args.args[2].name, 'cwd')
            with mock.patch.object(p, 'wait_python', return_value={p.q.WHEEL:{'url':'https://files.pythonhosted.org/fixture'}}), mock.patch.object(p.sys,'platform','win32'), mock.patch.object(p,'public',return_value=b'wrong'):
                with self.assertRaisesRegex(ValueError,'public wheel hash differs'):
                    p.installed(root,root)

    def test_registry_consumers_use_exact_version_and_checksum_not_path(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            calls=[]
            def execute(args,cwd,log):
                calls.append(args)
                if 'generate-lockfile' in args:
                    (cwd/'Cargo.lock').write_text('[[package]]\nname="spatial-typestate"\nversion="0.1.0"\nsource='+json.dumps(p.REGISTRY)+'\nchecksum='+json.dumps(p.CRATE_SHA)+'\n')
                return json.dumps({'packages':[{'name':p.PROJECT,'version':'0.1.0','source':p.REGISTRY}]})
            with mock.patch.object(p.q,'execute',side_effect=execute):
                self.assertTrue(p.registry_consumer(root,root)['binaries_use_std'])
            self.assertEqual(sum('run' in call for call in calls),2)
            with mock.patch.object(p.q,'execute',return_value=json.dumps({'packages':[{'name':p.PROJECT,'version':'0.1.0','source':None}]})):
                with self.assertRaisesRegex(ValueError,'public registry crate'):
                    p.registry_consumer(root,root)

    def test_pypi_exact_identity_floor_file_set_digests_and_yanked(self):
        data = release()
        with mock.patch.object(p, "public_json", return_value=data):
            self.assertEqual(set(p.python_release()), set(p.PYTHON_FILES))
        with mock.patch.object(p, "public_json", return_value=None):
            self.assertIsNone(p.python_release())
        mutations = []
        for key, value in (("name", "foreign"), ("version", "0.1.1"), ("requires_python", ">=3.12,<3.15")):
            changed = copy.deepcopy(data)
            changed["info"][key] = value
            mutations.append(changed)
        for field, value in (("filename", "../foreign.whl"), ("digests", {"sha256": "0" * 64}), ("yanked", True)):
            changed = copy.deepcopy(data)
            changed["urls"][0][field] = value
            mutations.append(changed)
        mutations += [{**data, "urls": data["urls"][:-1]}, {**data, "urls": data["urls"] + data["urls"][:1]}]
        for changed in mutations:
            with mock.patch.object(p, "public_json", return_value=changed):
                with self.assertRaises(ValueError):
                    p.python_release()

    def test_propagation_polls_are_bounded_reads_not_upload_retries(self):
        with mock.patch.object(p, "python_release", side_effect=[None, {"public": True}]), mock.patch.object(p.time, "sleep") as sleep:
            self.assertEqual(p.wait_python(), {"public": True})
            sleep.assert_called_once_with(5)
        with mock.patch.object(p, "python_release", return_value=None) as read, mock.patch.object(p.time, "sleep") as sleep:
            with self.assertRaisesRegex(ValueError, "inspect public state"):
                p.wait_python()
            self.assertEqual(read.call_count, 6)
            self.assertEqual(sleep.call_count, 5)

    def test_fresh_downloads_must_equal_the_three_approved_files(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            data = {n: {"url": "https://files.pythonhosted.org/" + n, "digests": {"sha256": h}}
                    for n, h in p.PYTHON_FILES.items()}
            with mock.patch.object(p, "wait_python", return_value=data), mock.patch.object(p, "public", return_value=b"wrong"):
                with self.assertRaisesRegex(ValueError, "differs"):
                    p.verify_python(root)
            payloads = {n: n.encode() for n in data}
            expected = {n: hashlib.sha256(raw).hexdigest() for n, raw in payloads.items()}
            with (mock.patch.object(p, "wait_python", return_value=data),
                  mock.patch.object(p, "public", side_effect=lambda u: payloads[u.rsplit('/', 1)[1]]),
                  mock.patch.object(p, "PYTHON_FILES", expected)):
                self.assertEqual(p.verify_python(root), {n: d['digests']['sha256'] for n, d in data.items()})
            self.assertEqual({f.name for f in root.iterdir()}, set(data))

    def test_crate_index_checksum_download_and_failure_stop(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            raw = b"qualified fixture"
            expected = hashlib.sha256(raw).hexdigest()
            version = {"vers": "0.1.0", "cksum": expected, "yanked": False}
            with (mock.patch.object(p, "CRATE_SHA", expected),
                  mock.patch.object(p, "public", side_effect=[json.dumps(version).encode(), raw])):
                self.assertEqual(p.verify_crate(root)['sha256'], expected)
            self.assertEqual((root / p.CRATE).read_bytes(), raw)
            with mock.patch.object(p, "public", return_value=b'{"vers":"0.0.1"}'), mock.patch.object(p.time, "sleep"):
                with self.assertRaisesRegex(ValueError, "do not republish"):
                    p.verify_crate(root)
            with mock.patch.object(p, "public", side_effect=[json.dumps({**version, 'cksum': p.CRATE_SHA}).encode(), b"wrong"]):
                with self.assertRaisesRegex(ValueError, "any yank requires owner"):
                    p.verify_crate(root)


class RoutingTests(unittest.TestCase):
    def test_ordered_preflights_and_reports_never_read_or_print_tokens(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            (root/'qualified-crate').mkdir()
            (root/'qualified-crate'/p.CRATE).write_bytes(b'fixture')
            values={**environment(),'RUNNER_TEMP':str(root),'GITHUB_WORKSPACE':str(root),'GITHUB_SHA':'a'*40,
                    'CARGO_REGISTRY_TOKEN':'planted-private-token','PYPI_API_TOKEN':'planted-private-token'}
            modes=['preflight','stage-python','verify-python','crate-guard','verify-crate','installed','registry-consumer']
            events=[]
            def action(label):
                def run(*args):
                    events.append(label)
                    return {'fixture':label}
                return run
            with (mock.patch.dict(os.environ,values,clear=True),
                  mock.patch.object(p.q,'validate_source'), mock.patch.object(p.q,'sha',return_value=p.CRATE_SHA),
                  mock.patch.object(p,'all_absent',side_effect=action('absent')),
                  mock.patch.object(p,'stage_python',side_effect=action('stage')),
                  mock.patch.object(p,'package_guard',side_effect=action('package')),
                  mock.patch.object(p,'verify_python',side_effect=action('verify-python')),
                  mock.patch.object(p,'rust_absent',side_effect=action('rust-absent')),
                  mock.patch.object(p,'verify_crate',side_effect=action('verify-crate')),
                  mock.patch.object(p,'installed',side_effect=action('installed')),
                  mock.patch.object(p,'registry_consumer',side_effect=action('registry-consumer'))):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    for mode in modes:
                        with mock.patch.object(p.sys,'argv',['script',mode]):p.main()
                    with mock.patch.object(p.sys,'argv',['script','gate']):p.main()
                    with mock.patch.object(p.sys,'argv',['script','unknown']):
                        with self.assertRaisesRegex(ValueError,'unknown fixed'):p.main()
                self.assertNotIn('planted-private-token',output.getvalue())
            self.assertEqual(events[:3],['absent','stage','package'])
            self.assertEqual(events[6:9],['verify-python','rust-absent','package'])
            for mode in modes:
                raw=(root/'publication-evidence'/(mode+'.json')).read_text()
                self.assertNotIn('planted-private-token',raw)
                self.assertEqual(json.loads(raw)['source_commit'],p.q.SOURCE_COMMIT)

    def test_wrong_qualified_download_stops_before_package_and_uploads(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            values={**environment(),'RUNNER_TEMP':str(root),'GITHUB_WORKSPACE':str(root),'GITHUB_SHA':'a'*40}
            with (mock.patch.dict(os.environ,values,clear=True),mock.patch.object(p.sys,'argv',['script','preflight']),
                  mock.patch.object(p.q,'validate_source'),mock.patch.object(p,'all_absent'),
                  mock.patch.object(p,'package_guard') as package):
                with self.assertRaisesRegex(ValueError,'qualified crate download differs'):p.main()
                package.assert_not_called()


if __name__ == "__main__":
    unittest.main()

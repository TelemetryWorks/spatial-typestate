"""Frozen artifact identity, extraction and installed-consumer boundary tests."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile


SCRIPT = Path(__file__).with_name("candidate_qualification.py")
spec = importlib.util.spec_from_file_location("qualification", SCRIPT)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def provenance():
    return {"source": {"git": {"base_commit": q.SOURCE_COMMIT, "state": "clean"},
                       "versions": {k: q.VERSION for k in ("core", "native", "python")},
                       "sha256_lf": q.SOURCE_IDENTITY}, "source_origin": "checkout"}


def fixture(root):
    raw = {"Cargo.toml": b'[package]\nname="spatial-typestate"\nversion="0.1.0"\n',
           "Cargo.lock": b"lock fixture\n", "README.md": b"candidate\n", "LICENSE": b"license\n",
           "src/lib.rs": b"#![no_std]\n"}
    for name, value in raw.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return {**raw, "Cargo.toml.orig": raw["Cargo.toml"],
            ".cargo_vcs_info.json": json.dumps({"git": {"sha1": q.SOURCE_COMMIT}}).encode()}


def tar_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, raw, kind in entries:
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            info.type = kind
            archive.addfile(info, io.BytesIO(raw))
    output.seek(0)
    return output


class FrozenIdentityTests(unittest.TestCase):
    def test_hash_and_duplicate_rejection_precede_any_installer(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            artifact = root / "source-artifact"
            artifact.mkdir()
            wheel = artifact / q.WHEEL
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr(q.PROVENANCE, json.dumps(provenance()))
            with mock.patch.object(q.venv, "EnvBuilder") as build:
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    q.windows(root / "output", root)
                build.assert_not_called()
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            with mock.patch.object(q, "WHEEL_SHA", digest):
                self.assertEqual(q.selected_wheel(artifact), wheel)
                (artifact / "duplicate").mkdir()
                (artifact / "duplicate" / q.WHEEL).write_bytes(wheel.read_bytes())
                with self.assertRaisesRegex(ValueError, "duplicated"):
                    q.selected_wheel(artifact)

    def test_every_identity_dimension_must_match(self):
        q.validate_provenance(provenance())
        for section, key, value in (("git", "base_commit", "a" * 40),
                                    ("git", "state", "dirty"),
                                    ("versions", "core", "0.0.1"),
                                    ("versions", "python", "0.0.1"),
                                    ("versions", "native", "0.0.1")):
            record = provenance()
            record["source"][section][key] = value
            with self.assertRaisesRegex(ValueError, "selected clean source"):
                q.validate_provenance(record)
        for key, value in (("source_origin", "sdist"), ("sha256_lf", "0" * 64)):
            record = provenance()
            (record if key == "source_origin" else record["source"])[key] = value
            with self.assertRaises(ValueError):
                q.validate_provenance(record)

    def test_source_git_root_head_dirty_and_version(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fixture(root)
            for values in ([str(root), q.SOURCE_COMMIT, ""],
                           [str(root.parent)], [str(root), "a" * 40],
                           [str(root), q.SOURCE_COMMIT, " M Cargo.toml"]):
                with mock.patch.object(q.subprocess, "check_output", side_effect=values):
                    if len(values) == 3 and not values[-1]:
                        q.validate_source(root)
                    else:
                        with self.assertRaisesRegex(ValueError, "frozen clean checkout"):
                            q.validate_source(root)
            (root / "Cargo.toml").write_text('[package]\nversion="0.0.1"\n')
            with mock.patch.object(q.subprocess, "check_output", side_effect=[str(root), q.SOURCE_COMMIT, ""]):
                with self.assertRaisesRegex(ValueError, "wrong core version"):
                    q.validate_source(root)

    def test_process_failures_keep_both_streams_and_real_status(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            result = subprocess.CompletedProcess(["tool"], 2, "stdout\n", "stderr\n")
            with mock.patch.object(q.subprocess, "run", return_value=result):
                with self.assertRaises(subprocess.CalledProcessError):
                    q.execute(["tool"], root, root / "failed.log")
            self.assertEqual((root / "failed.log").read_text(), "stdout\nstderr\n")


class CrateBoundaryTests(unittest.TestCase):
    def test_real_archive_orchestration_verifies_then_consumes_exact_extraction(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source, output = root / "source", root / "output"
            output.mkdir()
            files = fixture(source)
            files.update({"tests/case%d.rs" % i: b"test fixture" for i in range(61)})
            calls = []

            def execute(args, cwd, log):
                calls.append((args, cwd))
                if "--list" in args:
                    return "\n".join(files) + "\n"
                if "--target-dir" in args:
                    archive = args[args.index("--target-dir") + 1] / "package/spatial-typestate-0.1.0.crate"
                    archive.parent.mkdir(parents=True)
                    entries = [("spatial-typestate-0.1.0/" + n, b, tarfile.REGTYPE) for n, b in files.items()]
                    archive.write_bytes(tar_bytes(entries).read())
                return "verified tool version"

            def consume(unpacked, home, logs, mode):
                self.assertEqual((unpacked / "src/lib.rs").read_bytes(), files["src/lib.rs"])
                self.assertNotEqual(unpacked, source)
                self.assertEqual(logs, output)

            with (mock.patch.object(q, "SOURCE", source),
                  mock.patch.object(q, "execute", side_effect=execute),
                  mock.patch.object(q, "consumer", side_effect=consume) as consumers):
                result = q.crate(output, root)
            self.assertEqual([c.args[-1] for c in consumers.call_args_list], ["std", "no_std"])
            self.assertEqual(len(result["files"]), 68)
            self.assertEqual(result["archive_sha256"], q.sha(output / "spatial-typestate-0.1.0.crate"))
            self.assertTrue(all("--allow-dirty" not in args and "--no-verify" not in args for args, _ in calls))
            self.assertTrue(all(cwd == source for _, cwd in calls))

    def test_all_members_validated_before_unpack(self):
        prefix = "spatial-typestate-0.1.0/"
        good = [(prefix + "src/lib.rs", b"source", tarfile.REGTYPE)]
        with tarfile.open(fileobj=tar_bytes(good)) as archive:
            self.assertEqual(q.archive_files(archive), {"src/lib.rs": b"source"})
        bad = [("/absolute", tarfile.REGTYPE), (prefix + "../escape", tarfile.REGTYPE),
               (prefix + "src\\escape", tarfile.REGTYPE), ("other/src/lib.rs", tarfile.REGTYPE),
               (prefix + "src/link", tarfile.SYMTYPE), (prefix + "src/", tarfile.DIRTYPE),
               (prefix + "AGENTS.md", tarfile.REGTYPE)]
        for name, kind in bad:
            with tarfile.open(fileobj=tar_bytes([(name, b"", kind)])) as archive:
                with self.assertRaises(ValueError):
                    q.archive_files(archive)
        with tarfile.open(fileobj=tar_bytes(good + good)) as archive:
            with self.assertRaisesRegex(ValueError, "duplicate"):
                q.archive_files(archive)
        with tarfile.open(fileobj=tar_bytes([(prefix + "huge", b"x" * 2_000_001, tarfile.REGTYPE)])) as archive:
            with self.assertRaisesRegex(ValueError, "size"):
                q.archive_files(archive)

    def test_archive_source_manifest_license_lock_and_vcs(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            original = fixture(root)
            self.assertEqual(q.validate_crate(original, root), {"git": {"sha1": q.SOURCE_COMMIT}})
            mutations = [(".cargo_vcs_info.json", json.dumps({"git": {"sha1": q.SOURCE_COMMIT, "dirty": True}}).encode(), "VCS"),
                         (".cargo_vcs_info.json", b'{"git":{"sha1":"wrong"}}', "VCS"),
                         ("Cargo.toml", b'[package]\nversion="0.0.1"\n', "version"),
                         ("Cargo.toml", original["Cargo.toml"] + b'[dependencies]\nextra="1"\n', "dependencies"),
                         ("Cargo.toml.orig", b"wrong", "original manifest"),
                         ("LICENSE", b"wrong", "package input"),
                         ("Cargo.lock", b"wrong", "package input"),
                         ("src/lib.rs", b"wrong", "source bytes")]
            for key, value, message in mutations:
                files = {**original, key: value}
                with self.assertRaisesRegex(ValueError, message):
                    q.validate_crate(files, root)
            missing = {k: v for k, v in original.items() if k != "src/lib.rs"}
            with self.assertRaisesRegex(ValueError, "file set"):
                q.validate_crate(missing, root)
            destination = root / "unpacked"
            q.unpack(original, destination)
            self.assertEqual((destination / "src/lib.rs").read_bytes(), original["src/lib.rs"])

    def test_consumers_resolve_archive_not_checkout_or_registry(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            unpacked = root / "unpacked"
            metadata = {"packages": [{"name": "spatial-typestate", "version": q.VERSION,
                                      "manifest_path": str(unpacked / "Cargo.toml")}]}
            q.validate_consumer(metadata, unpacked)
            for replacement in ([], [metadata["packages"][0]] * 2,
                                [{**metadata["packages"][0], "version": "0.0.1"}],
                                [{**metadata["packages"][0], "manifest_path": str(root / "checkout/Cargo.toml")}]):
                with self.assertRaisesRegex(ValueError, "unpacked candidate"):
                    q.validate_consumer({"packages": replacement}, unpacked)
            output = root / "output"
            output.mkdir()
            for mode in ("std", "no_std"):
                calls = []

                def execute(args, cwd, log):
                    calls.append((args, cwd))
                    return json.dumps(metadata) if "metadata" in args else ""

                with mock.patch.object(q, "execute", side_effect=execute):
                    q.consumer(unpacked, root, output, mode)
                manifest = (root / ("consumer-" + mode) / "Cargo.toml").read_text()
                self.assertIn(str(unpacked).replace("\\", "/"), manifest)
                self.assertEqual('default-features = false' in manifest, mode == "no_std")
                self.assertEqual(calls[-1][0], ["cargo", q.TOOLCHAIN, "run", "--locked", "--offline", "--jobs", "2"])


class InstalledOrchestrationTests(unittest.TestCase):
    def test_copy_assets_excludes_package_and_bytecode(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for relative in ("python/tests/test_a.py", "python/tests/__pycache__/a.pyc",
                             "python/examples/data/sample.csv", "python/src/spatial_typestate/__init__.py",
                             "docs/PYTHON-GUIDE.md"):
                path = root / "source" / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            q.copy_test_assets(root / "source", root / "assets")
            actual = {p.relative_to(root / "assets").as_posix() for p in (root / "assets").rglob("*") if p.is_file()}
            self.assertEqual(actual, {"python/tests/test_a.py", "python/examples/data/sample.csv", "docs/PYTHON-GUIDE.md"})

    def test_windows_installs_selected_bytes_before_two_external_suites(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            wheel = root / q.WHEEL
            wheel.write_bytes(b"verified fixture")
            output = root / "output"
            output.mkdir()
            events = []
            probe = {"python": "fixture", "provenance": provenance()}
            with (mock.patch.object(q, "selected_wheel", return_value=wheel) as select,
                  mock.patch.object(q.venv, "EnvBuilder") as builder,
                  mock.patch.object(q, "copy_test_assets"),
                  mock.patch.object(q, "installed_probe", return_value=probe),
                  mock.patch.object(q, "execute", side_effect=lambda a, c, l: events.append((a, c))),
                  mock.patch.object(q, "installed_suite", side_effect=lambda p, a, c, o, phase: events.append((phase, c)))):
                result = q.windows(output, root)
            select.assert_called_once_with(root / "source-artifact")
            builder.assert_called_once_with(with_pip=True, system_site_packages=False)
            self.assertIn("find_spec('numpy') is None", events[0][0][-1])
            self.assertEqual(events[1][0][-4:], ["pip", "install", "--no-deps", wheel])
            self.assertEqual(events[2][0], "stdlib")
            self.assertIn("--require-hashes", events[3][0])
            self.assertEqual(events[4][0], "numpy")
            self.assertTrue(all(c.parent.parent == root and c.name == "cwd" for _, c in events))
            self.assertEqual(result["wheel_sha256"], hashlib.sha256(b"verified fixture").hexdigest())
            self.assertEqual((output / q.WHEEL).read_bytes(), b"verified fixture")

    def test_installed_probe_and_suite_use_isolated_interpreter(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with mock.patch.object(q, "execute", return_value=json.dumps({"provenance": provenance()})) as execute:
                q.installed_probe(Path("venv-python"), root, root)
                q.installed_suite(Path("venv-python"), root / "assets", root, root, "stdlib")
            args = [c.args[0] for c in execute.call_args_list]
            self.assertTrue(all(a[:2] == [Path("venv-python"), "-I"] for a in args))
            self.assertIn("sysconfig.get_paths()['purelib']", args[0][-1])
            self.assertEqual(args[-1][-1], "--demonstrate-errors")

    def test_hosted_only_and_fixed_mode(self):
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with self.assertRaisesRegex(ValueError, "hosted-only"):
                q.main()
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}), mock.patch.object(q.sys, "argv", ["script", "arbitrary"]):
            with self.assertRaisesRegex(ValueError, "fixed qualification mode"):
                q.main()

    def test_no_success_record_if_source_changes_during_consumer(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with (mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_TEMP": str(root), "GITHUB_SHA": "a" * 40}),
                  mock.patch.object(q.sys, "argv", ["script", "windows"]),
                  mock.patch.object(q, "validate_source", side_effect=[None, ValueError("source changed")]),
                  mock.patch.object(q, "windows", return_value={"kind": "fixture"})):
                with self.assertRaisesRegex(ValueError, "source changed"):
                    q.main()
            self.assertFalse((root / "qualified-candidate/qualification.json").exists())

    def test_success_record_is_fixed_location_and_binds_both_commits(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with (mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_TEMP": str(root), "GITHUB_SHA": "a" * 40}),
                  mock.patch.object(q.sys, "argv", ["script", "crate"]),
                  mock.patch.object(q, "validate_source") as validate,
                  mock.patch.object(q, "crate", return_value={"kind": "fixture", "source_commit": q.SOURCE_COMMIT})):
                q.main()
            result = json.loads((root / "qualified-candidate/qualification.json").read_text())
            self.assertEqual(result["source_commit"], q.SOURCE_COMMIT)
            self.assertEqual(result["tooling_commit"], "a" * 40)
            self.assertTrue(result["complete"])
            self.assertEqual(validate.call_count, 2)


if __name__ == "__main__":
    unittest.main()

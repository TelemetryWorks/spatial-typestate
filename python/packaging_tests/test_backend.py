"""Build-only gates, separate from installed-wheel runtime tests."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import build_backend as b
import verify_artifacts as v
import check_package_metadata as m


class BackendTests(unittest.TestCase):
    def test_extra_wheel_metadata_rejected(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);info=root/"prepared/fixture.dist-info";info.mkdir(parents=True)
            (info/"METADATA").write_bytes(b"Name: fixture\n")
            with zipfile.ZipFile(root/"fixture.whl","w") as z:
                z.writestr("fixture.dist-info/METADATA",b"Name: fixture\n")
                z.writestr("fixture.dist-info/EXTRA",b"unexpected")
                z.writestr("spatial_typestate/_provenance.json",b"{}")
            with self.assertRaisesRegex(ValueError,"file set mismatch"):m.verify_prepared(root)

    def test_metadata_compatibility_forwarded_without_wheel_flags(self):
        with tempfile.TemporaryDirectory() as d:
            old=Path.cwd()
            try:
                os.chdir(PROJECT)
                with patch("maturin.prepare_metadata_for_build_wheel",return_value="fixture.dist-info") as delegate:
                    b.prepare_metadata_for_build_wheel(d,{"build-args":"--compatibility manylinux_2_28 --auditwheel check"})
                    self.assertEqual(delegate.call_args.args[1],{"build-args":"--locked --compatibility manylinux_2_28 --auditwheel check"})
                    self.assertIn("--compatibility off",b.settings(None)["build-args"])
            finally:
                os.chdir(old)

    def test_editable_rejection_actionable(self):
        with self.assertRaisesRegex(ValueError,"installed development wheel"):
            b.build_editable("unused")

    def test_line_endings_and_bad_text(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"test.rs"
            p.write_bytes(b"a\r\nb\r\n")
            self.assertEqual(b.text_bytes(p), b"a\nb\n")
            p.write_bytes(b"a\rb")
            with self.assertRaises(ValueError): b.text_bytes(p)
            p.write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError): b.text_bytes(p)

    def test_git_root_worktree_and_unknown(self):
        core = PROJECT.parent.resolve()
        with patch.object(b, "run", side_effect=[str(core), "a"*40, ""]):
            self.assertEqual(b.git_identity(core), {"base_commit":"a"*40,"state":"clean"})
        with patch.object(b, "run", return_value=str(core.parent)):
            self.assertEqual(b.git_identity(core), {"base_commit":None,"state":"unknown"})
        with patch.object(b, "run", side_effect=[str(core), "b"*40, " M src/point.rs"]):
            self.assertEqual(b.git_identity(core)["state"], "dirty")
        with patch.object(b, "run", side_effect=OSError()):
            self.assertEqual(b.git_identity(core)["state"], "unknown")
        with tempfile.TemporaryDirectory() as d:
            worktree=Path(d).resolve()
            (worktree/".git").write_text("gitdir: separate-metadata\n")
            with patch.object(b,"run",side_effect=[str(worktree),"c"*40,""]):
                self.assertEqual(b.git_identity(worktree)["state"],"clean")

    def test_readiness_and_override_rejection(self):
        with patch.dict(os.environ,{"SPATIAL_EXPECT_COMMIT":"a"*40}):
            for identity in [{"base_commit":None,"state":"unknown"},
                             {"base_commit":"a"*40,"state":"dirty"},
                             {"base_commit":"b"*40,"state":"clean"}]:
                with patch.object(b,"git_identity",return_value=identity):
                    with self.assertRaisesRegex(ValueError,"clean exact"): b.source_record(PROJECT)
        with patch.dict(os.environ,{"RUSTFLAGS":"-Ctarget-cpu=native"}):
            with self.assertRaisesRegex(ValueError,"external build flags"):
                with b.build_environment(PROJECT.parent,PROJECT,"checkout"): pass

    def test_frozen_source_stale_tampered_and_compile_input(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SPATIAL_EXPECT_COMMIT",None)
            source, _ = b.source_record(PROJECT)
            with b.staging(PROJECT,source) as (project, root):
                package = b.layout(project)[3]
                (project/"PKG-INFO").write_text("Metadata-Version: 2.4\nName: spatial-typestate\nVersion: 0.1.0\n\n")
                record = package/b.RESOURCE
                record.write_bytes(b.canonical({"schema":1,"artifact_kind":"sdist","source":source}))
                with patch.object(b,"git_identity", side_effect=AssertionError("must not use Git")):
                    self.assertEqual(b.source_record(project), (source,"sdist"))
                core_file = root/"src/point.rs"; original=core_file.read_bytes()
                core_file.write_bytes(original.replace(b"\n",b"\r\n"))
                self.assertEqual(b.source_record(project)[0],source)
                core_file.write_bytes(original+b"\n// changed\n")
                with self.assertRaisesRegex(ValueError,"mismatch"): b.source_record(project)
                core_file.write_bytes(original)
                extra=root/"src/extra.rs";extra.write_text("// extra source\n")
                with self.assertRaisesRegex(ValueError,"mismatch"): b.source_record(project)
                extra.unlink()
                wrong = json.loads(record.read_bytes());wrong["source"]["files"]["core/src/point.rs"]="0"*64
                record.write_bytes(b.canonical(wrong))
                with self.assertRaisesRegex(ValueError,"mismatch"): b.source_record(project)
                wrong["artifact_kind"]="wheel";record.write_bytes(b.canonical(wrong))
                with self.assertRaisesRegex(ValueError,"not a frozen"): b.source_record(project)
                record.unlink()
                core_file.write_bytes(original+b'\nconst EXTRA: &str = include_str!("hidden.txt");\n')
                with self.assertRaisesRegex(ValueError,"compile inputs"): b.inputs(project)

    def test_frozen_record_cannot_hide_real_dirty_checkout(self):
        source,_=b.source_record(PROJECT)
        with b.staging(PROJECT,source) as (project,root):
            (project/"PKG-INFO").write_text("Name: spatial-typestate\nVersion: 0.1.0\n")
            (root/".gitignore").write_text("_provenance.json\n")
            subprocess.run(["git","init","--quiet",str(root)],check=True)
            subprocess.run(["git","-C",str(root),"add",".gitignore"],check=True)
            subprocess.run(["git","-C",str(root),"-c","user.name=Fixture","-c","user.email=fixture@example.invalid","commit","--quiet","-m","Fixture baseline"],check=True)
            self.assertEqual(b.git_identity(root)["state"],"dirty")
            forged=dict(source,git={"base_commit":"a"*40,"state":"clean"})
            (b.layout(project)[3]/b.RESOURCE).write_bytes(b.canonical({"schema":1,"artifact_kind":"sdist","source":forged}))
            with patch.dict(os.environ,{"SPATIAL_EXPECT_COMMIT":"a"*40}):
                with self.assertRaisesRegex(ValueError,"Git checkout"): b.source_record(project)

    def test_sdist_inside_parent_repository_and_warning_policy(self):
        source,_=b.source_record(PROJECT)
        with b.staging(PROJECT,source) as (project,root):
            (project/"PKG-INFO").write_text("Name: spatial-typestate\nVersion: 0.1.0\n")
            (b.layout(project)[3]/b.RESOURCE).write_bytes(b.canonical({"schema":1,"artifact_kind":"sdist","source":source}))
            with tempfile.TemporaryDirectory() as d:
                parent=Path(d);subprocess.run(["git","init","--quiet",str(parent)],check=True)
                shutil.copytree(root,parent/"extracted")
                extracted=parent/"extracted"/project.relative_to(root)
                self.assertEqual(b.source_record(extracted),(source,"sdist"))
            with patch.dict(os.environ,{},clear=False):
                os.environ.pop("SPATIAL_DENY_WARNINGS",None)
                with b.build_environment(root,root,"sdist") as (_,_,deny):
                    self.assertFalse(deny)
                    self.assertNotIn("-Dwarnings",os.environ["CARGO_ENCODED_RUSTFLAGS"])

    def test_notice_inventory_stale(self):
        source,_=b.source_record(PROJECT)
        with b.staging(PROJECT,source) as (project,_):
            p=project/"licenses/inventory.json";p.write_text("[]")
            with self.assertRaisesRegex(ValueError,"stale"): b.inputs(project)

    def test_path_scan_plant_and_version_gates(self):
        b.check_paths((PROJECT/"build_backend.py").read_bytes())
        for raw in [b"/home/alice/source/file.rs",b"C:\\Users\\Alice\\lib.pdb",b"/runner/work/a/a/src/main.rs",b"arbitrary/build/root/hello"]:
            with self.assertRaises(ValueError): b.check_paths(raw,["arbitrary/build/root"])
        v.validate_versions(["GLIBC_2.28","GCC_3.0"])
        for names in [["GLIBC_2.29"],["GCC_99.0"],["SOMETHING_1.0"]]:
            with self.assertRaises(ValueError): v.validate_versions(names)
        with patch.object(v.subprocess,"check_output",side_effect=["ELF64 Advanced Micro Devices X86-64","(NEEDED) [libc.so.6]","not parsed"]):
            with self.assertRaisesRegex(ValueError,"missing ELF version"): v.elf_report(Path("fixture.so"))

    def test_zip_modes_preserved_and_missing_tool_hashes(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.whl"
            info=zipfile.ZipInfo("spatial_typestate/_native.pyd");info.external_attr=0o100755<<16
            with zipfile.ZipFile(p,"w") as z:
                z.writestr(info,b"fixture")
                z.writestr("fixture.dist-info/METADATA",b"Name: fixture\n")
            b.rewrite_wheel(p,{"spatial_typestate/_provenance.json":b"{}"})
            with zipfile.ZipFile(p) as z:
                self.assertEqual(z.getinfo(info.filename).external_attr>>16,0o100755)
                self.assertEqual(z.getinfo("spatial_typestate/_provenance.json").external_attr>>16,0o100644)
            with patch.dict(os.environ,{},clear=False):
                os.environ.pop("SPATIAL_EXPECT_COMMIT",None)
                self.assertEqual(b.tool_hashes(Path(d)),{"cargo":None,"rustc":None})
            with patch.dict(os.environ,{"SPATIAL_EXPECT_COMMIT":"a"*40}):
                with self.assertRaisesRegex(ValueError,"binary hashes"): b.tool_hashes(Path(d))

    def test_sdist_headers_and_planted_path_fail(self):
        import tarfile,io
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fixture.tar.gz"
            def write(raw,owner=""):
                with tarfile.open(path,"w:gz") as tar:
                    info=tarfile.TarInfo("fixture/src/lib.rs");info.uname=owner;info.mode=0o644;info.size=len(raw)
                    tar.addfile(info,io.BytesIO(raw))
            write(b"// source\n", "private-owner")
            with self.assertRaisesRegex(ValueError,"header leaks"): v.sdist_report(path)
            write(b"C:\\Users\\Private\\source.rs")
            with self.assertRaisesRegex(ValueError,"local path"): v.sdist_report(path)
            write(b"// source\n")
            self.assertEqual(v.sdist_report(path)["headers"],"normalized")

    def test_final_wheel_tags_and_missing_native_fail_closed(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"spatial_typestate-0.1.0-cp311-abi3-manylinux_2_28_x86_64.whl"
            tag="cp311-abi3-manylinux_2_28_x86_64"
            record={"source":{},"build":{"tags":[tag]}}
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("spatial_typestate-0.1.0.dist-info/METADATA","Name: spatial-typestate\nLicense-Expression: Apache-2.0\n")
                z.writestr("spatial_typestate-0.1.0.dist-info/WHEEL","Tag: "+tag+"\n")
                for name in ["_native.pyi","py.typed"]:z.writestr("spatial_typestate/"+name,"")
            b.rewrite_wheel(path,{"spatial_typestate/_provenance.json":b.canonical(record)})
            with self.assertRaisesRegex(ValueError,"exactly one"):v.wheel_report(path)
            record["build"]["tags"]=["cp311-abi3-linux_x86_64"]
            b.rewrite_wheel(path,{"spatial_typestate/_provenance.json":b.canonical(record)})
            with self.assertRaisesRegex(ValueError,"tags disagree"):v.wheel_report(path)

    def test_checkout_warning_denial(self):
        # Run the exact encoded-flag policy on a real warning-producing crate.
        source,_=b.source_record(PROJECT)
        with b.staging(PROJECT,source) as (_,root):
            with b.build_environment(PROJECT.parent,root,"checkout"):
                p=root/"warning.rs";p.write_text("fn main() { let unused = 1; }\n")
                flags=os.environ["CARGO_ENCODED_RUSTFLAGS"].split("\x1f")
                run=subprocess.run(["rustc",str(p),*flags,"--out-dir",str(root)],capture_output=True,text=True)
                self.assertNotEqual(run.returncode,0)
                self.assertIn("unused",run.stderr)

    def test_missing_compiler_notices_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ,{"SPATIAL_EXPECT_COMMIT":"a"*40}):
                with self.assertRaisesRegex(ValueError,"notices"): b.compiler_notices(Path(d))
            with patch.dict(os.environ,{},clear=False):
                os.environ.pop("SPATIAL_EXPECT_COMMIT",None)
                self.assertEqual(b.compiler_notices(Path(d))[1]["state"],"unavailable")

    @unittest.skipUnless(sys.platform=="linux", "real new-glibc ELF test runs on newer Linux CI")
    def test_real_glibc_229_elf_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/"too_new.c"
            p.write_text('extern double newer_exp(double);\n__asm__(".symver newer_exp,exp@GLIBC_2.29");\ndouble compute(double x) { return newer_exp(x); }\n')
            subprocess.run(["cc","-shared","-fPIC",str(p),"-lm","-o",str(root/"too_new.so")],check=True)
            versions=subprocess.check_output(["readelf","--version-info",str(root/"too_new.so")],text=True)
            self.assertIn("GLIBC_2.29",versions)
            with self.assertRaisesRegex(ValueError,"exceeds baseline"): v.elf_report(root/"too_new.so")


if __name__=="__main__": unittest.main()

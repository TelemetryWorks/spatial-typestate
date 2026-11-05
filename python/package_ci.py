"""CI-only container orchestration; no Docker/tool installation on developer hosts."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANYLINUX = "quay.io/pypa/manylinux_2_28_x86_64@sha256:7e41b1c7fd64dfc69703a1124b43c404382973ee06ec5d764b85c34d2221fded"
NEWER = {
    "3.11": "python@sha256:061c190f3d5815b341a18dfe8a45771f8ba68c15a607ea56997fde3009ac4eec",
    "3.14": "python@sha256:47d41ea4947601fd5bc7ed6c00a7b9c1fbb936a7684873908a3c3b4e68ce3c86",
}


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def build_local(out, from_sdist=False):
    out.mkdir(parents=True, exist_ok=True)
    source = next(out.glob("*.tar.gz")) if from_sdist else ROOT/"python"
    destination = out/"from-sdist" if from_sdist else out
    destination.mkdir(exist_ok=True)
    if not from_sdist:
        sys.path.insert(0,str(ROOT/"python"))
        import build_backend
        (out/"prepared").mkdir(exist_ok=True)
        old=Path.cwd()
        try:
            os.chdir(ROOT/"python")
            config={"build-args":"--compatibility manylinux_2_28 --auditwheel check"} if sys.platform=="linux" else None
            build_backend.prepare_metadata_for_build_wheel(str(out/"prepared"),config)
        finally:
            os.chdir(old)
    command = [sys.executable,"-m","pip","wheel","--no-deps","--no-build-isolation","--wheel-dir",destination,source]
    if sys.platform=="linux":
        command += ["--config-settings=build-args=--compatibility manylinux_2_28 --auditwheel check"]
    run(*command)
    if not from_sdist:
        sys.path.insert(0,str(ROOT/"python"))
        import build_backend
        old = Path.cwd()
        try:
            os.chdir(ROOT/"python")
            build_backend.build_sdist(str(out))
        finally:
            os.chdir(old)
        run(sys.executable,ROOT/"python/check_package_metadata.py","--prepared",out)
    run(sys.executable,ROOT/"python/verify_artifacts.py",destination,"--expect-commit",os.environ["SPATIAL_EXPECT_COMMIT"])


def docker_build(out, version, from_sdist=False):
    toolchain = Path(subprocess.check_output(["rustc","--print","sysroot"],text=True).strip())
    executable = f"/opt/python/cp{version.replace('.','')}-cp{version.replace('.','')}/bin/python"
    out.mkdir(parents=True,exist_ok=True)
    command = ["docker","run","--rm","--platform","linux/amd64",
               "--mount",f"type=bind,src={ROOT},dst=/project,readonly",
               "--mount",f"type=bind,src={toolchain},dst=/opt/rust,readonly",
               "--mount",f"type=bind,src={out},dst=/out",
               "--env","CARGO_HOME=/cargo","--env","CARGO_TARGET_DIR=/target",
               "--env","SPATIAL_DENY_WARNINGS=1","--env","CARGO_BUILD_JOBS=2",
               "--env",f"SPATIAL_BUILD_IMAGE={MANYLINUX}",
               "--env",f"SPATIAL_EXPECT_COMMIT={os.environ['SPATIAL_EXPECT_COMMIT']}",
               MANYLINUX,executable,"/project/python/package_ci.py","inside-build","--out","/out"]
    if from_sdist: command += ["--from-sdist"]
    run(*command)


def runtime(out, version):
    evidence=json.loads((out/"runtime-evidence.json").read_text()) if (out/"runtime-evidence.json").exists() else []
    wheels=[next(out.glob("*.whl"))]
    if (out/"from-sdist").exists(): wheels += sorted((out/"from-sdist").glob("*.whl"))
    with tempfile.TemporaryDirectory(prefix="spatial-runtime-tests-") as d:
        assets=Path(d)
        for relative in ["python/tests","python/examples"]:
            shutil.copytree(ROOT/relative,assets/relative,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
        (assets/"docs").mkdir()
        shutil.copyfile(ROOT/"docs/PYTHON-GUIDE.md",assets/"docs/PYTHON-GUIDE.md")
        # Only tests/examples/docs are mounted, never package source or build dirs.
        for wheel in wheels:
            for image, executable, glibc in [(MANYLINUX,f"/opt/python/cp{version.replace('.','')}-cp{version.replace('.','')}/bin/python","2.28"),
                                               (NEWER[version],"python","2.36")]:
                command=["docker","run","--rm","--platform","linux/amd64",
                    "--mount",f"type=bind,src={wheel.parent},dst=/wheels,readonly",
                    "--mount",f"type=bind,src={assets},dst=/test-root,readonly",
                    "--workdir","/tmp",image,executable,"-c",
                    "import ctypes,subprocess,sys,json,hashlib,pathlib;lib=ctypes.CDLL(None);lib.gnu_get_libc_version.restype=ctypes.c_char_p;"
                    f"assert lib.gnu_get_libc_version().decode()=={glibc!r};"
                    f"assert sys.version_info[:2]=={tuple(map(int,version.split('.')))!r};"
                    f"print('SPATIAL_RUNTIME='+json.dumps(dict(glibc=lib.gnu_get_libc_version().decode(),python=sys.version,sha256=hashlib.sha256(pathlib.Path('/wheels/{wheel.name}').read_bytes()).hexdigest())),flush=True);"
                    f"subprocess.run([sys.executable,'-m','pip','install','--no-deps','/wheels/{wheel.name}'],check=True);"
                    "subprocess.run([sys.executable,'-I','-m','unittest','discover','-s','/test-root/python/tests','-v'],check=True)"]
                result=subprocess.run(command,capture_output=True,text=True)
                print(result.stdout);print(result.stderr,file=sys.stderr);result.check_returncode()
                record=json.loads(next(line.removeprefix("SPATIAL_RUNTIME=") for line in result.stdout.splitlines() if line.startswith("SPATIAL_RUNTIME=")))
                if record["sha256"]!=__import__("hashlib").sha256(wheel.read_bytes()).hexdigest():
                    raise ValueError("runtime tested different wheel bytes")
                evidence.append(dict(record,image=image,artifact=str(wheel.relative_to(out))))
    (out/"runtime-evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["build","inside-build","runtime"])
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--python",choices=["3.11","3.14"])
    parser.add_argument("--from-sdist",action="store_true")
    args=parser.parse_args();out=args.out.resolve()
    if args.mode=="inside-build":
        # Preserve the pinned image's clang/GCC-toolset/binutils directories.
        os.environ["PATH"]=str(Path(sys.executable).parent)+os.pathsep+"/opt/rust/bin"+os.pathsep+os.environ["PATH"]
        run("git","config","--global","--add","safe.directory","/project")
        run(sys.executable,"-m","pip","install","--require-hashes","--only-binary=:all:","-r",ROOT/"python/requirements-build.txt")
        build_local(out,args.from_sdist)
    elif args.mode=="build":
        if sys.platform=="linux": docker_build(out,args.python,args.from_sdist)
        else: build_local(out,args.from_sdist)
    else:
        # Each Linux candidate (including the 3.11 build) runs on BOTH interpreters.
        for version in ("3.11","3.14"):
            runtime(out,version)


if __name__=="__main__": main()

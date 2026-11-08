"""One frozen candidate's hosted-only consumers; never a publishing command."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile


SOURCE_COMMIT = "9974fd6a00521d631d6ff6e35d4aa936f6b624cf"
SOURCE_IDENTITY = "9c5b2f7c362afb06671fe5a5b8b6edf58aa86db87c721437dd719e45b023fa44"
VERSION = "0.1.0"
MANIFEST = "Cargo.toml"
WHEEL = "spatial_typestate-0.1.0-cp311-abi3-win_amd64.whl"
WHEEL_SHA = "b59ead8787b870d28f0aba2b7bd8264a993e2dfa93ca3fa9d3a5d249254c12c8"
TOOLCHAIN = "+1.99.0"
SOURCE = Path(__file__).resolve().parents[3] / "candidate-source"
PROVENANCE = "spatial_typestate/_provenance.json"
EXCLUDED = {"AGENTS.md", "CLAUDE.md", ".cargo", "rust-toolchain.toml",
            "scripts", ".gitignore", "ROADMAP.md", "images", "docs", ".github", "python"}
SMOKE = '''use spatial_typestate::{Frame, Meters, Point3, SpatialError, Transform};
struct Body; struct World;
impl Frame for Body {} impl Frame for World {}
fn main() -> Result<(), SpatialError> {
    let map = Transform::<Body, World, Meters>::from_translation(10., 20., 30.);
    let p = map.apply_point(Point3::<Body, Meters>::new(1., 2., 3.))?;
    assert_eq!((p.x, p.y, p.z), (11., 22., 33.));
    assert_eq!(map.apply_point(Point3::new(f64::NAN, 0., 0.)).unwrap_err(), SpatialError::NonFinite);
    Ok(())
}
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(args, cwd, log):
    """Keep complete stdout/stderr and fail on the real process status."""
    result = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                            encoding="utf-8", errors="strict", timeout=1200)
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    result.check_returncode()
    return result.stdout


def validate_source(source):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], encoding="utf-8").strip()
    if (Path(git("rev-parse", "--show-toplevel")).resolve() != source.resolve()
            or git("rev-parse", "HEAD") != SOURCE_COMMIT
            or git("status", "--porcelain", "--untracked-files=all")):
        raise ValueError("source is not the frozen clean checkout")
    if tomllib.loads((source / MANIFEST).read_text(encoding="utf-8"))["package"]["version"] != VERSION:
        raise ValueError("wrong core version")


def validate_provenance(record):
    source = record["source"]
    if (source["git"] != {"base_commit": SOURCE_COMMIT, "state": "clean"}
            or source["versions"] != {"core": VERSION, "python": VERSION, "native": VERSION}
            or source["sha256_lf"] != SOURCE_IDENTITY
            or record["source_origin"] != "checkout"):
        raise ValueError("wheel is not the selected clean source")


def selected_wheel(directory):
    matches = list(directory.rglob(WHEEL))
    if len(matches) != 1 or sha(matches[0]) != WHEEL_SHA:
        raise ValueError("selected wheel missing, duplicated or hash mismatch")
    with zipfile.ZipFile(matches[0]) as archive:
        validate_provenance(json.loads(archive.read(PROVENANCE)))
    return matches[0]


def installed_probe(python, cwd, output):
    code = '''import importlib.resources as r, importlib.metadata as m, json, pathlib, sys, sysconfig
import spatial_typestate as s
from spatial_typestate import _native as n
origin=pathlib.Path(s.__file__).resolve()
native_origin=pathlib.Path(n.__file__).resolve()
site=pathlib.Path(sysconfig.get_paths()['purelib']).resolve()
assert origin.is_relative_to(site) and native_origin.is_relative_to(site)
assert m.version('spatial-typestate')=='0.1.0'
print(json.dumps(dict(origin=str(origin),native_origin=str(native_origin),python=sys.version,
provenance=json.loads(r.files(s).joinpath('_provenance.json').read_text()))))
'''
    result = json.loads(execute([python, "-I", "-c", code], cwd, output / "installed-probe.log"))
    validate_provenance(result["provenance"])
    return result


def copy_test_assets(source, destination):
    for relative in ("python/tests", "python/examples"):
        shutil.copytree(source / relative, destination / relative,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (destination / "docs").mkdir()
    shutil.copyfile(source / "docs/PYTHON-GUIDE.md", destination / "docs/PYTHON-GUIDE.md")


def installed_suite(python, assets, cwd, output, phase):
    execute([python, "-I", "-m", "unittest", "discover", "-s", assets / "python/tests", "-v"],
            cwd, output / (phase + "-tests.log"))
    execute([python, "-I", assets / "python/examples/lab_workflow.py", "--demonstrate-errors"],
            cwd, output / (phase + "-lab.log"))


def windows(output, temporary):
    # The immutable hash check precedes venv creation and every installer call.
    wheel = selected_wheel(temporary / "source-artifact")
    with tempfile.TemporaryDirectory(prefix="candidate-consumer-", dir=temporary) as name:
        root = Path(name)
        environment, assets, cwd = root / "venv", root / "assets", root / "cwd"
        cwd.mkdir()
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
        python = environment / "Scripts/python.exe"
        copy_test_assets(SOURCE, assets)
        execute([python, "-I", "-c", "import importlib.util; assert importlib.util.find_spec('numpy') is None"],
                cwd, output / "stdlib-only.log")
        execute([python, "-m", "pip", "install", "--no-deps", wheel], cwd, output / "install.log")
        probe = installed_probe(python, cwd, output)
        installed_suite(python, assets, cwd, output, "stdlib")
        execute([python, "-m", "pip", "install", "--require-hashes", "--only-binary=:all:",
                 "-r", SOURCE / "python/requirements-interop.txt"], cwd, output / "interop-install.log")
        installed_suite(python, assets, cwd, output, "numpy")
        shutil.copyfile(wheel, output / WHEEL)
        return {"kind": "installed-wheel", "source_commit": SOURCE_COMMIT, "wheel_sha256": sha(wheel),
                "installed": probe, "stdlib_suite": "passed", "numpy_suite": "passed",
                "cwd_outside_checkout": True, "publication_approved": False}


def archive_files(archive):
    result = {}
    for member in archive:
        path = PurePosixPath(member.name)
        if (not member.isfile() or path.is_absolute() or ".." in path.parts
                or "\\" in member.name or len(path.parts) < 2
                or path.parts[0] != "spatial-typestate-" + VERSION):
            raise ValueError("unsafe crate member")
        logical = PurePosixPath(*path.parts[1:]).as_posix()
        if logical in result or path.parts[1] in EXCLUDED:
            raise ValueError("duplicate or unintended crate member")
        if member.size > 2_000_000:
            raise ValueError("unexpected crate member size")
        result[logical] = archive.extractfile(member).read()
    return result


def validate_crate(files, source):
    vcs = json.loads(files[".cargo_vcs_info.json"])
    if vcs["git"]["sha1"] != SOURCE_COMMIT or vcs["git"].get("dirty", False) is not False:
        raise ValueError("crate VCS identity mismatch")
    config = tomllib.loads(files[MANIFEST].decode())
    if config["package"]["version"] != VERSION or config.get("dependencies"):
        raise ValueError("crate version or normal dependencies changed")
    if files["Cargo.toml.orig"] != (source / MANIFEST).read_bytes():
        raise ValueError("crate original manifest differs")
    for name in ("LICENSE", "README.md", "Cargo.lock"):
        if files[name] != (source / name).read_bytes():
            raise ValueError("crate package input differs: " + name)
    tracked = {p.relative_to(source).as_posix() for p in (source / "src").rglob("*.rs")}
    if {n for n in files if n.startswith("src/")} != tracked:
        raise ValueError("crate source file set differs")
    for name in tracked:
        if files[name] != (source / name).read_bytes():
            raise ValueError("crate source bytes differ")
    return vcs


def unpack(files, destination):
    # All names/types were checked before any writes; destination is our private temp.
    destination.mkdir()
    for name, raw in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def validate_consumer(metadata, unpacked):
    core = [p for p in metadata["packages"] if p["name"] == "spatial-typestate"]
    if (len(core) != 1 or core[0]["version"] != VERSION
            or Path(core[0]["manifest_path"]).resolve() != (unpacked / MANIFEST).resolve()):
        raise ValueError("consumer did not resolve the unpacked candidate")


def consumer(unpacked, root, output, mode):
    directory = root / ("consumer-" + mode)
    (directory / "src").mkdir(parents=True)
    options = "" if mode == "std" else ', default-features = false, features = ["no_std"]'
    dependency = json.dumps(str(unpacked).replace("\\", "/"))
    (directory / MANIFEST).write_text(
        '[package]\nname="candidate-consumer"\nversion="0.0.0"\nedition="2024"\n'
        '[dependencies]\nspatial-typestate={path=' + dependency + ', version="=0.1.0"' + options + '}\n',
        encoding="utf-8")
    (directory / "src/main.rs").write_text(SMOKE, encoding="utf-8")
    execute(["cargo", TOOLCHAIN, "generate-lockfile", "--offline"], directory, output / (mode + "-lock.log"))
    raw = execute(["cargo", TOOLCHAIN, "metadata", "--locked", "--offline", "--format-version", "1"],
                  directory, output / (mode + "-metadata.json"))
    validate_consumer(json.loads(raw), unpacked)
    execute(["cargo", TOOLCHAIN, "run", "--locked", "--offline", "--jobs", "2"],
            directory, output / (mode + "-consumer.log"))


def crate(output, temporary):
    tools = {"rustc": execute(["rustc", "+1.99.0", "-vV"], SOURCE, output / "rustc.txt"),
             "cargo": execute(["cargo", TOOLCHAIN, "--version"], SOURCE, output / "cargo.txt")}
    with tempfile.TemporaryDirectory(prefix="candidate-crate-", dir=temporary) as name:
        root = Path(name)
        target = root / "target"
        names = execute(["cargo", TOOLCHAIN, "package", "--list", "--locked"], SOURCE, output / "package-list.txt")
        execute(["cargo", TOOLCHAIN, "package", "--locked", "--jobs", "2", "--target-dir", target],
                SOURCE, output / "package-verify.log")
        archive = target / "package/spatial-typestate-0.1.0.crate"
        with tarfile.open(archive) as handle:
            files = archive_files(handle)
        if set(files) != set(names.splitlines()) or len(files) != 68:
            raise ValueError("actual archive differs from reviewed package list")
        vcs = validate_crate(files, SOURCE)
        unpacked = root / "unpacked"
        unpack(files, unpacked)
        for mode in ("std", "no_std"):
            consumer(unpacked, root, output, mode)
        shutil.copyfile(archive, output / archive.name)
        return {"kind": "crate", "source_commit": SOURCE_COMMIT, "archive_sha256": sha(archive),
                "vcs": vcs, "tools": tools,
                "files": {n: hashlib.sha256(v).hexdigest() for n, v in sorted(files.items())},
                "consumer_modes": ["std", "no_std"], "publication_approved": False}


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("qualification is hosted-only")
    mode = sys.argv[1:]
    if mode not in (["windows"], ["crate"]):
        raise ValueError("expected a fixed qualification mode")
    validate_source(SOURCE)
    temporary = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    output = temporary / "qualified-candidate"
    output.mkdir(mode=0o700)
    result = (windows if mode == ["windows"] else crate)(output, temporary)
    validate_source(SOURCE)
    result["tooling_commit"] = os.environ["GITHUB_SHA"]
    result["complete"] = True
    (output / "qualification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"installed", "files"}}))


if __name__ == "__main__":
    main()

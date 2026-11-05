"""Private PEP 517 wrapper: locked maturin builds plus inspectable provenance.

No runtime imports depend on this module. All paths in records are logical.
"""
from contextlib import contextmanager
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib
import zipfile
import tarfile

WRAPPER_VERSION = "1"
RESOURCE = "_provenance.json"
TEXT_SUFFIXES = {".rs", ".toml", ".lock", ".py", ".pyi", ".md", ".txt", ".json"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def text_bytes(path):
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    raw.decode("utf-8")
    if b"\r" in raw:
        raise ValueError("lone CR in source input")
    return raw


def layout(project):
    project = Path(project).resolve()
    config = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    native = (project / config["tool"]["maturin"]["manifest-path"]).resolve().parent
    native_config = tomllib.loads((native / "Cargo.toml").read_text(encoding="utf-8"))
    dependency = native_config["dependencies"]["spatial-typestate"]
    if set(dependency) != {"path"}:
        raise ValueError("core dependency must be the vendored path only")
    core = (native / dependency["path"]).resolve()
    cargo_config = core / ".cargo/config.toml"
    if cargo_config.exists() and tomllib.loads(cargo_config.read_text(encoding="utf-8")) != {"build": {"rustflags": ["-Dwarnings"]}}:
        raise ValueError("extend build provenance for changed Cargo configuration")
    package = project / config["tool"]["maturin"]["python-source"] / "spatial_typestate"
    for path in (project, native, package):
        path.relative_to(core)
    return project, core, native, package, config, native_config


def inputs(project):
    project, core, native, package, config, native_config = layout(project)
    paths = {}
    for label, base in (("core", core), ("native", native)):
        manifest = tomllib.loads((base / "Cargo.toml").read_text(encoding="utf-8"))
        if manifest["package"].get("build") or manifest.get("lib", {}).get("path", "src/lib.rs") != "src/lib.rs":
            raise ValueError("extend inventory for redirected Cargo compile inputs")
        for path in sorted((base / "src").rglob("*")):
            if path.is_file():
                if path.suffix != ".rs":
                    # In an extracted sdist the Python package shares core/src.
                    if base == core and path.is_relative_to(package):
                        continue
                    raise ValueError("unreviewed non-Rust compile input")
                raw = text_bytes(path)
                if re.search(rb"\b(?:include|include_str|include_bytes|env|option_env)\s*!|#\s*\[\s*path\s*=", raw):
                    raise ValueError("extend the inventory before using external compile inputs")
                paths[f"{label}/{path.relative_to(base).as_posix()}"] = path
        if (base / "build.rs").exists():
            raise ValueError("build.rs requires an extended inventory")
        for name in ("Cargo.toml", "Cargo.lock"):
            paths[f"{label}/{name}"] = base / name
    for path in sorted(package.rglob("*")):
        if path.is_file() and (path.suffix in {".py", ".pyi"} or path.name == "py.typed"):
            paths[f"package/{path.relative_to(package).as_posix()}"] = path
    paths["backend/build_backend.py"] = project / "build_backend.py"
    paths["licenses/LICENSE"] = project / "LICENSE"
    paths["project/PYTHON-README.md"] = project / "PYTHON-README.md"
    for path in sorted((project / "licenses").rglob("*")):
        if path.is_file():
            paths[f"licenses/{path.relative_to(project / 'licenses').as_posix()}"] = path
    normalized = json.loads(json.dumps(config))
    normalized["tool"]["maturin"]["manifest-path"] = "<native>/Cargo.toml"
    normalized["tool"]["maturin"]["python-source"] = "<package-parent>"
    inventory = {"project/config": digest(canonical(normalized))}
    for name, path in paths.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or linked source input: " + name)
        if path.suffix not in TEXT_SUFFIXES and path.name != "py.typed" and not path.name.startswith(("LICENSE", "NOTICE", "COPYING")):
            raise ValueError("unreviewed text suffix: " + name)
        inventory[name] = digest(text_bytes(path))
    core_config = tomllib.loads((core / "Cargo.toml").read_text(encoding="utf-8"))
    versions = {"core": core_config["package"]["version"], "python": config["project"]["version"],
                "native": native_config["package"]["version"]}
    if versions["python"] != versions["native"]:
        raise ValueError("Python/native version mismatch")
    verify_licenses(project, native)
    return paths, {"versions": versions, "files": inventory, "sha256_lf": digest(canonical(inventory)),
                   "lock_sha256_lf": {k: inventory[f"{k}/Cargo.lock"] for k in ("core", "native")}}


def verify_licenses(project, native):
    locked = tomllib.loads((native / "Cargo.lock").read_text(encoding="utf-8"))["package"]
    expected = {(p["name"], p["version"], p["source"], p["checksum"]) for p in locked if "source" in p}
    notices = json.loads((project / "licenses/inventory.json").read_text(encoding="utf-8"))
    if {(p["name"], p["version"], p["source"], p["checksum"]) for p in notices} != expected:
        raise ValueError("stale third-party license inventory")
    for item in notices:
        for name, expected_hash in item["files"].items():
            path = project / "licenses" / f"{item['name']}-{item['version']}" / name
            if digest(text_bytes(path)) != expected_hash:
                raise ValueError("license content mismatch")


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def git_identity(core):
    try:
        top = Path(run("git", "-C", str(core), "rev-parse", "--show-toplevel")).resolve()
        if top != core.resolve():
            raise ValueError("parent repository is not source identity")
        commit = run("git", "-C", str(core), "rev-parse", "HEAD")
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("invalid Git revision")
        state = "dirty" if run("git", "-C", str(core), "status", "--porcelain", "--untracked-files=all") else "clean"
        return {"base_commit": commit, "state": state}
    except (OSError, ValueError, subprocess.CalledProcessError):
        return {"base_commit": None, "state": "unknown"}


def source_record(project):
    _, core, _, package, _, _ = layout(project)
    _, actual = inputs(project)
    frozen = package / RESOURCE
    if frozen.exists():
        if (core / ".git").exists() or not (project / "PKG-INFO").is_file():
            raise ValueError("frozen record is only valid in an extracted sdist, never a Git checkout")
        data = json.loads(frozen.read_text(encoding="utf-8"))
        if set(data) != {"schema", "artifact_kind", "source"} or data["schema"] != 1 or data["artifact_kind"] != "sdist":
            raise ValueError("not a frozen sdist source record")
        source = data["source"]
        if set(source) != set(actual) | {"git"} or any(source[k] != v for k, v in actual.items()):
            raise ValueError("sdist source provenance mismatch")
        git = source["git"]
        if set(git) != {"base_commit", "state"} or git["state"] not in {"clean", "dirty", "unknown"}:
            raise ValueError("invalid source state")
        if (git["state"] == "unknown" and git["base_commit"] is not None) or (git["state"] != "unknown" and not re.fullmatch(r"[0-9a-f]{40}", git["base_commit"] or "")):
            raise ValueError("invalid source commit")
        origin = "sdist"
    else:
        source = dict(actual, git=git_identity(core))
        origin = "checkout"
    expected = os.environ.get("SPATIAL_EXPECT_COMMIT")
    if expected and (source["git"] != {"base_commit": expected, "state": "clean"}):
        raise ValueError("readiness requires a clean exact source commit")
    return source, origin


def check_paths(raw, prefixes=()):
    for prefix in prefixes:
        if len(prefix) > 3:
            for candidate in {prefix, prefix.replace("\\", "/"), prefix.replace("/", "\\")}:
                for separator in ("/", "\\"):
                    text = candidate.rstrip("/\\") + separator
                    if text.encode().lower() in raw.lower() or text.encode("utf-16-le").lower() in raw.lower():
                        raise ValueError("local build path in package")
    generic = (rb"(?i)([a-z]:[\\/](?:users|git)[\\/]|/" + rb"home/[^/\x00\s]+/|/" +
               rb"Users/[^/\x00\s]+/|/github/" + rb"workspace|/runner/" + rb"work/)")
    if re.search(generic, raw):
        raise ValueError("generic local path in package")


def rewrite_wheel(path, extra):
    with zipfile.ZipFile(path) as archive:
        members = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/RECORD")}
        infos = {n: archive.getinfo(n) for n in archive.namelist()}
    members.update(extra)
    record = next(n.rsplit("/", 1)[0] + "/RECORD" for n in members if n.endswith(".dist-info/METADATA"))
    rows = []
    for name, raw in sorted(members.items()):
        encoded = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
        rows.append([name, "sha256=" + encoded, len(raw)])
    rows.append([record, "", ""])
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    members[record] = output.getvalue().encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            info = infos.get(name)
            if info is None:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)


def tool_hashes(sysroot):
    hashes = {}
    for tool in ("cargo", "rustc"):
        path = sysroot / "bin" / (tool + (".exe" if os.name == "nt" else ""))
        hashes[tool] = digest(path.read_bytes()) if path.is_file() else None
    if os.environ.get("SPATIAL_EXPECT_COMMIT") and not all(hashes.values()):
        raise ValueError("readiness requires compiler binary hashes")
    return hashes


def linux_tools():
    import platform
    if platform.system() != "Linux":
        return {}
    result = {}
    for name in ("cc", "readelf"):
        executable = shutil.which(name)
        if executable is None:
            if os.environ.get("SPATIAL_EXPECT_COMMIT"):
                raise ValueError("missing readiness native inspection tool")
            result[name] = None
        else:
            path = Path(executable).resolve()
            location = "image-gcc-toolset" if "/gcc-toolset-" in str(path) else "system-or-image"
            result[name] = {"executable":path.name,"path_class":location,"version":run(executable,"--version").splitlines()[0],"sha256":digest(path.read_bytes())}
    return result


def compiler_notices(sysroot):
    doc = sysroot / "share/doc/rust"
    paths = [doc / "COPYRIGHT-library.html", *sorted((doc / "licenses").glob("*.txt"))]
    if not paths[0].is_file() or len(paths) < 2:
        if os.environ.get("SPATIAL_EXPECT_COMMIT"):
            raise ValueError("readiness requires rust-docs compiler notices")
        return {}, {"state": "unavailable", "files": {}}
    resources = {"spatial_typestate/_compiler_notices/" + p.name: p.read_bytes() for p in paths}
    return resources, {"state": "present", "files": {k.rsplit("/", 1)[-1]: digest(v) for k, v in resources.items()}}


@contextmanager
def staging(project, source):
    project, core, native, package, _, _ = layout(project)
    paths, _ = inputs(project)
    with tempfile.TemporaryDirectory(prefix="spatial-build-") as temporary:
        root = Path(temporary)
        for path in paths.values():
            target = root / path.relative_to(core)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        staged_project = root / project.relative_to(core)
        shutil.copyfile(project / "pyproject.toml", staged_project / "pyproject.toml")
        shutil.copyfile(core / "README.md", root / "README.md")
        # Explicit [[bench]] in the unmodified core manifest must remain valid.
        if (core / "benches").exists():
            shutil.copytree(core / "benches", root / "benches")
        _, staged = inputs(staged_project)
        if staged != {k: source[k] for k in staged}:
            raise ValueError("staging altered source inputs")
        old_cwd = Path.cwd()
        try:
            os.chdir(staged_project)
            yield staged_project, root
        finally:
            os.chdir(old_cwd)


@contextmanager
def build_environment(core, stage, origin):
    overrides = {"RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "MATURIN_PEP517_ARGS", "RUSTC", "RUSTC_WRAPPER",
                 "RUSTC_WORKSPACE_WRAPPER", "CARGO_BUILD_TARGET", "CARGO_BUILD_RUSTFLAGS"}
    if any(value and (key in overrides or key.startswith("CARGO_PROFILE_") or (key.startswith("CARGO_TARGET_") and key.endswith("RUSTFLAGS"))) for key, value in os.environ.items()):
        raise ValueError("unaccounted external build flags")
    sysroot = Path(run("rustc", "--print", "sysroot"))
    prefixes = [str(Path.home()), os.environ.get("CARGO_HOME", str(Path.home() / ".cargo")),
                os.environ.get("RUSTUP_HOME", str(Path.home() / ".rustup")), str(sysroot), str(core), str(stage)]
    if os.environ.get("CARGO_TARGET_DIR"):
        prefixes.append(os.environ["CARGO_TARGET_DIR"])
    deny = origin == "checkout" or os.environ.get("SPATIAL_DENY_WARNINGS") == "1"
    flags = (["-Dwarnings"] if deny else []) + [f"--remap-path-prefix={p}=/redacted/{i}" for i, p in enumerate(prefixes)]
    update = {"CARGO_ENCODED_RUSTFLAGS": "\x1f".join(flags), "MATURIN_NO_INSTALL_RUST": "1", "CARGO_BUILD_JOBS": "2"}
    previous = {k: os.environ.get(k) for k in update}
    os.environ.update(update)
    try:
        yield sysroot, prefixes, deny
    finally:
        for k, value in previous.items():
            if value is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = value


def settings(config_settings):
    args = (config_settings or {}).get("build-args", "")
    if not isinstance(args, str) or re.search(r"[^\w\s.\-=]", args):
        raise ValueError("unsupported build settings")
    # Keep supported knobs small and recorded; no hidden feature/profile overrides.
    import shlex
    tokens = shlex.split(args)
    if set(config_settings or {}) - {"build-args"}:
        raise ValueError("unsupported build setting")
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--locked", action="store_true")
    parser.add_argument("--jobs", choices=["2"], default="2")
    parser.add_argument("--compatibility", choices=["manylinux_2_28", "off"], default="off")
    parser.add_argument("--auditwheel", choices=["check"])
    parsed = parser.parse_args(tokens)
    command = "--profile release --locked --jobs 2"
    if parsed.compatibility:
        command += " --compatibility " + parsed.compatibility
    if parsed.auditwheel:
        command += " --auditwheel " + parsed.auditwheel
    return {"build-args": command}


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    import maturin
    project = Path.cwd()
    source, origin = source_record(project)
    _, core, _, _, _, _ = layout(project)
    output = str(Path(wheel_directory).resolve())
    config = settings(config_settings)
    image = os.environ.get("SPATIAL_BUILD_IMAGE")
    if image and not re.fullmatch(r"quay\.io/pypa/manylinux_2_28_x86_64@sha256:[0-9a-f]{64}", image):
        raise ValueError("unreviewed build image identifier")
    with staging(project, source) as (staged_project, root):
        with build_environment(core, root, origin) as (sysroot, prefixes, deny):
            rust = run("rustc", "--version", "--verbose")
            tools = tool_hashes(sysroot)
            native_tools = linux_tools()
            notices, notice_record = compiler_notices(sysroot)
            name = maturin.build_wheel(output, config, metadata_directory)
            path = Path(output) / name
            with zipfile.ZipFile(path) as wheel:
                tags = [line[5:] for line in wheel.read(next(n for n in wheel.namelist() if n.endswith(".dist-info/WHEEL"))).decode().splitlines() if line.startswith("Tag: ")]
                for member in wheel.namelist():
                    check_paths(wheel.read(member), prefixes)
            record = {"schema": 1, "artifact_kind": "wheel", "source_origin": origin, "source": source,
                      "build": {"wrapper_version": WRAPPER_VERSION, "maturin": run("maturin", "--version"),
                                "rustc": rust, "cargo": run("cargo", "--version"),
                                "tool_sha256": tools,
                                "native_tools": native_tools,
                                "container_image": image,
                                "target": next(line[6:] for line in rust.splitlines() if line.startswith("host: ")),
                                "python": __import__("platform").python_version(), "profile": "release",
                                "features": ["pyo3/extension-module"], "locked": True, "deny_warnings": deny,
                                "path_remapping": "checkout-home-cargo-rustup-staging-v1",
                                "settings": config, "tags": tags, "compiler_notices": notice_record}}
            raw = canonical(record) + b"\n"
            check_paths(raw, prefixes)
            rewrite_wheel(path, dict(notices, **{"spatial_typestate/" + RESOURCE: raw}))
    if source_record(project)[0] != source:
        raise ValueError("source changed during build")
    return name


def build_sdist(sdist_directory, config_settings=None):
    import maturin
    project = Path.cwd()
    source, _ = source_record(project)
    output = str(Path(sdist_directory).resolve())
    with staging(project, source):
        name = maturin.build_sdist(output, config_settings)
    archive = Path(output) / name
    with tempfile.TemporaryDirectory(prefix="spatial-sdist-") as temporary:
        root = Path(temporary)
        with tarfile.open(archive) as tar:
            # Regular data only; avoids a Python-patch-version extraction API dependency.
            for member in tar:
                from pathlib import PurePosixPath
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts or "\\" in member.name or not (member.isdir() or member.isfile()):
                    raise ValueError("unsafe sdist member")
                target = root.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tar.extractfile(member).read())
        tree = next(root.iterdir())
        # No inherited development compiler or warning policy in source archives.
        for relative in ("rust-toolchain.toml", ".cargo/config.toml", "AGENTS.md", "CLAUDE.md"):
            (tree / relative).unlink(missing_ok=True)
        _, actual = inputs(tree)
        if actual != {k: source[k] for k in actual}:
            raise ValueError("maturin relocated source unexpectedly")
        package = layout(tree)[3]
        (package / RESOURCE).write_bytes(canonical({"schema": 1, "artifact_kind": "sdist", "source": source}) + b"\n")
        def normalized_header(info):
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            info.pax_headers = {}
            info.mode = 0o755 if info.isdir() else 0o644
            return info
        import gzip
        with archive.open("wb") as file:
            with gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as tar:
                    tar.add(tree, arcname=tree.name, filter=normalized_header)
    if source_record(project)[0] != source:
        raise ValueError("source changed during sdist build")
    return name


def project_prepared_tag(path, compatibility, system):
    if system != "linux" or compatibility != "manylinux_2_28":
        return
    # maturin 1.16 tags_from_bridge() hardcodes PlatformTag::Linux during prepare:
    # https://github.com/PyO3/maturin/blob/v1.16.0/src/build_orchestrator.rs
    # This projects intent only. Final build/audit and strict parity independently
    # establish the actual tag; unexpected/upstream-fixed metadata must fail here.
    old = b"Tag: cp311-abi3-linux_x86_64"
    new = b"Tag: cp311-abi3-manylinux_2_28_x86_64"
    lines = path.read_bytes().splitlines(keepends=True)
    if [line.rstrip(b"\r\n") for line in lines if line.startswith(b"Tag: ")] != [old]:
        raise ValueError("unreviewed maturin prepared tag")
    path.write_bytes(b"".join(line.replace(old,new,1) if line.rstrip(b"\r\n")==old else line for line in lines))


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    import maturin
    project = Path.cwd()
    source, origin = source_record(project)
    core = layout(project)[1]
    output = str(Path(metadata_directory).resolve())
    import shlex
    tokens = shlex.split(settings(config_settings)["build-args"])
    compatibility = tokens[tokens.index("--compatibility") + 1] if "--compatibility" in tokens else "off"
    metadata_args = "--locked --compatibility " + compatibility
    if "--auditwheel" in tokens:
        metadata_args += " --auditwheel " + tokens[tokens.index("--auditwheel") + 1]
    with staging(project, source) as (_, root):
        with build_environment(core, root, origin):
            name = maturin.prepare_metadata_for_build_wheel(output, {"build-args": metadata_args})
            project_prepared_tag(Path(output)/name/"WHEEL",compatibility,__import__("sys").platform)
            return name


def get_requires_for_build_wheel(config_settings=None):
    return []  # Missing installed Rust is an error, never an implicit installer.


get_requires_for_build_sdist = get_requires_for_build_wheel


def build_editable(*args, **kwargs):
    raise ValueError("editable builds bypass immutable artifact evidence; use an installed development wheel")

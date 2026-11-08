"""Public checks and exact-file staging for the one approved 0.1.0 publication.

Registry credentials are handled only by Cargo and the official PyPA action.
This module never reads those credentials or performs an authenticated request.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import venv


spec = importlib.util.spec_from_file_location("qualification", Path(__file__).with_name("candidate_qualification.py"))
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
PROJECT = "spatial-typestate"
MANIFEST = "Cargo.toml"
HASH = "sha256"
CRATE = "spatial-typestate-0.1.0.crate"
CRATE_SHA = "fc6b60a9a7f3aa44122e51473cbe52026ae6330826b15401610489ca0b355abf"
LINUX = "spatial_typestate-0.1.0-cp311-abi3-manylinux_2_28_x86_64.whl"
SDIST = "spatial_typestate-0.1.0.tar.gz"
PYTHON_FILES = {LINUX: "e591cc87071cdc7db9e1ff162d11d661f1e6854ab1c6cfbf96473cde7e57ebd5",
                q.WHEEL: q.WHEEL_SHA,
                SDIST: "d94f841d8ab4368de4994b071f9d035fe5260feba2e50157200a9467d51e9448"}
OWNER = "joey-huckabee"
CRATES = "https://crates.io/api/v1/crates/" + PROJECT
PYPI = "https://pypi.org/pypi/" + PROJECT
INDEX = "https://index.crates.io/sp/at/spatial-typestate"
DOWNLOAD = "https://static.crates.io/crates/spatial-typestate/" + CRATE
REGISTRY = "registry+https://github.com/rust-lang/crates.io-index"
PUBLIC_HOSTS = {"crates.io", "pypi.org", "files.pythonhosted.org", "index.crates.io", "static.crates.io"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        raise ValueError("public registry redirect rejected")


def public(url, missing=False):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in PUBLIC_HOSTS
            or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("unexpected public registry URL")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "spatial-typestate-publication/0.1.0"})
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("public registry response too large")
            return raw
    except urllib.error.HTTPError as error:
        if error.code == 404 and missing:
            return None
        raise ValueError("public registry HTTP status " + str(error.code)) from None


def public_json(url, missing=False):
    raw = public(url, missing)
    return None if raw is None else json.loads(raw)


def execution_guard():
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"
            or os.environ.get("PUBLICATION_GUARD") != "approved-9974fd6-once"):
        raise ValueError("publication requires the reviewed one-time main dispatch")


def gate():
    execution_guard()
    for flag, name in (("CARGO_PRESENT", "CARGO_REGISTRY_TOKEN"), ("PYPI_PRESENT", "PYPI_API_TOKEN")):
        if os.environ.get(flag) != "true":
            raise ValueError(name + " is not configured")


def rust_absent():
    data = public_json(CRATES)
    if any(v["num"] == q.VERSION for v in data["versions"]):
        raise ValueError("Rust version already exists; inspect public state before any retry")
    owners = public_json(CRATES + "/owners")["users"]
    if [u["login"] for u in owners] != [OWNER]:
        raise ValueError("crate ownership changed")


def all_absent():
    rust_absent()
    if public_json(PYPI + "/json", missing=True) is not None:
        raise ValueError("PyPI project exists; inspect public state before any retry")


def stage_python(temporary, destination):
    # Download roots and filenames are fixed; never select a rebuilt/Windows sdist.
    roots = {LINUX: "source-ubuntu", SDIST: "source-ubuntu", q.WHEEL: "source-windows"}
    selected = {name: temporary / roots[name] / name for name in PYTHON_FILES}
    for name, path in selected.items():
        if not path.is_file() or path.is_symlink() or q.sha(path) != PYTHON_FILES[name]:
            raise ValueError("selected Python artifact hash mismatch")
    destination.mkdir()
    for name, path in selected.items():
        shutil.copyfile(path, destination / name)
    if {p.name for p in destination.iterdir()} != set(PYTHON_FILES):
        raise ValueError("unexpected Python publish file")


def package_guard(temporary, evidence):
    q.validate_source(q.SOURCE)
    target = temporary / "publication-cargo-target"
    q.execute(["cargo", q.TOOLCHAIN, "package", "--locked", "--jobs", "2", "--target-dir", target],
              q.SOURCE, evidence / "package-guard.log")
    path = target / "package" / CRATE
    if q.sha(path) != CRATE_SHA:
        raise ValueError("Cargo archive differs from owner-approved bytes; do not publish")
    import tarfile
    with tarfile.open(path) as archive:
        files = q.archive_files(archive)
    q.validate_crate(files, q.SOURCE)
    q.validate_source(q.SOURCE)
    return {HASH: CRATE_SHA, "vcs": json.loads(files[".cargo_vcs_info.json"])}


def python_release():
    data = public_json(PYPI + "/0.1.0/json", missing=True)
    if data is None:
        return None
    if data["info"]["name"] != PROJECT or data["info"]["version"] != q.VERSION:
        raise ValueError("wrong PyPI project identity")
    if {s.strip() for s in data["info"]["requires_python"].split(",")} != {">=3.11", "<3.15"}:
        raise ValueError("Python support metadata changed")
    files = {f["filename"]: f for f in data["urls"]}
    if len(files) != len(data["urls"]) or set(files) != set(PYTHON_FILES):
        raise ValueError("PyPI file set differs; inspect partial publication")
    for name, digest in PYTHON_FILES.items():
        if files[name]["digests"][HASH] != digest or files[name]["yanked"]:
            raise ValueError("PyPI checksum or yanked status differs")
    return files


def wait_python():
    # Bounded public reads for propagation, never retries an upload.
    for attempt in range(6):
        result = python_release()
        if result is not None:
            return result
        if attempt < 5:
            time.sleep(5)
    raise ValueError("PyPI version not visible; inspect public state before any retry")


def verify_python(evidence):
    files = wait_python()
    for name, info in files.items():
        raw = public(info["url"])
        if hashlib.sha256(raw).hexdigest() != PYTHON_FILES[name]:
            raise ValueError("downloaded PyPI artifact differs")
        (evidence / name).write_bytes(raw)
    return {name: info["digests"][HASH] for name, info in files.items()}


def verify_crate(evidence):
    # crates.io can acknowledge the upload before its index is updated.
    versions = []
    for attempt in range(6):
        versions = [json.loads(line) for line in public(INDEX).splitlines()]
        if any(v["vers"] == q.VERSION for v in versions):
            break
        if attempt < 5:
            time.sleep(5)
    version = next((v for v in versions if v["vers"] == q.VERSION), None)
    if not version or version["cksum"] != CRATE_SHA or version["yanked"]:
        raise ValueError("crates.io index differs or not visible; inspect public state, do not republish")
    raw = public(DOWNLOAD)
    if hashlib.sha256(raw).hexdigest() != CRATE_SHA:
        raise ValueError("published crate differs; stop, any yank requires owner decision")
    (evidence / CRATE).write_bytes(raw)
    return {HASH: CRATE_SHA, "index_checksum": version["cksum"]}


def installed(evidence, temporary):
    files = wait_python()
    name = q.WHEEL if sys.platform == "win32" else LINUX
    raw = public(files[name]["url"])
    if hashlib.sha256(raw).hexdigest() != PYTHON_FILES[name]:
        raise ValueError("public wheel hash differs")
    with tempfile.TemporaryDirectory(prefix="public-python-", dir=temporary) as d:
        root = Path(d)
        wheel = root / name
        wheel.write_bytes(raw)
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(root / "venv")
        python = root / ("venv/Scripts/python.exe" if sys.platform == "win32" else "venv/bin/python")
        assets, cwd = root / "assets", root / "cwd"
        cwd.mkdir()
        q.copy_test_assets(q.SOURCE, assets)
        # Install the freshly public-downloaded bytes; no local candidate fallback.
        q.execute([python, "-m", "pip", "--isolated", "install", "--no-deps", wheel], cwd, evidence / "public-install.log")
        probe = q.installed_probe(python, cwd, evidence)
        q.installed_suite(python, assets, cwd, evidence, "public-stdlib")
        return {"wheel": name, HASH: PYTHON_FILES[name], "installed": probe}


def registry_consumer(evidence, temporary):
    for mode in ("std", "no_std"):
        with tempfile.TemporaryDirectory(prefix="registry-consumer-", dir=temporary) as d:
            root = Path(d)
            (root / "src").mkdir()
            value = '"=0.1.0"' if mode == "std" else '{version="=0.1.0",default-features=false,features=["no_std"]}'
            (root / MANIFEST).write_text('[package]\nname="public-consumer"\nversion="0.0.0"\nedition="2024"\n[dependencies]\nspatial-typestate=' + value + '\n', encoding="utf-8")
            (root / "src/main.rs").write_text(q.SMOKE, encoding="utf-8")
            q.execute(["cargo", q.TOOLCHAIN, "generate-lockfile"], root, evidence / (mode + "-lock.log"))
            raw = q.execute(["cargo", q.TOOLCHAIN, "metadata", "--locked", "--format-version", "1"], root, evidence / (mode + "-metadata.json"))
            packages = json.loads(raw)["packages"]
            core = [p for p in packages if p["name"] == PROJECT]
            if len(core) != 1 or core[0]["version"] != q.VERSION or core[0]["source"] != REGISTRY:
                raise ValueError("consumer did not resolve the public registry crate")
            locked = tomllib.loads((root / "Cargo.lock").read_text(encoding="utf-8"))["package"]
            selected = [item for item in locked if item["name"] == PROJECT]
            if len(selected) != 1 or selected[0].get("checksum") != CRATE_SHA or selected[0].get("source") != REGISTRY:
                raise ValueError("public consumer lock checksum differs")
            q.execute(["cargo", q.TOOLCHAIN, "run", "--locked", "--jobs", "2"], root, evidence / (mode + "-consumer.log"))
    return {"modes": ["std", "no_std"], "library_dependency": "crates.io =0.1.0", "binaries_use_std": True}


def main():
    mode = sys.argv[1:]
    if mode == ["gate"]:
        gate()
        return
    execution_guard()
    temporary = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    evidence = temporary / "publication-evidence"
    evidence.mkdir(mode=0o700, exist_ok=True)
    q.validate_source(q.SOURCE)
    if mode == ["preflight"]:
        all_absent()
        original = temporary / "qualified-crate" / CRATE
        if not original.is_file() or q.sha(original) != CRATE_SHA:
            raise ValueError("qualified crate download differs")
        stage_python(temporary, Path(os.environ["GITHUB_WORKSPACE"]) / "preflight-dist")
        result = package_guard(temporary, evidence)
    elif mode == ["stage-python"]:
        all_absent()
        stage_python(temporary, Path(os.environ["GITHUB_WORKSPACE"]) / "publish-dist")
        result = {"python_file_hashes": PYTHON_FILES}
    elif mode == ["verify-python"]:
        result = verify_python(evidence)
    elif mode == ["crate-guard"]:
        verify_python(evidence)
        rust_absent()
        result = package_guard(temporary, evidence)
    elif mode == ["verify-crate"]:
        result = verify_crate(evidence)
    elif mode == ["installed"]:
        result = installed(evidence, temporary)
    elif mode == ["registry-consumer"]:
        result = registry_consumer(evidence, temporary)
    else:
        raise ValueError("unknown fixed publication check")
    q.validate_source(q.SOURCE)
    record = {"source_commit": q.SOURCE_COMMIT, "publication_tooling_commit": os.environ["GITHUB_SHA"], "mode": mode[0], "result": result}
    (evidence / (mode[0] + ".json")).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()

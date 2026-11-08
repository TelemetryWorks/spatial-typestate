"""Stdlib artifact gates; readelf is used only for Linux ELF inspection."""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile

from build_backend import check_paths, digest


METADATA_SUFFIX = ".dist-info/METADATA"

def needed_libraries(dynamic):
    """Parse each NEEDED line with bounded scans, preserving bracket semantics."""
    result = []
    for line in dynamic.split("\n"):
        start = line.find("(NEEDED)")
        if start < 0:
            continue
        closing = line.rfind("]")
        if closing < start:
            continue
        opening = line.rfind("[", start + len("(NEEDED)"), closing)
        if opening >= 0:
            result.append(line[opening + 1:line.find("]", opening + 1)])
    return result


def elf_report(path):
    def read(*options):
        return subprocess.check_output(["readelf", *options, str(path)], text=True)
    header, dynamic, versions = read("-h"), read("-d"), read("--version-info")
    if "Advanced Micro Devices X86-64" not in header or "ELF64" not in header:
        raise ValueError("unexpected ELF architecture")
    needed = sorted(set(needed_libraries(dynamic)))
    if not needed or len(re.findall(r"\(NEEDED\)", dynamic)) != len(needed):
        raise ValueError("missing/unparsed ELF dynamic requirements")
    allowed = {"libgcc_s.so.1", "libc.so.6", "libm.so.6", "libdl.so.2", "librt.so.1", "libpthread.so.0", "ld-linux-x86-64.so.2"}
    if set(needed) - allowed:
        raise ValueError("unexpected dynamic library")
    required = sorted(set(re.findall(r"Name: (\S+)", versions)))
    if not required or not any(name.startswith("GLIBC_") for name in required):
        raise ValueError("missing ELF version requirements")
    validate_versions(required)
    return {"needed": needed, "version_needs": required, "architecture": "x86_64", "glibc_ceiling": "2.28"}


def validate_versions(required):
    ceilings = {"GLIBC": (2, 28), "GCC": (4, 2, 0)}
    for name in required:
        match = re.fullmatch(r"([A-Z]+)_([0-9.]+)", name)
        if not match or match[1] not in ceilings:
            raise ValueError("unreviewed ELF version namespace: " + name)
        actual = tuple(map(int, match[2].split(".")))
        ceiling = ceilings[match[1]]
        length = max(len(actual), len(ceiling))
        if actual + (0,) * (length-len(actual)) > ceiling + (0,) * (length-len(ceiling)):
            raise ValueError("ELF requirement exceeds baseline: " + name)


def validate_metadata(names, metadata):
    if metadata.get_all("Requires-Dist") or metadata["License-Expression"] != "Apache-2.0":
        raise ValueError("unexpected wheel runtime dependencies/license")
    for relative in metadata.get_all("License-File", []):
        prefix = next(n.split("/", 1)[0] for n in names if n.endswith(METADATA_SUFFIX))
        if f"{prefix}/licenses/{relative}" not in names:
            raise ValueError("missing declared license file")


def validate_record(archive, names):
    record_name = next(n for n in names if n.endswith(".dist-info/RECORD"))
    rows = list(csv.reader(io.StringIO(archive.read(record_name).decode())))
    if {r[0] for r in rows} != set(names) or len(rows) != len(names):
        raise ValueError("incomplete RECORD")
    for name, hashed, size in rows:
        raw = archive.read(name)
        if name == record_name:
            if hashed or size:
                raise ValueError("self-hashed RECORD")
            continue
        expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
        if hashed != expected or size != str(len(raw)):
            raise ValueError("RECORD mismatch")


def validate_wheel_tags(path, archive, names, provenance):
    wheel_tags = [line[5:] for line in archive.read(next(n for n in names if n.endswith(".dist-info/WHEEL"))).decode().splitlines() if line.startswith("Tag: ")]
    filename_tags = path.name[:-4].rsplit("-",3)[-3:]
    if len(filename_tags) != 3 or filename_tags[:2] != ["cp311","abi3"]:
        raise ValueError("unexpected filename ABI tags")
    if wheel_tags != ["-".join(filename_tags)] or wheel_tags != provenance["build"]["tags"]:
        raise ValueError("filename/WHEEL/provenance tags disagree")
    linux = filename_tags[2].startswith(("linux", "manylinux"))
    expected_platform = "manylinux_2_28_x86_64" if linux else "win_amd64"
    if filename_tags[2] != expected_platform:
        raise ValueError("unexpected platform tag")
    native_names = [n for n in names if n.endswith((".so", ".pyd"))]
    suffix = ".so" if linux else ".pyd"
    if len(native_names) != 1 or not native_names[0].startswith("spatial_typestate/_native") or not native_names[0].endswith(suffix):
        raise ValueError("expected exactly one platform native library")


def validate_licenses(archive, names, metadata, source):
    expected_licenses = {"LICENSE" if key=="licenses/LICENSE" else key for key in source["files"] if key.startswith("licenses/")}
    if not {"LICENSE","licenses/inventory.json"}.issubset(expected_licenses) or set(metadata.get_all("License-File",[])) != expected_licenses:
        raise ValueError("license inventory/metadata mismatch")
    prefix=next(n.split("/",1)[0] for n in names if n.endswith(METADATA_SUFFIX))
    for relative in expected_licenses:
        key="licenses/LICENSE" if relative=="LICENSE" else relative
        if digest(archive.read(f"{prefix}/licenses/{relative}").replace(b"\r\n",b"\n"))!=source["files"][key]:
            raise ValueError("packaged license hash mismatch")


def validate_compiler_notices(archive, provenance):
    if provenance["build"]["compiler_notices"]["state"] != "present":
        raise ValueError("compiler notices unavailable: not readiness artifact")
    hashes=provenance["build"]["tool_sha256"]
    if set(hashes)!={"cargo","rustc"} or not all(re.fullmatch(r"[0-9a-f]{64}",value or "") for value in hashes.values()):
        raise ValueError("compiler binary hashes unavailable")
    notices=provenance["build"]["compiler_notices"]["files"]
    if "COPYRIGHT-library.html" not in notices or len(notices)<2:
        raise ValueError("incomplete compiler notices")
    for name,expected in notices.items():
        if digest(archive.read("spatial_typestate/_compiler_notices/"+name))!=expected:
            raise ValueError("compiler notice hash mismatch")


def inspect_wheel_members(archive, names, provenance):
    import tempfile
    prefixes = [str(Path.home()), os.environ.get("CARGO_HOME", str(Path.home()/".cargo")),
                os.environ.get("RUSTUP_HOME", str(Path.home()/".rustup")), str(Path.cwd())]
    native_reports = []
    for name in names:
        raw = archive.read(name)
        check_paths(raw, prefixes)
        if name.endswith(".so"):
            if not all("manylinux_2_28_x86_64" in t for t in provenance["build"]["tags"]):
                raise ValueError("unexpected Linux tag")
            with tempfile.TemporaryDirectory() as tmp:
                native = Path(tmp)/"native.so"; native.write_bytes(raw)
                native_reports.append(elf_report(native))
    return native_reports


def wheel_report(path, expected_commit=None):
    from email.parser import BytesParser
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError("duplicate wheel member")
        metadata = BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith(METADATA_SUFFIX))))
        validate_metadata(names, metadata)
        validate_record(archive, names)
        for required in ("spatial_typestate/_native.pyi", "spatial_typestate/py.typed", "spatial_typestate/_provenance.json"):
            if required not in names:
                raise ValueError("missing package evidence")
        provenance = json.loads(archive.read("spatial_typestate/_provenance.json"))
        validate_wheel_tags(path, archive, names, provenance)
        source = provenance["source"]
        from build_backend import canonical
        if source["sha256_lf"] != digest(canonical(source["files"])):
            raise ValueError("invalid source aggregate")
        validate_licenses(archive, names, metadata, source)
        validate_compiler_notices(archive, provenance)
        if expected_commit and source["git"] != {"base_commit": expected_commit, "state": "clean"}:
            raise ValueError("not the expected clean commit")
        native_reports = inspect_wheel_members(archive, names, provenance)
        return {"filename": path.name, "kind": "wheel", "sha256": digest(path.read_bytes()), "size": path.stat().st_size,
                "source_sha256_lf": source["sha256_lf"], "tags": provenance["build"]["tags"],
                "source_git": source["git"], "versions": source["versions"], "build": provenance["build"],
                "licenses": sorted(n for n in names if "/licenses/" in n or "/_compiler_notices/" in n),
                "elf": native_reports, "all_record_hashes": "verified"}


def validate_source_member(member, allowed):
    from pathlib import PurePosixPath
    parts=PurePosixPath(member.name).parts
    if not parts or PurePosixPath(member.name).is_absolute() or ".." in parts or "\\" in member.name:
        raise ValueError("invalid source archive path")
    if len(parts)>1 and parts[1] not in allowed:
        raise ValueError("unintended source archive top-level member")
    if (member.uid,member.gid,member.uname,member.gname,member.mtime)!=(0,0,"","",0) or member.pax_headers:
        raise ValueError("source archive header leaks build identity")
    if not (member.isfile() or member.isdir()) or member.mode!=(0o644 if member.isfile() else 0o755):
        raise ValueError("unexpected source member mode/type")


def sdist_report(path):
    import tarfile
    allowed = {"Cargo.lock","Cargo.toml","LICENSE","PKG-INFO","PYTHON-README.md","README.md",
               "benches","build_backend.py","licenses","pyproject.toml","python","src"}
    prefixes = [str(Path.home()),str(Path.cwd()),os.environ.get("CARGO_HOME",str(Path.home()/".cargo")),
                os.environ.get("RUSTUP_HOME",str(Path.home()/".rustup"))]
    files=[]
    with tarfile.open(path) as archive:
        for member in archive:
            validate_source_member(member, allowed)
            check_paths(canonical_header(member),prefixes)
            if member.isfile():
                check_paths(archive.extractfile(member).read(),prefixes)
                files.append(member.name)
    return {"filename":path.name,"kind":"sdist","sha256":digest(path.read_bytes()),"size":path.stat().st_size,"files":files,
            "headers":"normalized","path_scan":"verified"}


def canonical_header(member):
    return json.dumps({"name":member.name,"uname":member.uname,"gname":member.gname,"pax":member.pax_headers},sort_keys=True).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expect-commit")
    args = parser.parse_args()
    reports = [wheel_report(p, args.expect_commit) for p in sorted(args.directory.glob("*.whl"))]
    for p in sorted(args.directory.glob("*.tar.gz")):
        reports.append(sdist_report(p))
    if not reports:
        raise ValueError("no build artifacts")
    (args.directory/"artifact-inventory.json").write_text(json.dumps(reports,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()

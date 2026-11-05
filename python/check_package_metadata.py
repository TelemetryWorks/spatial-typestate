"""Check sdist/wheel metadata parity and vendored source identity after rebuild."""
from email.parser import BytesParser
import json
from pathlib import Path
import sys
import tarfile
import zipfile
from verify_artifacts import sdist_report


def wheel(path):
    with zipfile.ZipFile(path) as z:
        metadata=BytesParser().parsebytes(z.read(next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))))
        provenance=json.loads(z.read("spatial_typestate/_provenance.json"))
    return metadata,provenance


def verify_prepared(directory):
    prepared=BytesParser().parsebytes(next((directory/"prepared").rglob("METADATA")).read_bytes())
    built,_=wheel(next(directory.glob("*.whl")))
    for key in set(prepared.keys())|set(built.keys()):
        if sorted(prepared.get_all(key,[]))!=sorted(built.get_all(key,[])):
            raise ValueError("prepared/wheel metadata mismatch: "+key)
    if prepared.get_payload()!=built.get_payload():
        raise ValueError("prepared/wheel README mismatch")
    info=next((directory/"prepared").iterdir())
    with zipfile.ZipFile(next(directory.glob("*.whl"))) as z:
        prepared_files={info.name+"/"+p.relative_to(info).as_posix() for p in info.rglob("*") if p.is_file()}
        wheel_files={name for name in z.namelist() if name.startswith(info.name+"/") and not name.endswith("/")} - {info.name+"/RECORD"}
        if prepared_files!=wheel_files:
            raise ValueError("prepared/wheel dist-info file set mismatch")
        for path in info.rglob("*"):
            if path.is_file() and z.read(info.name+"/"+path.relative_to(info).as_posix())!=path.read_bytes():
                raise ValueError("prepared/wheel file mismatch: "+path.name)
    print("PASS prepared/build wheel metadata parity")


def verify(directory):
    sdist_report(next(directory.glob("*.tar.gz")))
    with tarfile.open(next(directory.glob("*.tar.gz"))) as t:
        names=t.getnames()
        info=BytesParser().parsebytes(t.extractfile(next(n for n in names if n.endswith("/PKG-INFO"))).read())
        source=json.load(t.extractfile(next(n for n in names if n.endswith("/spatial_typestate/_provenance.json"))))
        for n in names:
            parts=Path(n).parts[1:]
            if n.endswith(("rust-toolchain.toml",".cargo/config.toml","AGENTS.md","CLAUDE.md")) or (parts and parts[0] in {"tests","docs","scripts"}):
                raise ValueError("unintended development source member")
        if source["artifact_kind"]!="sdist" or "build" in source:
            raise ValueError("sdist must contain source identity only")
        if any("_compiler_notices" in n for n in names):
            raise ValueError("compiler build notices in source archive")
    rebuilt=next((directory/"from-sdist").glob("*.whl"))
    metadata,provenance=wheel(rebuilt)
    if provenance["source_origin"]!="sdist" or provenance["source"]!=source["source"]:
        raise ValueError("source rebuild changed identity")
    if wheel(next(directory.glob("*.whl")))[1]["source"]!=source["source"]:
        raise ValueError("checkout wheel/source archive differ")
    dynamic={s.lower() for s in info.get_all("Dynamic",[])}
    for key in set(info.keys())|set(metadata.keys()):
        if key.lower() not in dynamic and key.lower()!="dynamic":
            if sorted(info.get_all(key,[]))!=sorted(metadata.get_all(key,[])):
                raise ValueError("sdist/wheel metadata mismatch: "+key)
    if info.get_payload()!=metadata.get_payload():
        raise ValueError("sdist/wheel README mismatch")
    print("PASS source identity, intentional archive contents and all static metadata (including licenses)")


if __name__=="__main__":
    if sys.argv[1]=="--prepared": verify_prepared(Path(sys.argv[2]))
    else: verify(Path(sys.argv[1]))

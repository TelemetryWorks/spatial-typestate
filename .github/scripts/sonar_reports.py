"""Token-free report generation/normalization. Never run in the scanner job."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


REPORTS = ("core-std.lcov", "core-no-std.lcov", "native.lcov",
           "clippy-core-std.jsonl", "clippy-core-no-std.jsonl", "clippy-native.jsonl",
           "python-coverage.xml")


def clippy_outcome(path, exit_code):
    try:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, ValueError):
        return {"exit_code": exit_code, "kind": "tool-error", "warnings": 0, "errors": 0}
    messages = [r["message"] for r in records if r.get("reason") == "compiler-message"]
    errors = [m for m in messages if m.get("level") == "error"]
    warnings = [m for m in messages if m.get("level") == "warning"]
    finished = [r for r in records if r.get("reason") == "build-finished"]
    lint_exit = bool(errors) and all((m.get("code") or {}).get("code", "").startswith("clippy::") for m in errors)
    valid = len(finished) == 1 and ((exit_code == 0 and finished[0].get("success") is True and not errors)
                                   or (exit_code != 0 and lint_exit and finished[0].get("success") is False))
    kind = "tool-error" if not valid else "lint-findings" if errors or warnings else "clean"
    return {"exit_code": exit_code, "kind": kind, "warnings": len(warnings), "errors": len(errors)}


def source_path(value, root, base=None):
    """Map only real checkout files; never strip an arbitrary absolute prefix."""
    root = root.resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (base or root) / candidate
    candidate = candidate.resolve(strict=True)
    relative = candidate.relative_to(root)
    if not candidate.is_file() or any(part.startswith(".") and part != ".github"
                                      for part in relative.parts):
        raise ValueError("not an allowed source file")
    return relative.as_posix()


def normalize_lcov(path, root):
    lines = path.read_text(encoding="utf-8").splitlines()
    files = []
    for i, line in enumerate(lines):
        if line.startswith("SF:"):
            value = source_path(line[3:], root)
            if not value.endswith(".rs"):
                raise ValueError("non-Rust LCOV source")
            files.append(value)
            lines[i] = "SF:" + value
    if not files:
        raise ValueError("LCOV has no source files")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sorted(set(files))


def normalize_clippy(path, root, manifest_base):
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        # Cargo artifact/progress objects are not Clippy findings. Keep every
        # diagnostic and the actual final success value, without severity filters.
        if record.get("reason") == "compiler-message":
            message = record["message"]
            def map_spans(node):
                for span in node.get("spans", []):
                    span["file_name"] = source_path(span["file_name"], root, manifest_base)
                    if span.get("expansion"):
                        raise ValueError("macro expansion span needs reviewed path mapping")
                for child in node.get("children", []):
                    map_spans(child)
            map_spans(message)
            if "manifest_path" in record:
                record["manifest_path"] = source_path(record["manifest_path"], root, manifest_base)
            if record.get("target", {}).get("src_path"):
                record["target"]["src_path"] = source_path(record["target"]["src_path"], root, manifest_base)
            records.append(record)
        elif record.get("reason") == "build-finished":
            records.append(record)
    if not any(r.get("reason") == "build-finished" for r in records):
        raise ValueError("Clippy report lacks completion status")
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def normalize_python(path, root):
    data = path.read_text(encoding="utf-8")
    if "<!DOCTYPE" in data.upper() or "<!ENTITY" in data.upper():
        raise ValueError("XML declarations/entities forbidden")
    tree = ET.fromstring(data)
    files = []
    for node in tree.findall(".//class"):
        value = node.attrib["filename"]
        # Coverage aliases produce one of these checkout-relative spellings.
        candidates = [root / value, root / "python" / value,
                      root / "python/src" / value, root / "python/src/spatial_typestate" / value]
        resolved = {source_path(p, root) for p in candidates if p.is_file()}
        if len(resolved) != 1:
            raise ValueError("ambiguous/unmapped Python coverage source")
        node.attrib["filename"] = resolved.pop()
        files.append(node.attrib["filename"])
    if not files:
        raise ValueError("Python coverage has no files")
    sources = tree.find("sources")
    if sources is not None:
        sources.clear()
        ET.SubElement(sources, "source").text = "."
    path.write_text(ET.tostring(tree, encoding="unicode") + "\n", encoding="utf-8")
    return sorted(set(files))


def generate(root, output, revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid source revision")
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("report output must be outside checkout")
    output.mkdir(parents=True, exist_ok=False)
    statuses = {}
    clippy = {}
    env = os.environ.copy()
    env.update(CARGO_BUILD_JOBS="2", RUSTUP_TOOLCHAIN="1.99.0", RUSTUP_AUTO_INSTALL="0")
    def run(name, args, destination=None, extra=None):
        command_env = env | (extra or {})
        try:
            if destination:
                with destination.open("w", encoding="utf-8") as stream:
                    result = subprocess.run(args, cwd=root, env=command_env, stdout=stream, check=False)
            else:
                result = subprocess.run(args, cwd=root, env=command_env, check=False)
            status = result.returncode
        except OSError:
            status = 127
        statuses[name] = status
        return status
    for name, features, manifest in [
            ("core-std", ["--all-features"], []),
            ("core-no-std", ["--no-default-features", "--features", "no_std"], []),
            ("native", [], ["--manifest-path", "python/native/Cargo.toml"])]:
        run(name, ["cargo", "+1.99.0", "llvm-cov", *manifest, "--locked", "--jobs", "2",
                   *features, "--lcov", "--output-path", str(output / (name + ".lcov")),
                   "--", "--test-threads=2"], extra={"RUSTFLAGS": "-Dwarnings"})
        status = run("clippy-" + name,
            ["cargo", "+1.99.0", "clippy", *manifest, "--locked", "--jobs", "2",
             "--all-targets", *features, "--message-format=json"],
            output / ("clippy-" + name + ".jsonl"), extra={"RUSTFLAGS": ""})
        # Report-only severity: an empty RUSTFLAGS intentionally removes the
        # checkout's global -Dwarnings promotion for THIS subprocess. Lint rules
        # still run and every diagnostic is kept. ci.yml remains the strict gate.
        clippy["clippy-" + name] = clippy_outcome(output / ("clippy-" + name + ".jsonl"), status)
    wheels = output.parent / "sonar-wheels"
    wheels.mkdir(exist_ok=False)
    run("wheel-build", [sys.executable, "-m", "pip", "wheel", "--no-deps",
                       "--no-build-isolation", str(root / "python"), "-w", str(wheels)])
    candidates = list(wheels.glob("*.whl"))
    if len(candidates) == 1 and statuses["wheel-build"] == 0:
        run("wheel-install", [sys.executable, "-m", "pip", "install", "--no-deps", str(candidates[0])])
    else:
        statuses["wheel-install"] = 1
    coverage_env = {"COVERAGE_FILE": str(output.parent / ".sonar-coverage")}
    config = str(root / ".github/security/coverage.ini")
    for name, directory in [("packaging", "python/packaging_tests"),
                            ("pipeline", ".github/scripts"), ("wheel", "python/tests")]:
        run("python-" + name, [sys.executable, "-I", "-m", "coverage", "run",
                              "--rcfile=" + config, "-m", "unittest", "discover", "-s", directory, "-v"],
            extra=coverage_env)
    run("coverage-combine", [sys.executable, "-m", "coverage", "combine", "--rcfile=" + config],
        extra=coverage_env)
    run("coverage-xml", [sys.executable, "-m", "coverage", "xml", "--rcfile=" + config,
                         "-o", str(output / "python-coverage.xml")], extra=coverage_env)
    (output.parent / "generation-status.json").write_text(json.dumps(statuses, indent=2) + "\n", encoding="utf-8")
    (output.parent / "clippy-status.json").write_text(json.dumps(clippy, indent=2) + "\n", encoding="utf-8")
    if any(value != 0 for name, value in statuses.items() if name not in clippy) or any(outcome["kind"] == "tool-error" for outcome in clippy.values()):
        raise RuntimeError("report generation failed; inspect phase statuses and retained diagnostics")
    paths = {}
    for name in REPORTS[:3]:
        paths[name] = normalize_lcov(output / name, root)
    for name in REPORTS[3:6]:
        normalize_clippy(output / name, root,
                         root / "python/native" if name == "clippy-native.jsonl" else root)
    paths["python-coverage.xml"] = normalize_python(output / "python-coverage.xml", root)
    versions = {"rust": subprocess.check_output(["rustc", "+1.99.0", "-vV"], env=env, text=True),
                "llvm_cov": subprocess.check_output(["cargo", "+1.99.0", "llvm-cov", "--version"], env=env, text=True),
                "coverage": subprocess.check_output([sys.executable, "-m", "coverage", "--version"], env=env, text=True)}
    if "cargo-llvm-cov 0.9.1" not in versions["llvm_cov"] or "7.17.2" not in versions["coverage"]:
        raise ValueError("coverage tool version differs from reviewed pin")
    record = {"schema": 1, "revision": revision, "generation_exit_codes": statuses, "clippy_outcomes": clippy,
              "reports": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in REPORTS},
              "source_paths": paths, "tools": versions,
              "limitations": ["Python tests do not instrument Rust FFI instructions",
                              "Optional NumPy tests skipped unless already installed",
                              "Report validation does not prevent a writer fabricating data"]}
    (output / "report-inventory.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    generate(args.root.resolve(), args.output.resolve(), args.revision)

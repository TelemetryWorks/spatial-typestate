"""Bounded, resumable Criterion study. Python standard library only.

Run --prepare before the quiet window; --run never builds concurrently with
measurement. Independent process repetitions are retained, not pooled as samples.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "target" / "performance-study"
CARGO = ["cargo", "+1.99.0-x86_64-pc-windows-msvc"]
CONFIGS = {
    "lto-std": ([], {}),
    "lto-no-std": (["--no-default-features", "--features", "no_std"], {}),
    "nolto-std": ([], {"CARGO_PROFILE_BENCH_LTO": "false",
                        "CARGO_PROFILE_BENCH_CODEGEN_UNITS": "16"}),
}
# Downstream-like bounded subset; the full two-feature study is already broad.
SUBSET = r"operations/(point_valid|vector_valid|compose_valid|inverse_valid|constructor_valid)$|conversion/.*valid$|point_candidates/(valid|mixed_1in8|subnormal)/|quaternion/normal/public$|preparation/"


def capture(command, env=None):
    return subprocess.check_output(command, cwd=ROOT, env=env, text=True).strip()


def fingerprint():
    names = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / ".cargo/config.toml"]
    names += sorted((ROOT / "src").glob("*.rs"))
    names += sorted((ROOT / "benches").rglob("*.rs"))
    digest = hashlib.sha256()
    for path in names:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def prepare(configs):
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"fingerprint": fingerprint(), "configs": {},
                "compiler": capture(["rustc", CARGO[1], "-vV"]),
                "platform": platform.platform(),
                "base_commit": capture(["git", "rev-parse", "HEAD"])}
    for name in configs:
        flags, overrides = CONFIGS[name]
        env = os.environ.copy()
        env.update(overrides)
        env["CARGO_BUILD_JOBS"] = "2"
        if name.startswith("nolto"):
            env["CARGO_TARGET_DIR"] = str(OUT / "build-nolto")
        command = CARGO + ["bench", "--locked", "--jobs", "2", "--bench", "spatial",
                           "--no-run", "--message-format=json"] + flags
        print("BUILD " + name, flush=True)
        with (OUT / (name + "-build.log")).open("w", encoding="utf-8") as log:
            result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                    stdout=subprocess.PIPE, stderr=log, check=True)
        artifacts = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        executable = next(item["executable"] for item in artifacts
                          if item.get("reason") == "compiler-artifact"
                          and item["target"]["name"] == "spatial" and item.get("executable"))
        manifest["configs"][name] = {"executable": executable, "command": command,
                                     "overrides": overrides}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def collect(home, label, metadata):
    rows, samples = [], []
    for path in sorted(home.glob("**/new/estimates.json")):
        estimates = json.loads(path.read_text())
        info = json.loads((path.parent / "benchmark.json").read_text())
        raw = json.loads((path.parent / "sample.json").read_text())
        row = {"run": label, "benchmark": info["full_id"]}
        for kind in ["median", "mean", "std_dev", "slope"]:
            if kind not in estimates:
                continue
            estimate = estimates[kind]
            row[kind + "_ns"] = estimate["point_estimate"]
            row[kind + "_lower_ns"] = estimate["confidence_interval"]["lower_bound"]
            row[kind + "_upper_ns"] = estimate["confidence_interval"]["upper_bound"]
        rows.append(row)
        samples.append({"run": label, "benchmark": info["full_id"], "sample": raw})
    if not rows:
        raise RuntimeError("No Criterion estimates found; refusing an empty result")
    result = {"metadata": metadata, "estimates": rows, "samples": samples}
    (home.parent / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def run(study, configs, selected_filter):
    manifest = json.loads((OUT / "manifest.json").read_text())
    if manifest["fingerprint"] != fingerprint():
        raise RuntimeError("Source changed after preparation; rebuild before collecting timings")
    if any(config not in manifest["configs"] for config in configs):
        raise RuntimeError("Prepare all requested profiles before measuring")
    study_folder = OUT / study
    study_folder.mkdir(parents=True, exist_ok=True)
    plan = {"fingerprint": manifest["fingerprint"], "configs": configs,
            "filter": selected_filter}
    plan_file = study_folder / "study-plan.json"
    if plan_file.exists() and json.loads(plan_file.read_text()) != plan:
        raise RuntimeError("Study plan changed; choose a fresh study name")
    plan_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    (study_folder / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for repeat in range(1, 4):
        order = ["lto-std", "lto-no-std"] if repeat % 2 else ["lto-no-std", "lto-std"]
        order += ["nolto-std"]
        order = [config for config in order if config in configs]
        if len(configs) != len(CONFIGS):
            order = list(configs) if repeat % 2 else list(reversed(configs))
        for config in order:
            label = config + "-r" + str(repeat)
            folder = OUT / study / label
            if (folder / "result.json").exists():
                saved = json.loads((folder / "result.json").read_text())
                if saved["metadata"]["fingerprint"] != manifest["fingerprint"]:
                    raise RuntimeError("Completed result has another fingerprint; use a fresh study")
                print("RESUME skip " + label, flush=True)
                continue
            folder.mkdir(parents=True, exist_ok=True)
            # Each attempt gets a fresh directory, including after interruption.
            # Preserve partial evidence without mixing it into a resumed run.
            home = folder / ("criterion-" + str(time.time_ns()))
            env = os.environ.copy()
            env["CRITERION_HOME"] = str(home)
            env["SPATIAL_BENCH_SEED"] = "5573589319906701683"
            # Reverse candidate registration, not benchmark IDs or inputs.
            env.pop("SPATIAL_BENCH_REVERSE", None)
            if repeat % 2 == 0:
                env["SPATIAL_BENCH_REVERSE"] = "1"
            command = [manifest["configs"][config]["executable"], "--bench", "--noplot"]
            if selected_filter:
                command.append(selected_filter)
            elif config.startswith("nolto"):
                command.append(SUBSET)
            metadata = {"config": config, "repeat": repeat, "command": command,
                        "seed": env["SPATIAL_BENCH_SEED"], "reverse": repeat % 2 == 0,
                        "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "fingerprint": manifest["fingerprint"]}
            print("MEASURE " + label, flush=True)
            start = time.monotonic()
            with (folder / "console.log").open("w", encoding="utf-8") as log:
                subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                               stderr=subprocess.STDOUT, check=True)
            metadata["seconds"] = time.monotonic() - start
            collect(home, label, metadata)
            print("DONE " + label + " %.1fs" % metadata["seconds"], flush=True)
    export(study)


def export(study):
    folder = OUT / study
    rows = []
    for path in sorted(folder.glob("*/result.json")):
        rows.extend(json.loads(path.read_text())["estimates"])
    fields = sorted({key for row in rows for key in row})
    with (folder / "estimates.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--study", default="host-study")
    parser.add_argument("--configs", default=",".join(CONFIGS),
                        help="comma-separated named profiles (default: all)")
    parser.add_argument("--filter", default=None,
                        help="optional Criterion filter, replacing the no-LTO subset")
    args = parser.parse_args()
    configs = args.configs.split(",")
    if not configs or any(config not in CONFIGS for config in configs):
        parser.error("unknown/empty profile selection")
    if not args.prepare and not args.run:
        parser.error("select --prepare and/or --run")
    if args.prepare:
        prepare(configs)
    if args.run:
        run(args.study, configs, args.filter)

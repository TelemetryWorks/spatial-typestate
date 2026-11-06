"""Retain source-archive and SARIF counts; fail if an intended source is missing."""

import json
import os
from pathlib import Path
import zipfile


def inventory(language, database_dir, results_dir):
    archives = list(database_dir.rglob("src.zip"))
    if len(archives) != 1:
        raise ValueError(f"expected one source archive, found {len(archives)}")
    with zipfile.ZipFile(archives[0]) as archive:
        paths = sorted(name.replace("\\", "/") for name in archive.namelist()
                       if not name.endswith("/"))
    expected = {
        "rust": ["src/transform.rs", "src/quaternion.rs", "python/native/src/lib.rs",
                 "python/native/src/kernels.rs"],
        "python": ["python/build_backend.py", "python/verify_artifacts.py",
                   "python/src/spatial_typestate/__init__.py",
                   "python/examples/lab_workflow.py"],
        "actions": [".github/workflows/codeql.yml", ".github/workflows/python.yml",
                    ".github/workflows/ci.yml"],
    }[language]
    missing = [path for path in expected
               if not any(name.endswith("/" + path) or name == path for name in paths)]
    if missing:
        raise ValueError(f"intended source missing from archive: {missing}")
    sarif_paths = sorted(results_dir.glob("*.sarif"))
    if not sarif_paths:
        raise ValueError("no SARIF results")
    runs = []
    for path in sarif_paths:
        for run in json.loads(path.read_text(encoding="utf-8"))["runs"]:
            driver = run["tool"]["driver"]
            components = [driver, *run["tool"].get("extensions", [])]
            invocations = run.get("invocations", [])
            diagnostics = [notice for invocation in invocations
                           for key in ("toolExecutionNotifications", "toolConfigurationNotifications")
                           for notice in invocation.get(key, [])]
            runs.append({"sarif": path.name, "tool": driver["name"],
                         "version": driver.get("semanticVersion", driver.get("version")),
                         "rules": sum(len(component.get("rules", [])) for component in components),
                         "results": len(run.get("results", [])),
                         "diagnostics": diagnostics,
                         "diagnostic_errors": sum(notice.get("level") == "error" for notice in diagnostics),
                         "execution_successful": [invocation.get("executionSuccessful")
                                                  for invocation in invocations],
                         "metrics": run.get("properties", {}),
                         "artifacts": run.get("artifacts", [])})
    if not runs or any(run["rules"] == 0 for run in runs):
        raise ValueError("no query rules in SARIF")
    return {"language": language, "source_files": len(paths),
            "expected_sources": expected, "source_paths": paths, "runs": runs}


if __name__ == "__main__":
    result_dir = Path(os.environ["EVIDENCE_DIR"])
    report = inventory(os.environ["ANALYSIS_LANGUAGE"],
                       Path(os.environ["DATABASE_DIR"]), result_dir)
    (result_dir / "source-inventory.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key != "source_paths"}, indent=2))

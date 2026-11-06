"""Public-only Sonar evidence. No token support or alternate host is provided."""

import argparse
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


HOST = "https://sonarcloud.io"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Sonar evidence redirects are forbidden")


def public_json(endpoint, parameters):
    if not re.fullmatch(r"/api/[a-z_]+/[a-z_]+", endpoint):
        raise ValueError("unexpected API endpoint")
    url = HOST + endpoint + "?" + urllib.parse.urlencode(parameters)
    # Do not inherit proxy/auth handlers or credentials from the environment.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(url, timeout=30) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError("API response too large")
    return json.loads(data)


def pages(get, endpoint, parameters, field, identity):
    records = []
    expected = None
    seen = set()
    for page in range(1, 101):
        response = get(endpoint, parameters | {"p": page, "ps": 100})
        paging = response["paging"]
        total = paging["total"]
        if type(total) is not int or total < 0 or total > 10000:
            raise ValueError("unsupported/incomplete pagination total")
        if expected is None:
            expected = total
        if total != expected or paging["pageIndex"] != page:
            raise ValueError("pagination changed during collection")
        items = response[field]
        for record in items:
            key = record[identity]
            if key in seen:
                raise ValueError("duplicate paginated record")
            seen.add(key)
            records.append(record)
        if len(records) == total:
            return records
        if not items or len(records) > total:
            raise ValueError("incomplete pagination")
    raise ValueError("pagination limit reached")


def task_properties(path, project, organization=None):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("missing/invalid scanner task file; no analysis evidence")
    record = {}
    allowed = {"projectKey", "organization", "serverUrl", "serverVersion", "dashboardUrl", "ceTaskId", "ceTaskUrl"}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key not in allowed or key in record:
            raise ValueError("unexpected/duplicate scanner task field")
        record[key] = value
    if record["projectKey"] != project or record["serverUrl"] != HOST:
        raise ValueError("task project/host mismatch")
    if "organization" in record and record["organization"] != organization:
        raise ValueError("task organization mismatch")
    for key in ("dashboardUrl", "ceTaskUrl"):
        url = urllib.parse.urlsplit(record[key])
        if url.scheme != "https" or url.netloc != "sonarcloud.io":
            raise ValueError("foreign task URL")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", record["ceTaskId"]):
        raise ValueError("invalid task ID")
    task_url = urllib.parse.urlsplit(record["ceTaskUrl"])
    if task_url.path != "/api/ce/task" or urllib.parse.parse_qs(task_url.query) != {"id": [record["ceTaskId"]]}:
        raise ValueError("task URL/ID mismatch")
    return record


def collect(get, project, revision, task_id, branch, pr_number=None):
    result = {"project": project, "revision": revision, "public_only": True,
              "restoration_verified": False, "complete": False}
    task = get("/api/ce/task", {"id": task_id})["task"]
    result["task"] = task
    if task["status"] != "SUCCESS" or task.get("componentKey") != project:
        raise ValueError("analysis task failed or belongs to another project")
    context = {"pullRequest": pr_number} if pr_number else {"branch": branch}
    result["gate"] = get("/api/qualitygates/project_status", {"analysisId": task["analysisId"]})
    result["measures"] = get("/api/measures/component", {
        "component": project, **context,
        "metricKeys": "ncloc,files,ncloc_language_distribution,coverage,line_coverage,branch_coverage,lines_to_cover,uncovered_lines,security_hotspots"})
    result["files"] = pages(get, "/api/measures/component_tree", {
        "component": project, **context, "strategy": "leaves", "qualifiers": "FIL",
        "metricKeys": "ncloc,coverage,line_coverage,lines_to_cover,uncovered_lines"}, "components", "key")
    result["github_indexed_paths"] = [item["path"] for item in result["files"] if item.get("path", "").startswith(".github/")]
    result["github_analysis_claim"] = "unproven; server file listing must be reviewed, indexing alone is not rule coverage"
    issues = []
    for resolved in ("false", "true"):
        issues.extend(pages(get, "/api/issues/search", {
            "componentKeys": project, **context, "resolved": resolved}, "issues", "key"))
    if len({record["key"] for record in issues}) != len(issues):
        raise ValueError("issue state changed during inventory")
    result["issues"] = issues
    branches = get("/api/project_branches/list", {"project": project})["branches"]
    is_main = len([item for item in branches if item.get("isMain") and item["name"] == branch]) == 1
    if pr_number or not is_main:
        # Current public API schema has no PR/branch argument for hotspot search.
        # Never relabel a main-branch inventory as PR hotspot evidence.
        result["partial"] = True
        result["hotspot_scope"] = "unavailable for PR/nonmain; full inventory main-only"
        result["requires_independent_review"] = ["Rust execution/import/coverage and scanner warnings", "Partial evidence is not complete hotspot coverage"]
        return result
    analyses = pages(get, "/api/project_analyses/search", {"project": project, "branch": branch}, "analyses", "key")
    matching = [analysis for analysis in analyses if analysis["key"] == task["analysisId"]]
    if len(matching) != 1 or matching[0].get("revision") != revision:
        raise ValueError("server analysis revision mismatch")
    result["analysis"] = matching[0]
    hotspots = []
    for status in ("TO_REVIEW", "REVIEWED"):
        hotspots.extend(pages(get, "/api/hotspots/search", {
            "projectKey": project, "status": status}, "hotspots", "key"))
    if len({record["key"] for record in hotspots}) != len(hotspots):
        raise ValueError("hotspot state changed during inventory")
    result["hotspots"] = hotspots
    result["complete"] = True
    result["partial"] = False
    result["requires_independent_review"] = [
        "Rust analyzer execution boundary and scanner warnings",
        "Per-file Rust/Python coverage versus submitted inventory and scanner import logs",
        "Clippy import and issue/hotspot disposition (no automatic acceptance)"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"complete": False, "restoration_verified": False}
    queries = []
    def recorded_json(endpoint, parameters):
        response = public_json(endpoint, parameters)
        queries.append({"endpoint": endpoint, "parameters": parameters, "response": response})
        return response
    try:
        project = os.environ["PROJECT_KEY"]
        revision = os.environ["SOURCE_REVISION"]
        task = task_properties(args.task_dir / "report-task.txt", project, os.environ["ORGANIZATION"])
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        pr = str(event["number"]) if os.environ["GITHUB_EVENT_NAME"] == "pull_request" else None
        branch = os.environ["GITHUB_REF"].removeprefix("refs/heads/")
        result = collect(recorded_json, project, revision, task["ceTaskId"], branch, pr)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        result["blocker"] = str(error)
    finally:
        result["public_queries"] = queries
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if (not result["complete"] and not result.get("partial")) or result.get("gate", {}).get("projectStatus", {}).get("status") != "OK":
        raise SystemExit("Sonar evidence incomplete or gate failed; NOT restored")
    if result.get("partial"):
        print("PARTIAL PR/nonmain evidence only; quality gate result retained, no complete hotspot claim")

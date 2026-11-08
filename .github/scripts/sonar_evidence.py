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
        append_unique(records, seen, items, identity)
        if len(records) == total:
            return records
        if not items or len(records) > total:
            raise ValueError("incomplete pagination")
    raise ValueError("pagination limit reached")


def append_unique(records, seen, items, identity):
    for record in items:
        key = record[identity]
        if key in seen:
            raise ValueError("duplicate paginated record")
        seen.add(key)
        records.append(record)


def validate_task_urls(record):
    for key in ("dashboardUrl", "ceTaskUrl"):
        url = urllib.parse.urlsplit(record[key])
        if url.scheme != "https" or url.netloc != "sonarcloud.io":
            raise ValueError("foreign task URL")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", record["ceTaskId"]):
        raise ValueError("invalid task ID")
    task_url = urllib.parse.urlsplit(record["ceTaskUrl"])
    if task_url.path != "/api/ce/task" or urllib.parse.parse_qs(task_url.query) != {"id": [record["ceTaskId"]]}:
        raise ValueError("task URL/ID mismatch")


def validate_task_identity(record, project, organization, branch):
    if record["projectKey"] != project or record["serverUrl"] != HOST:
        raise ValueError("task project/host mismatch")
    if "organization" in record and record["organization"] != organization:
        raise ValueError("task organization mismatch")
    if "branch" in record and (branch is None or record["branch"] != branch):
        raise ValueError("task branch mismatch")


def task_properties(path, project, organization=None, branch=None):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ValueError("missing/invalid scanner task file; no analysis evidence")
    record = {}
    allowed = {"projectKey", "organization", "branch", "serverUrl", "serverVersion", "dashboardUrl", "ceTaskId", "ceTaskUrl"}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key not in allowed or key in record:
            raise ValueError("unexpected/duplicate scanner task field")
        record[key] = value
    validate_task_identity(record, project, organization, branch)
    validate_task_urls(record)
    return record


def analysis_identity(get, project, revision, branch, pr_number):
    if pr_number:
        records = get("/api/project_pull_requests/list", {"project": project})["pullRequests"]
        matches = [r for r in records if r["key"] == pr_number]
        if len(matches) != 1 or matches[0].get("commit", {}).get("sha") != revision:
            raise ValueError("server PR revision mismatch")
        record = matches[0]
        return {"pullRequest": pr_number, "revision": revision, "analysisDate": record["analysisDate"]}
    records = pages(get, "/api/project_analyses/search", {"project": project, "branch": branch}, "analyses", "key")
    if not records or records[0].get("revision") != revision:
        raise ValueError("server analysis revision mismatch")
    return records[0]


def collect(get, project, revision, task_id, branch, pr_number=None, organization=None):
    result = {"project": project, "revision": revision, "public_only": True,
              "restoration_verified": False, "complete": False}
    component = get("/api/components/show", {"component": project})["component"]
    if component.get("key") != project or component.get("organization") != organization or component.get("visibility") != "public":
        raise ValueError("server project/organization/public visibility mismatch")
    result["component"] = component
    result["scanner_task_id"] = task_id
    result["task_status_limit"] = "No public CE task status: endpoint requires Execute Analysis permission"
    identity = analysis_identity(get, project, revision, branch, pr_number)
    result["analysis_identity"] = identity
    context = {"pullRequest": pr_number} if pr_number else {"branch": branch}
    gate_parameters = {"projectKey": project, "pullRequest": pr_number} if pr_number else {"analysisId": identity["key"]}
    result["gate"] = get("/api/qualitygates/project_status", gate_parameters)
    result["measures"] = get("/api/measures/component", {
        "component": project, **context,
        "metricKeys": "ncloc,files,ncloc_language_distribution,coverage,line_coverage,branch_coverage,lines_to_cover,uncovered_lines,security_hotspots"})
    result["files"] = pages(get, "/api/measures/component_tree", {
        "component": project, **context, "strategy": "leaves",
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
    result["hotspot_scope"] = "unavailable for PR/nonmain; full inventory main-only"
    result["partial"] = True
    result["requires_independent_review"] = ["Rust execution/import/coverage and scanner warnings", "Partial evidence is not complete hotspot coverage"]
    if pr_number:
        # Current public API schema has no PR/branch argument for hotspot search.
        # Never relabel a main-branch inventory as PR hotspot evidence.
        verify_stable_analysis(get, project, revision, branch, pr_number, identity)
        return result
    branches = get("/api/project_branches/list", {"project": project})["branches"]
    if not any(item.get("isMain") and item["name"] == branch for item in branches):
        verify_stable_analysis(get, project, revision, branch, pr_number, identity)
        return result
    result["analysis"] = identity
    hotspots = []
    for status in ("TO_REVIEW", "REVIEWED"):
        hotspots.extend(pages(get, "/api/hotspots/search", {
            "projectKey": project, "status": status}, "hotspots", "key"))
    if len({record["key"] for record in hotspots}) != len(hotspots):
        raise ValueError("hotspot state changed during inventory")
    result["hotspots"] = hotspots
    result["hotspot_scope"] = "complete main-branch inventory"
    verify_stable_analysis(get, project, revision, branch, pr_number, identity)
    result["complete"] = True
    result["partial"] = False
    result["requires_independent_review"] = [
        "Rust analyzer execution boundary and scanner warnings",
        "Per-file Rust/Python coverage versus submitted inventory and scanner import logs",
        "Clippy import and issue/hotspot disposition (no automatic acceptance)"]
    return result


def verify_stable_analysis(get, project, revision, branch, pr_number, before):
    if analysis_identity(get, project, revision, branch, pr_number) != before:
        raise ValueError("server analysis changed during collection")


def evidence_output(temporary):
    root = temporary.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("runner temporary directory missing")
    output = root / "sonar-server-evidence.json"
    if output.is_symlink() or output.exists():
        raise ValueError("evidence output already exists or is a symlink")
    return output


def write_evidence(task_dir, environ, get=public_json):
    # The caller cannot select a destination. Only the runner-owned temp root
    # and this fixed basename are used, before any network request or write.
    output = evidence_output(Path(environ["RUNNER_TEMP"]))
    result = {"complete": False, "restoration_verified": False}
    queries = []
    def recorded_json(endpoint, parameters):
        response = get(endpoint, parameters)
        queries.append({"endpoint": endpoint, "parameters": parameters, "response": response})
        return response
    try:
        project = environ["PROJECT_KEY"]
        revision = environ["SOURCE_REVISION"]
        event = json.loads(Path(environ["GITHUB_EVENT_PATH"]).read_text())
        pr = str(event["number"]) if environ["GITHUB_EVENT_NAME"] == "pull_request" else None
        branch = environ["GITHUB_REF"].removeprefix("refs/heads/")
        expected_task_branch = None if pr else branch
        task = task_properties(task_dir / "report-task.txt", project, environ["ORGANIZATION"], expected_task_branch)
        result = collect(recorded_json, project, revision, task["ceTaskId"], branch, pr, environ["ORGANIZATION"])
    except (ValueError, KeyError, OSError) as error:
        result["blocker"] = str(error)
    finally:
        result["public_queries"] = queries
        with output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    return result


def evidence_passes(result):
    return (result["complete"] or result.get("partial", False)) and result.get("gate", {}).get("projectStatus", {}).get("status") == "OK"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    args = parser.parse_args()
    result = write_evidence(args.task_dir, os.environ)
    if not evidence_passes(result):
        raise SystemExit("Sonar evidence incomplete or gate failed; NOT restored")
    if result.get("partial"):
        print("PARTIAL PR/nonmain evidence only; quality gate result retained, no complete hotspot claim")

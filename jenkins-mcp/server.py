"""Jenkins MCP server for Claude Code (Terraform pipeline helper).

Env vars: JENKINS_URL, JENKINS_USER, JENKINS_API_TOKEN
Safety: apply/destroy builds are refused unless confirm_destructive=True.
"""
import os
import time

import requests
from mcp.server.fastmcp import FastMCP

JENKINS_URL = os.environ.get("JENKINS_URL", "http://localhost:8080").rstrip("/")
AUTH = (os.environ.get("JENKINS_USER", ""), os.environ.get("JENKINS_API_TOKEN", ""))
DEFAULT_JOB = os.environ.get("JENKINS_DEFAULT_JOB", "terraform-pipeline")
VALID_MODULES = {"ec2", "iam", "s3"}
VALID_ACTIONS = {"plan", "apply", "destroy"}
TIMEOUT = 30

mcp = FastMCP("jenkins")
session = requests.Session()
session.auth = AUTH


def _job_path(job: str) -> str:
    # supports folders: "folder/job" -> /job/folder/job/job
    return "".join(f"/job/{p}" for p in job.strip("/").split("/"))


def _crumb_headers() -> dict:
    try:
        r = session.get(f"{JENKINS_URL}/crumbIssuer/api/json", timeout=10)
        if r.ok:
            d = r.json()
            return {d["crumbRequestField"]: d["crumb"]}
    except requests.RequestException:
        pass
    return {}


@mcp.tool()
def list_jobs() -> list[dict]:
    """List top-level Jenkins jobs with their last-known color/status."""
    r = session.get(f"{JENKINS_URL}/api/json?tree=jobs[name,color,url]", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["jobs"]


@mcp.tool()
def trigger_terraform(module: str, action: str = "plan", branch: str = "main",
                      job: str = DEFAULT_JOB, confirm_destructive: bool = False) -> dict:
    """Trigger the parameterized Terraform pipeline.

    module: ec2 | iam | s3. action: plan | apply | destroy.
    apply/destroy are refused unless confirm_destructive=True, which must only be
    set after the user has explicitly approved in chat.
    Returns the queue URL; use get_queue_item then get_build_status to follow it.
    """
    if module not in VALID_MODULES:
        return {"error": f"module must be one of {sorted(VALID_MODULES)}"}
    if action not in VALID_ACTIONS:
        return {"error": f"action must be one of {sorted(VALID_ACTIONS)}"}
    if action in ("apply", "destroy") and not confirm_destructive:
        return {"error": f"'{action}' needs explicit user approval. Ask the user, then retry with confirm_destructive=true."}
    r = session.post(
        f"{JENKINS_URL}{_job_path(job)}/buildWithParameters",
        params={"MODULE": module, "ACTION": action, "BRANCH": branch},
        headers=_crumb_headers(),
        timeout=TIMEOUT,
    )
    if r.status_code not in (200, 201):
        return {"error": f"Jenkins returned {r.status_code}", "body": r.text[:500]}
    return {"queued": True, "queue_url": r.headers.get("Location"), "module": module, "action": action}


@mcp.tool()
def get_queue_item(queue_url: str) -> dict:
    """Resolve a queue URL (from trigger_terraform) to a build number once it starts."""
    r = session.get(f"{queue_url.rstrip('/')}/api/json", timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json()
    ex = d.get("executable")
    return {"waiting": ex is None, "why": d.get("why"),
            "build_number": ex["number"] if ex else None, "build_url": ex["url"] if ex else None}


@mcp.tool()
def get_build_status(build_number: int | None = None, job: str = DEFAULT_JOB) -> dict:
    """Status of a build (latest if build_number omitted): building flag, result, params."""
    ref = build_number if build_number else "lastBuild"
    r = session.get(f"{JENKINS_URL}{_job_path(job)}/{ref}/api/json"
                    "?tree=number,building,result,duration,url,actions[parameters[name,value]]",
                    timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json()
    params = {p["name"]: p["value"] for a in d.get("actions", []) for p in a.get("parameters", [])}
    return {"number": d["number"], "building": d["building"], "result": d["result"],
            "duration_ms": d["duration"], "url": d["url"], "parameters": params}


@mcp.tool()
def wait_for_build(build_number: int, job: str = DEFAULT_JOB, timeout_s: int = 300) -> dict:
    """Poll until the build finishes or timeout. Builds paused at the Approval stage
    stay 'building'; tell the user to click Proceed in Jenkins."""
    end = time.time() + timeout_s
    while time.time() < end:
        s = get_build_status(build_number, job)
        if not s["building"]:
            return s
        time.sleep(5)
    s = get_build_status(build_number, job)
    s["note"] = "timeout reached; build still running (possibly waiting at the approval stage)"
    return s


@mcp.tool()
def get_console_log(build_number: int | None = None, job: str = DEFAULT_JOB, tail_lines: int = 150) -> str:
    """Return the last N lines of the console log (latest build if number omitted)."""
    ref = build_number if build_number else "lastBuild"
    r = session.get(f"{JENKINS_URL}{_job_path(job)}/{ref}/consoleText", timeout=TIMEOUT)
    r.raise_for_status()
    return "\n".join(r.text.splitlines()[-tail_lines:])


@mcp.tool()
def get_plan_output(build_number: int | None = None, job: str = DEFAULT_JOB) -> str:
    """Fetch the archived plan.txt (terraform show of the saved plan) for a build."""
    ref = build_number if build_number else "lastBuild"
    for m in sorted(VALID_MODULES):
        r = session.get(f"{JENKINS_URL}{_job_path(job)}/{ref}/artifact/{m}/plan.txt", timeout=TIMEOUT)
        if r.ok:
            return r.text[-12000:]
    return "plan.txt not found. Check the build reached the Plan stage."


@mcp.tool()
def abort_build(build_number: int, job: str = DEFAULT_JOB) -> dict:
    """Abort a running build."""
    r = session.post(f"{JENKINS_URL}{_job_path(job)}/{build_number}/stop",
                     headers=_crumb_headers(), timeout=TIMEOUT)
    return {"status_code": r.status_code, "aborted": r.status_code in (200, 302)}


if __name__ == "__main__":
    mcp.run()

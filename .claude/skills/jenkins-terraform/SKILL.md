---
name: jenkins-terraform
description: Run Terraform plan/apply/destroy for the ec2, iam or s3 modules through the local Jenkins pipeline (http://localhost:8080), check build status, explain failures, and troubleshoot the Claude-Jenkins integration. Use when the user asks to plan, deploy, apply, destroy, check, debug or abort a Jenkins/Terraform build.
---

# Jenkins Terraform workflow

Uses the `jenkins` MCP server (tools `mcp__jenkins__*`, defined in `jenkins-mcp/server.py`).
Job: `terraform-pipeline`, parameters `MODULE` (ec2|iam|s3), `ACTION` (plan|apply|destroy), `BRANCH` (default main).
State: S3 bucket `malli-terraform-learning-tfstate`, key `<module>/terraform.tfstate`, region us-east-1.

| Tool | Use |
|---|---|
| `list_jobs` | Sanity check that Jenkins is reachable |
| `trigger_terraform(module, action, branch, confirm_destructive)` | Queue a build; returns `queue_url` |
| `get_queue_item(queue_url)` | Poll until `build_number` appears |
| `wait_for_build(build_number, timeout_s)` | Block until the build finishes (or pauses at Approval) |
| `get_build_status(build_number?)` | Result, building flag, parameters (latest if omitted) |
| `get_plan_output(build_number?)` | Archived `<module>/plan.txt` |
| `get_console_log(build_number?, tail_lines)` | Last N console lines |
| `abort_build(build_number)` | Stop a running build (ask first) |

## 1. Identify the request
Extract module, action and branch. "deploy"/"create" = apply, "tear down"/"remove" = destroy,
"check"/"preview" = plan. Ask only if the module is unclear. "all modules" = run each module
in turn (order for apply: iam → s3 → ec2; for destroy: reverse), one build at a time
(the job disallows concurrent builds).

## 2. Pre-flight (only if code in the module changed)
```
terraform -chdir=<module> fmt
terraform -chdir=<module> validate   # needs a prior init; skip if it fails on backend auth
git status --short
```
Jenkins builds what is on GitHub, not local files. If there are uncommitted or unpushed changes,
tell the user and ask before `git commit` / `git push`.

## 3. Plan first, always
`trigger_terraform(module, "plan", branch)` → `get_queue_item` (repeat every few seconds until
`build_number`) → `wait_for_build(build_number)` → `get_plan_output(build_number)`.

## 4. Report
Reply with:
- Build `#N` result and link.
- Table: resource address | action (create / update / replace / destroy).
- Totals line from the plan ("Plan: X to add, Y to change, Z to destroy").
- Flags: any replace (`-/+`), destroy, IAM policy attached (especially `AdministratorAccess`),
  public S3 access, security-group 0.0.0.0/0.

## 5. Apply / destroy
Only after the user explicitly approves *this module and action* in chat, after seeing the plan:
`trigger_terraform(module, action, branch, confirm_destructive=true)`.
The pipeline re-plans and pauses at **Approval**: tell the user to review `plan.txt` in the build and
click **Proceed** at http://localhost:8080/job/terraform-pipeline/<N>/. Then `wait_for_build`
(timeout 600) and report outputs from `get_console_log` (the `Apply complete!` and `Outputs:` lines).
If the timeout hits while paused, say so; do not abort.

## 6. Failures
`get_console_log(build_number, 200)`, find the first `Error:` line and explain the cause and the fix.

| Symptom | Cause / fix |
|---|---|
| `terraform fmt -check` fails | Run `terraform fmt -recursive`, commit, push, re-plan |
| `S3 bucket does not exist` / `NoSuchBucket` at init | Create the state bucket (JENKINS-CLAUDE-SETUP.md §1) |
| `No valid credential sources` / `InvalidClientTokenId` | `aws-creds` credential missing or wrong in Jenkins |
| `EntityAlreadyExists` (IAM) / `BucketAlreadyOwnedByYou` | Resource exists outside state: `terraform import`, never recreate |
| State lock error | Another build is running; check `get_build_status`. Never force-unlock without asking |
| `DeleteConflict` on IAM destroy | Policies still attached; plan should detach first — check ordering |
| `'terraform' is not recognized` / `not found` | Terraform not on the Jenkins agent PATH |
| `ERROR: script returned exit code` with no TF error | Read 50 lines above it in the log |

## 7. Integration troubleshooting
| Symptom | Fix |
|---|---|
| `mcp__jenkins__*` tools missing | `/mcp` in Claude Code, approve project server `jenkins`; `pip install -r jenkins-mcp/requirements.txt`; `python` on PATH |
| 401 Unauthorized | `JENKINS_USER` / `JENKINS_API_TOKEN` not set in this terminal (setx needs a new terminal) |
| 403 No valid crumb | Token user lacks Job/Build permission, or CSRF crumb blocked |
| 404 on buildWithParameters | Job name differs (`JENKINS_DEFAULT_JOB` in `.mcp.json`) or job never run once |
| 400 "is not parameterized" | Run the job once manually so Jenkins registers parameters |
| Connection refused | Jenkins not running on localhost:8080 |

## Hard rules
- Never run `terraform apply`, `destroy`, `state rm`, `force-unlock` or `import` locally without explicit approval; applies go through Jenkins only.
- Never set `confirm_destructive=true` without explicit user approval in this conversation.
- Never read or print `*.tfstate`, `*.tfvars` or credentials.

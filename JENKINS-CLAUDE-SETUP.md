# Claude Code ↔ Jenkins ↔ Terraform setup (Windows)

Flow: you chat with Claude Code → `jenkins` MCP server (`jenkins-mcp/server.py`) → Jenkins REST API
(http://localhost:8080) → `Jenkinsfile` → Terraform → AWS (state in S3).

## 1. One-time AWS: create the state bucket
State lives in S3 (`<module>/backend.tf`) because Jenkins wipes its workspace after every build.
```powershell
aws s3api create-bucket --bucket malli-terraform-learning-tfstate --region us-east-1
aws s3api put-bucket-versioning --bucket malli-terraform-learning-tfstate --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket malli-terraform-learning-tfstate --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```
If that name is taken (bucket names are global), pick another and update all three `backend.tf` files.
Requires Terraform >= 1.10 (native S3 locking, no DynamoDB table).

Then, in each module (`ec2`, `iam`, `s3`), move the old local state to S3 once:
```powershell
cd ec2; terraform init -migrate-state; cd ..
```
Old local `terraform.tfstate*` files can be deleted after migration.

## 2. Format the code (otherwise the pipeline's fmt check fails)
```powershell
terraform fmt -recursive
```

## 3. Jenkins (http://localhost:8080)
1. Plugins: Git, Pipeline, Credentials Binding, Timestamper, Workspace Cleanup.
2. Terraform (>= 1.10) and Git installed on the Jenkins machine and on its PATH.
   The Jenkinsfile picks `bat` on Windows and `sh` on Linux automatically.
3. Manage Jenkins → Credentials → add "AWS Credentials" (CloudBees AWS Credentials plugin),
   ID `aws-terraform-creds` (access key ID + secret access key). Use a least-privilege IAM user.
   Add `github-token` only if the repo is private.
4. New Item → Pipeline `terraform-pipeline` → "Pipeline script from SCM" → Git
   `https://github.com/Malli-WAS/Terraform-learning.git`, branch `main`, script path `Jenkinsfile`.
5. Run it once with "Build Now" so Jenkins registers the parameters (MODULE, ACTION, BRANCH).
6. Your user (top right) → Security → API Token → Add new token. Copy it.

## 4. Commit and push
```powershell
git add Jenkinsfile CLAUDE.md .mcp.json .claude jenkins-mcp ec2 iam s3 .gitignore JENKINS-CLAUDE-SETUP.md README.md
git commit -m "Add Jenkins pipeline, S3 backend and Claude Code integration"
git push
```

## 5. Your laptop
```powershell
pip install -r jenkins-mcp\requirements.txt
setx JENKINS_USER "<your-jenkins-username>"
setx JENKINS_API_TOKEN "<token-from-step-3.6>"
```
Open a **new** terminal (setx only affects new ones), then:
```powershell
cd "Terraform-learning"
claude
```
Inside Claude Code run `/mcp`, approve the project server `jenkins`, and confirm it is connected.
(`.mcp.json` uses `python`; if your Python is launched as `py`, change it there.)

## 6. Try it
- "List my Jenkins jobs"
- "Plan the s3 module on Jenkins and summarize the changes"
- "Why did the last build fail?"
- "Apply the s3 module" — Claude asks you first, then the build pauses at Approval until you click Proceed in Jenkins.

## 7. Skill and agent
- **Skill** `.claude/skills/jenkins-terraform/SKILL.md`: the step-by-step workflow (plan → report → approve →
  apply), failure table and integration troubleshooting. Invoke directly with `/jenkins-terraform plan s3`.
- **Agent** `.claude/agents/jenkins-terraform-agent.md`: a subagent restricted to the Jenkins MCP tools plus
  read/fmt/git-status. It preloads the skill, runs builds in its own context (keeps long logs out of your
  main chat) and returns a short report. Claude delegates to it automatically, or ask:
  "Use the jenkins-terraform-agent to plan the iam module".
  Check it is loaded with `/agents`.
- Approval flow: agent plans and returns `NEEDS APPROVAL` → Claude asks you → you say yes → agent triggers
  apply with `confirm_destructive=true` → you click **Proceed** in Jenkins.

## Safety built in
- `.claude/settings.json`: read-only Jenkins calls allowed; triggering builds, commits and pushes ask first;
  local `terraform apply/destroy` and reading `*.tfstate` / `*.tfvars` are denied.
- `server.py` refuses apply/destroy unless `confirm_destructive=true` (set only after you approve in chat).
- The Jenkinsfile applies exactly the reviewed `tfplan`, behind a manual Approval stage.

# Terraform-learning

Three independent root modules: `ec2/`, `iam/`, `s3/`. Each has providers.tf, versions.tf, backend.tf,
variables.tf, main.tf, outputs.tf. Run Terraform per module directory, never from repo root.
State is remote in S3 (`malli-terraform-learning-tfstate`, key `<module>/terraform.tfstate`, us-east-1).

## Rules
- Never run `terraform apply` or `destroy` locally. All applies go through Jenkins (`terraform-pipeline` job).
- Always run `terraform fmt` and `terraform validate` in the module before committing.
- Never read or print `*.tfstate` / `*.tfvars` or any AWS credentials.
- For apply/destroy: show the plan first, then ask the user for explicit approval in chat.

## Jenkins tasks
- Delegate Jenkins/Terraform build work to the `jenkins-terraform-agent` subagent
  (it preloads the `jenkins-terraform` skill and uses the `jenkins` MCP tools).
- Before calling the agent (unless the user already named both), show the selection menu with
  AskUserQuestion: page 1 "Select the module" (EC2 / IAM / S3), page 2 "Select the option"
  (Apply / Destroy). Pass the result as `Module: <m>, Action: <a>`. If the agent returns
  `NEEDS INPUT: show menu`, show the same menu.
- The agent cannot ask the user questions. When it returns `NEEDS APPROVAL: <action> <module>`,
  show the user the plan summary and ask. Only if they approve, call the agent again with
  "User approved: <action> <module>, plan build #<N>".
- Push any local changes (with the user's OK) before triggering builds — Jenkins builds from GitHub.

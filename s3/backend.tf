# State is kept in this Git repo (<module>/terraform.tfstate). Jenkins commits and pushes it
# after every apply/destroy, so always `git pull` before running Terraform locally.
# WARNING: the repo is public and state is plain text — never create secrets (access keys,
# login profiles, passwords) in these modules while state lives here.
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}

# Remote state so Jenkins builds share state (the workspace is wiped after every build).
# The bucket must exist before "terraform init" — see JENKINS-CLAUDE-SETUP.md.
terraform {
  backend "s3" {
    bucket       = "malli-terraform-learning-tfstate"
    key          = "ec2/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true # native S3 locking (Terraform >= 1.10), no DynamoDB table needed
  }
}

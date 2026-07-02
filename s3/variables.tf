########################
# S3 Variables
########################
variable "region" {
  default = "us-east-1"
}

variable "bucket_name" {
  default = "malli-terraform-s3"
}

variable "environment" {
  default = "Dev"
}

variable "versioning" {
  default = "Enabled"
}
########################
# EC2 Variables
########################

variable "instance_name" {
  default = "Terraform-EC2"
}

variable "instance_type" {
  default = "t2.micro"
}
########################
# IAM Variables
########################

variable "user_name" {
  default = "terraform-demo-user"
}

variable "user_name1" {
  default = "Hari"
}

variable "user_name2" {
  default = "Mallikaraja"
}

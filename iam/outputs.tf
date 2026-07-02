####################
# IAM Outputs
####################

output "demo_user" {
  value = aws_iam_user.demo_user.name
}

output "hari_user" {
  value = aws_iam_user.hari.name
}

output "mallikaraja_user" {
  value = aws_iam_user.mallikaraja.name
}

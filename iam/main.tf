#################################################################
#                           IAM 
##################################################################  
resource "aws_iam_user" "demo_user" {
  name = var.user_name
}

resource "aws_iam_user" "hari" {
  name = var.user_name1
}

resource "aws_iam_user" "mallikaraja" {
  name = var.user_name2
}

resource "aws_iam_user_policy_attachment" "demo_policy" {
  user       = aws_iam_user.demo_user.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_user_policy_attachment" "hari_policy" {
  user       = aws_iam_user.hari.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_user_policy_attachment" "mallikaraja_policy" {
  user       = aws_iam_user.mallikaraja.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

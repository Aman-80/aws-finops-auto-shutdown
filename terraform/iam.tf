# Trust policy: only Lambda service can assume this role
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
} 
resource "aws_iam_role" "scheduler_lambda" {
  name               = "finops-scheduler-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

# Permissions: manage EC2 + write CloudWatch logs
data "aws_iam_policy_document" "scheduler_perms" {
  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
      "ec2:StartInstances",
      "ec2:StopInstances"
    ]
    resources = ["*"]
  }
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "scheduler_perms" {
  name   = "finops-scheduler-permissions"
  role   = aws_iam_role.scheduler_lambda.id
  policy = data.aws_iam_policy_document.scheduler_perms.json
}

resource "aws_ssm_parameter" "slack_webhook" {
  name        = "/finops/slack/webhook-url"
  description = "Slack incoming webhook for FinOps notifications"
  type        = "SecureString"
  value       = var.slack_webhook_url
}

resource "aws_iam_role_policy" "scheduler_ssm" {
  name = "finops-scheduler-ssm-access"
  role = aws_iam_role.scheduler_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter"]
      Resource = aws_ssm_parameter.slack_webhook.arn
    }]
  })
}

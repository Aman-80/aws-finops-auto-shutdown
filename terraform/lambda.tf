data "archive_file" "scheduler_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambdas/scheduler"
  output_path = "${path.module}/build/scheduler.zip"
  excludes    = ["requirements.txt", "__pycache__", "*.pyc"]
}

resource "aws_lambda_function" "scheduler" {
  function_name    = "finops-scheduler"
  role             = aws_iam_role.scheduler_lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 128

  filename         = data.archive_file.scheduler_zip.output_path
  source_code_hash = data.archive_file.scheduler_zip.output_base64sha256

  environment {
    variables = {
      DRY_RUN             = "false"
      OVERRIDE_TABLE      = aws_dynamodb_table.overrides.name
      SLACK_WEBHOOK_PARAM = aws_ssm_parameter.slack_webhook.name
    }
  }
}

resource "aws_cloudwatch_log_group" "scheduler" {
  name              = "/aws/lambda/${aws_lambda_function.scheduler.function_name}"
  retention_in_days = 7
}

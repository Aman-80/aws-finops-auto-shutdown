# Stop rule: weekday 6 PM IST (= 12:30 PM UTC)
resource "aws_cloudwatch_event_rule" "shutdown_stop" {
  name                = "finops-scheduler-stop"
  description         = "Stop dev instances every weekday at 6 PM IST"
  schedule_expression = "cron(30 12 ? * MON-FRI *)"
}

resource "aws_cloudwatch_event_target" "shutdown_stop" {
  rule      = aws_cloudwatch_event_rule.shutdown_stop.name
  target_id = "scheduler-lambda-stop"
  arn       = aws_lambda_function.scheduler.arn
  input     = jsonencode({ action = "stop" })
}

# Start rule: weekday 9 AM IST (= 3:30 AM UTC)
resource "aws_cloudwatch_event_rule" "shutdown_start" {
  name                = "finops-scheduler-start"
  description         = "Start dev instances every weekday at 9 AM IST"
  schedule_expression = "cron(30 3 ? * MON-FRI *)"
}

resource "aws_cloudwatch_event_target" "shutdown_start" {
  rule      = aws_cloudwatch_event_rule.shutdown_start.name
  target_id = "scheduler-lambda-start"
  arn       = aws_lambda_function.scheduler.arn
  input     = jsonencode({ action = "start" })
}

# Allow EventBridge to invoke Lambda
resource "aws_lambda_permission" "stop_rule" {
  statement_id  = "AllowExecutionFromEventBridgeStop"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.shutdown_stop.arn
}

resource "aws_lambda_permission" "start_rule" {
  statement_id  = "AllowExecutionFromEventBridgeStart"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.shutdown_start.arn
}

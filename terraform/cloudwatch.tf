# Allow Lambda to publish custom metrics
resource "aws_iam_role_policy" "scheduler_metrics" {
  name = "finops-scheduler-metrics-access"
  role = aws_iam_role.scheduler_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["cloudwatch:PutMetricData"]
      Resource = "*"
    }]
  })
}

# Dashboard with savings tracker, affected/skipped trends
resource "aws_cloudwatch_dashboard" "finops" {
  dashboard_name = "FinOps-Scheduler-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["FinOps/Scheduler", "SavingsINR"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "ap-south-1"
          title   = "💰 Cost Savings Over Time (₹)"
          stat    = "Sum"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["FinOps/Scheduler", "SavingsINR", { stat = "Sum", label = "Total Savings" }]
          ]
          view   = "singleValue"
          region = "ap-south-1"
          title  = "💰 Total Savings Tracked"
          period = 86400
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["FinOps/Scheduler", "InstancesAffected", "Action", "stop", { label = "Stopped" }],
            [".", ".", ".", "start", { label = "Started" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "ap-south-1"
          title   = "🔄 Instances Affected (by Action)"
          stat    = "Sum"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["FinOps/Scheduler", "InstancesSkipped", "Action", "stop", { label = "Skipped (override)" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "ap-south-1"
          title   = "⏭️ Instances Skipped Due to Overrides"
          stat    = "Sum"
          period  = 300
        }
      }
    ]
  })
}

output "dashboard_url" {
  value       = "https://ap-south-1.console.aws.amazon.com/cloudwatch/home?region=ap-south-1#dashboards:name=${aws_cloudwatch_dashboard.finops.dashboard_name}"
  description = "CloudWatch dashboard URL"
}

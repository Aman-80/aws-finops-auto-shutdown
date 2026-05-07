resource "aws_dynamodb_table" "overrides" {
  name         = "finops-shutdown-overrides"
  billing_mode = "PAY_PER_REQUEST"  # serverless, free-tier friendly
  hash_key     = "instance_id"

  attribute {
    name = "instance_id"
    type = "S"
  }

  # Auto-cleanup expired overrides
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

# Add DynamoDB read permission to scheduler Lambda's role
resource "aws_iam_role_policy" "scheduler_dynamodb" {
  name = "finops-scheduler-dynamodb-access"
  role = aws_iam_role.scheduler_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem"]
      Resource = aws_dynamodb_table.overrides.arn
    }]
  })
}

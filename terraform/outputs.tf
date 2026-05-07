output "instance_ids" {
  description = "IDs of playground EC2 instances"
  value       = aws_instance.dev_playground[*].id
}

output "instance_names" {
  description = "Names of playground EC2 instances"
  value       = aws_instance.dev_playground[*].tags.Name
}

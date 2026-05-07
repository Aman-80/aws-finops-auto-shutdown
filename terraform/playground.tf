# Latest Amazon Linux 2023 AMI - dynamic per region
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# 3 dummy dev instances - auto-shutdown candidates
resource "aws_instance" "dev_playground" {
  count         = 1
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  tags = {
    Name         = "dev-playground-${count.index + 1}"
    Environment  = "dev"
    AutoShutdown = "true"
    Schedule     = "weekday-9-18"
  }
}

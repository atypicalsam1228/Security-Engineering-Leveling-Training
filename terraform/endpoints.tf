# Private paths for Session Manager and S3 (saves NAT data charges).

locals {
  # Empty while paused: interface endpoints bill hourly. The security group
  # above them is free and stays.
  ssm_endpoint_services = var.enable_ssm_endpoints && !var.paused ? toset(["ssm", "ssmmessages", "ec2messages"]) : toset([])
}

resource "aws_security_group" "endpoints" {
  name        = "${var.lab_id}-endpoints"
  description = "HTTPS from inside the VPC to interface endpoints"
  vpc_id      = aws_vpc.lab.id

  ingress {
    description = "HTTPS from the VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.lab.cidr_block]
  }

  tags = { Name = "${var.lab_id}-endpoints" }
}

resource "aws_vpc_endpoint" "ssm" {
  for_each = local.ssm_endpoint_services

  vpc_id              = aws_vpc.lab.id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private.id]
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${var.lab_id}-${each.value}" }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.lab.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = { Name = "${var.lab_id}-s3" }
}

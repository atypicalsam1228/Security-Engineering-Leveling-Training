data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# Pick an AZ that offers BOTH the cluster instance type and the bastion
# instance type, instead of blindly taking the first AZ.
data "aws_ec2_instance_type_offerings" "cluster" {
  location_type = "availability-zone"

  filter {
    name   = "instance-type"
    values = [var.instance_type]
  }
}

data "aws_ec2_instance_type_offerings" "bastion" {
  location_type = "availability-zone"

  filter {
    name   = "instance-type"
    values = [var.bastion_instance_type]
  }
}

locals {
  az_candidates = [
    for name in sort(data.aws_availability_zones.available.names) : name
    if contains(data.aws_ec2_instance_type_offerings.cluster.locations, name)
    && contains(data.aws_ec2_instance_type_offerings.bastion.locations, name)
  ]
  az = try(local.az_candidates[0], null)
}

resource "aws_vpc" "lab" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.lab_id}-vpc" }
}

resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id

  tags = { Name = "${var.lab_id}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.lab.id
  cidr_block        = "10.0.0.0/24"
  availability_zone = local.az

  lifecycle {
    precondition {
      condition     = local.az != null
      error_message = "No availability zone in this region offers both instance_type and bastion_instance_type. Choose another region or instance type."
    }
  }

  tags = { Name = "${var.lab_id}-public" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.lab.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = local.az

  tags = { Name = "${var.lab_id}-private" }
}

# NAT gateway and its Elastic IP are the main idle cost; paused = true removes them.
resource "aws_eip" "nat" {
  count  = var.paused ? 0 : 1
  domain = "vpc"

  tags = { Name = "${var.lab_id}-nat" }
}

resource "aws_nat_gateway" "lab" {
  count         = var.paused ? 0 : 1
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public.id

  depends_on = [aws_internet_gateway.lab]

  tags = { Name = "${var.lab_id}-nat" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lab.id
  }

  tags = { Name = "${var.lab_id}-public" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.lab.id

  # The default route to the NAT is a separate resource (aws_route.private_nat)
  # so it can be removed while paused.
  tags = { Name = "${var.lab_id}-private" }
}

resource "aws_route" "private_nat" {
  count                  = var.paused ? 0 : 1
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.lab[0].id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "nodes_extra" {
  name        = "${var.lab_id}-nodes-extra"
  description = "Extra rules for the cluster node"
  vpc_id      = aws_vpc.lab.id

  ingress {
    description = "HTTPS from inside the VPC only"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.lab.cidr_block]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.lab_id}-nodes-extra" }
}

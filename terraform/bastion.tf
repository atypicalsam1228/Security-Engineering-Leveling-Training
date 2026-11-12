# FIPS-mode RHEL 9 bastion that runs openshift-install-fips.
# No public address, no key pair, no inbound rules. Access is Session Manager only.

data "aws_ami" "rhel9" {
  count       = var.bastion_ami_id == "" ? 1 : 0
  most_recent = true
  owners      = ["309956199498"] # Red Hat

  filter {
    name   = "name"
    values = ["RHEL-9*_HVM-*-x86_64-*-Hourly2-GP3"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  bastion_ami = var.bastion_ami_id != "" ? var.bastion_ami_id : data.aws_ami.rhel9[0].id
}

resource "aws_security_group" "bastion" {
  name        = "${var.lab_id}-bastion"
  description = "Bastion: no inbound, all outbound"
  vpc_id      = aws_vpc.lab.id

  # No ingress block on purpose.
  egress {
    description = "All outbound (installer, mirror.openshift.com, quay.io, AWS APIs)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.lab_id}-bastion" }
}

data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "bastion" {
  name               = "${var.lab_id}-bastion"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "bastion_ssm" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "bastion_installer" {
  for_each   = aws_iam_policy.installer
  role       = aws_iam_role.bastion.name
  policy_arn = each.value.arn
}

data "aws_iam_policy_document" "bastion_artifacts" {
  statement {
    sid       = "ArtifactsObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.artifacts.arn}/*"]
  }

  statement {
    sid       = "ArtifactsList"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.artifacts.arn]
  }

  # The installer policies grant S3 and IAM actions on "*" (Red Hat's list; the
  # installer's permission check evaluates them against "*", so they are not
  # narrowed here). These explicit Denies keep the bastion away from the
  # evidence buckets and from rewriting its own role.
  statement {
    sid     = "DenyLogBucket"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.log.arn, "${aws_s3_bucket.log.arn}/*",
    ]
  }

  statement {
    sid    = "DenyChangingOwnRole"
    effect = "Deny"
    actions = [
      "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:AttachRolePolicy", "iam:DetachRolePolicy",
      "iam:UpdateAssumeRolePolicy", "iam:DeleteRole", "iam:TagRole", "iam:UntagRole",
      "iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary",
      "iam:AddRoleToInstanceProfile", "iam:RemoveRoleFromInstanceProfile",
    ]
    resources = [
      aws_iam_role.bastion.arn,
      "arn:aws:iam::${local.account_id}:instance-profile/${var.lab_id}-bastion",
    ]
  }
}

resource "aws_iam_role_policy" "bastion_artifacts" {
  name   = "artifacts"
  role   = aws_iam_role.bastion.id
  policy = data.aws_iam_policy_document.bastion_artifacts.json
}

resource "aws_iam_instance_profile" "bastion" {
  name = "${var.lab_id}-bastion"
  role = aws_iam_role.bastion.name
}

# count = 0 while paused. The role, instance profile and security group stay.
resource "aws_instance" "bastion" {
  count                       = var.paused ? 0 : 1
  ami                         = local.bastion_ami
  instance_type               = var.bastion_instance_type
  subnet_id                   = aws_subnet.private.id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  iam_instance_profile        = aws_iam_instance_profile.bastion.name
  associate_public_ip_address = false
  user_data_replace_on_change = false

  user_data = templatefile("${path.module}/templates/bastion-userdata.sh.tftpl", {
    region           = var.region
    artifacts_bucket = aws_s3_bucket.artifacts.id
    ocp_channel      = var.ocp_channel
    install_export   = var.guard_bucket != ""
    lab_id           = var.lab_id
    guard_bucket     = var.guard_bucket
  })

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size = 60
    volume_type = "gp3"
    encrypted   = true
    kms_key_id  = aws_kms_key.lab.arn
  }

  lifecycle {
    ignore_changes = [ami]
  }

  # The endpoints and NAT must exist before first boot, or the SSM agent and
  # the tool downloads fail.
  depends_on = [
    aws_nat_gateway.lab,
    aws_route_table_association.private,
    aws_vpc_endpoint.ssm,
    aws_kms_key_policy.lab,
  ]

  tags = { Name = "${var.lab_id}-bastion", Role = "openshift-install-fips" }
}

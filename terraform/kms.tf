data "aws_caller_identity" "current" {}

locals {
  account_id   = data.aws_caller_identity.current.account_id
  cluster_name = var.cluster_name != "" ? var.cluster_name : substr(var.lab_id, 0, 14)
}

# Key policy for aws_kms_key.lab.
# Statement 1 keeps the account root as key owner, which also lets IAM policies
# (installer role, bastion role, cluster roles) grant key use. Without it the
# key could become unmanageable.
data "aws_iam_policy_document" "kms_lab" {
  statement {
    sid       = "EnableRootAndIamPolicies"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:root"]
    }
  }

  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${var.region}.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = ["arn:aws:logs:${var.region}:${local.account_id}:log-group:*"]
    }
  }

  # Cluster storage drivers, and S3 are created later
  # by the installer or the lab, so they cannot be named here. Allow account
  # principals to use the key only through EBS (EC2) and S3 in this region.
  statement {
    sid    = "AllowAccountUseViaEc2AndS3"
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [local.account_id]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values = [
        "ec2.${var.region}.amazonaws.com",
        "s3.${var.region}.amazonaws.com",
      ]
    }
  }

  statement {
    sid       = "AllowGrantsForAwsResources"
    effect    = "Allow"
    actions   = ["kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "StringEquals"
      variable = "kms:CallerAccount"
      values   = [local.account_id]
    }

    condition {
      test     = "Bool"
      variable = "kms:GrantIsForAWSResource"
      values   = ["true"]
    }
  }
}

resource "aws_kms_key_policy" "lab" {
  key_id = aws_kms_key.lab.id
  policy = data.aws_iam_policy_document.kms_lab.json
}

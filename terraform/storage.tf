locals {
  log_bucket       = "${var.lab_id}-logs-${local.account_id}"
  artifacts_bucket = "${var.lab_id}-artifacts-${local.account_id}"
  buckets = {
    log       = local.log_bucket
    artifacts = local.artifacts_bucket
  }
}

# ---- Log bucket: Object Lock (Compliance), versioning, SSE-KMS ----

resource "aws_s3_bucket" "log" {
  bucket              = local.log_bucket
  object_lock_enabled = true

  # Compliance-locked versions cannot be force-deleted. They expire through the
  # lifecycle rule below, after which the bucket empties and can be destroyed.
  tags = { Name = local.log_bucket, Purpose = "siem-log-store" }

  lifecycle {
    precondition {
      condition     = var.log_expire_days > var.log_retention_days
      error_message = "log_expire_days must be greater than log_retention_days."
    }
  }
}

resource "aws_s3_bucket_versioning" "log" {
  bucket = aws_s3_bucket.log.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "log" {
  bucket = aws_s3_bucket.log.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.log_retention_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.log]
}

resource "aws_s3_bucket_lifecycle_configuration" "log" {
  bucket = aws_s3_bucket.log.id

  rule {
    id     = "archive-then-expire"
    status = "Enabled"

    filter {}

    transition {
      days          = var.log_archive_days
      storage_class = "GLACIER"
    }

    expiration {
      days = var.log_expire_days
    }

    noncurrent_version_expiration {
      noncurrent_days = var.log_expire_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }

  depends_on = [aws_s3_bucket_versioning.log]
}

# ---- Artifacts bucket: install-config in, kubeconfig and status out ----
# Not versioned on purpose: install-config.yaml holds the pull secret and the
# bastion deletes it after reading it. With versioning, "delete" would only add
# a delete marker and leave the pull secret (and later the kubeadmin password)
# readable as a noncurrent version.

resource "aws_s3_bucket" "artifacts" {
  bucket        = local.artifacts_bucket
  force_destroy = true

  tags = { Name = local.artifacts_bucket, Purpose = "installer-handoff" }
}

# ---- Settings common to all three buckets ----

resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = local.buckets
  bucket   = each.value

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.lab.arn
    }
  }

  depends_on = [aws_s3_bucket.log, aws_s3_bucket.artifacts]
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each = local.buckets
  bucket   = each.value

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  depends_on = [aws_s3_bucket.log, aws_s3_bucket.artifacts]
}

data "aws_iam_policy_document" "tls_only" {
  for_each = local.buckets

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = ["arn:aws:s3:::${each.value}", "arn:aws:s3:::${each.value}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  # Only the bastion role may read the install-config (pull secret). The lab
  # shell only needs to write it.
  dynamic "statement" {
    for_each = each.key == "artifacts" ? [1] : []

    content {
      sid       = "OnlyBastionReadsInstallConfig"
      effect    = "Deny"
      actions   = ["s3:GetObject", "s3:GetObjectVersion"]
      resources = ["arn:aws:s3:::${each.value}/install/install-config.yaml"]

      principals {
        type        = "*"
        identifiers = ["*"]
      }

      condition {
        test     = "StringNotEquals"
        variable = "aws:PrincipalArn"
        values   = [aws_iam_role.bastion.arn]
      }
    }
  }
}

resource "aws_s3_bucket_policy" "all" {
  for_each = local.buckets
  bucket   = each.value
  policy   = data.aws_iam_policy_document.tls_only[each.key].json

  depends_on = [aws_s3_bucket_public_access_block.all]
}

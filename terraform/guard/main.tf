# Lab cost guard (see ../../COST-CONTROLS.md). Deploy once per AWS account and
# region, separate from any lab, so destroying a lab never removes it.
# Nothing here has run on AWS.

terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      ManagedBy = "terraform"
      Purpose   = "lab-guard"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id    = data.aws_caller_identity.current.account_id
  name          = "lab-guard"
  bucket_name   = "${local.name}-${local.account_id}-${var.region}"
  project_name  = "${local.name}-runner"
  codebuild_arn = "arn:aws:codebuild:${var.region}:${local.account_id}:project/${local.project_name}"
}

# ---------------------------------------------------------------- bucket

resource "aws_s3_bucket" "guard" {
  bucket = local.bucket_name
}

resource "aws_s3_bucket_public_access_block" "guard" {
  bucket                  = aws_s3_bucket.guard.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "guard" {
  bucket = aws_s3_bucket.guard.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "guard" {
  bucket = aws_s3_bucket.guard.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "guard" {
  bucket = aws_s3_bucket.guard.id

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_iam_policy_document" "bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.guard.arn, "${aws_s3_bucket.guard.arn}/*"]

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
}

resource "aws_s3_bucket_policy" "guard" {
  bucket = aws_s3_bucket.guard.id
  policy = data.aws_iam_policy_document.bucket.json

  depends_on = [aws_s3_bucket_public_access_block.guard]
}

resource "aws_s3_bucket_lifecycle_configuration" "guard" {
  bucket = aws_s3_bucket.guard.id

  rule {
    id     = "saves-90-days"
    status = "Enabled"

    filter {
      prefix = "saves/"
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }

  rule {
    id     = "heartbeat-7-days"
    status = "Enabled"

    filter {
      prefix = "heartbeat/"
    }

    expiration {
      days = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }

  rule {
    id     = "requests-7-days"
    status = "Enabled"

    filter {
      prefix = "requests/"
    }

    expiration {
      days = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }

  rule {
    id     = "other-noncurrent-30-days"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.guard]
}

# ---------------------------------------------------------------- lab code zip

# The lab Terraform (the parent directory) without this stack, the sweeper,
# local state, provider caches or variable files. CodeBuild applies and
# destroys a lab from this zip.
data "archive_file" "code" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/.build/terraform.zip"

  excludes = [
    "guard/**",
    "sweeper/**",
    ".terraform/**",
    "**/.terraform/**",
    "*.tfstate",
    "*.tfstate.*",
    "**/*.tfstate",
    "**/*.tfstate.*",
    "*.tfvars",
    "*.tfvars.json",
    "crash.log",
    "**/__pycache__/**",
    "*.zip",
  ]
}

resource "aws_s3_object" "code" {
  bucket = aws_s3_bucket.guard.id
  key    = "code/terraform.zip"
  source = data.archive_file.code.output_path
  etag   = data.archive_file.code.output_md5
}

# ---------------------------------------------------------------- SNS

resource "aws_sns_topic" "notify" {
  name = "${local.name}-notify"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.notify.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic" "budget" {
  name = "${local.name}-budget"
}

data "aws_iam_policy_document" "budget_topic" {
  statement {
    sid       = "AllowBudgetsPublish"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.budget.arn]

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:budgets::${local.account_id}:*"]
    }
  }
}

resource "aws_sns_topic_policy" "budget" {
  arn    = aws_sns_topic.budget.arn
  policy = data.aws_iam_policy_document.budget_topic.json
}

resource "aws_sns_topic_subscription" "budget_lambda" {
  topic_arn = aws_sns_topic.budget.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.guard.arn
}

resource "aws_lambda_permission" "sns" {
  statement_id  = "AllowBudgetTopic"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guard.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.budget.arn
}

# ---------------------------------------------------------------- Lambda

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda/guard.py"
  output_path = "${path.module}/.build/guard.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda" {
  statement {
    sid       = "ReadBucketObjects"
    actions   = ["s3:GetObject"]
    resources = [for p in ["labs", "heartbeat", "keep", "requests", "state"] : "${aws_s3_bucket.guard.arn}/${p}/*"]
  }

  statement {
    sid       = "WriteState"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.guard.arn}/state/*"]
  }

  statement {
    sid       = "DeleteHandledRequests"
    actions   = ["s3:DeleteObject"]
    resources = ["${aws_s3_bucket.guard.arn}/requests/*"]
  }

  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.guard.arn]
  }

  statement {
    sid       = "FindBastion"
    actions   = ["ec2:DescribeInstances"]
    resources = ["*"]
  }

  statement {
    sid       = "RunSaveDocument"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ssm:${var.region}::document/AWS-RunShellScript"]
  }

  statement {
    sid       = "RunSaveOnLabInstances"
    actions   = ["ssm:SendCommand"]
    resources = ["arn:aws:ec2:${var.region}:${local.account_id}:instance/*"]

    condition {
      test     = "Null"
      variable = "ssm:resourceTag/LabId"
      values   = ["false"]
    }
  }

  statement {
    sid       = "ReadCommandResult"
    actions   = ["ssm:GetCommandInvocation"]
    resources = ["*"]
  }

  statement {
    sid       = "RunBuilds"
    actions   = ["codebuild:StartBuild", "codebuild:BatchGetBuilds"]
    resources = [local.codebuild_arn]
  }

  statement {
    sid       = "Notify"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.notify.arn]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "guard"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "guard" {
  function_name    = local.name
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.13"
  handler          = "guard.handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 120
  memory_size      = 256

  environment {
    variables = {
      GUARD_BUCKET       = aws_s3_bucket.guard.id
      GUARD_REGION       = var.region
      NOTIFY_TOPIC_ARN   = aws_sns_topic.notify.arn
      BUDGET_TOPIC_ARN   = aws_sns_topic.budget.arn
      CODEBUILD_PROJECT  = local.project_name
      IDLE_HOURS         = tostring(var.idle_hours)
      WARN_MINUTES       = tostring(var.warn_minutes)
      BUILD_GRACE_HOURS  = tostring(var.build_grace_hours)
      PAUSE_DESTROY_DAYS = tostring(var.pause_destroy_days)
      DRY_RUN            = var.dry_run ? "true" : "false"
      SPEND_DESTROY_PCT  = tostring(var.spend_destroy_pct)
    }
  }

  depends_on = [aws_iam_role_policy.lambda, aws_iam_role_policy_attachment.lambda_logs]
}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${local.name}-schedule"
  schedule_expression = var.schedule
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule = aws_cloudwatch_event_rule.schedule.name
  arn  = aws_lambda_function.guard.arn
}

resource "aws_lambda_permission" "events" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guard.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}

# ---------------------------------------------------------------- CodeBuild

data "aws_iam_policy_document" "codebuild_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codebuild" {
  name               = "${local.name}-codebuild"
  assume_role_policy = data.aws_iam_policy_document.codebuild_assume.json
}

# BROAD ON PURPOSE. This role runs terraform apply/destroy of a whole lab
# (VPC, IAM, KMS, S3, EC2, Route 53, Budgets) and sweep.sh, which destroys the
# OpenShift cluster the installer built. A narrower policy would break the
# destroy. The explicit denies below only block the most dangerous account-wide
# changes and edits to the guard's own roles. Deploy the guard only in a
# dedicated lab account.
data "aws_iam_policy_document" "codebuild" {
  statement {
    sid    = "LabInfrastructure"
    effect = "Allow"
    actions = [
      "ec2:*",
      "elasticloadbalancing:*",
      "autoscaling:*",
      "iam:*",
      "kms:*",
      "s3:*",
      "route53:*",
      "budgets:*",
      "ssm:*",
      "logs:*",
      "cloudwatch:*",
      "events:*",
      "sns:*",
      "tag:*",
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "DenyAccountWideChanges"
    effect = "Deny"
    actions = [
      "organizations:*",
      "account:*",
      "iam:CreateUser",
      "iam:CreateAccessKey",
      "iam:CreateLoginProfile",
      "iam:UpdateAccountPasswordPolicy",
      "iam:DeleteAccountPasswordPolicy",
      "iam:CreateSAMLProvider",
      "iam:CreateOpenIDConnectProvider",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "DenyEditingTheGuard"
    effect    = "Deny"
    actions   = ["iam:*"]
    resources = ["arn:aws:iam::${local.account_id}:role/${local.name}-*"]
  }

  statement {
    sid       = "DenyChangingTheGuardBucket"
    effect    = "Deny"
    actions   = ["s3:DeleteBucket", "s3:PutBucketPolicy", "s3:PutLifecycleConfiguration"]
    resources = [aws_s3_bucket.guard.arn]
  }
}

resource "aws_iam_role_policy" "codebuild" {
  name   = "runner"
  role   = aws_iam_role.codebuild.id
  policy = data.aws_iam_policy_document.codebuild.json
}

resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/aws/codebuild/${local.project_name}"
  retention_in_days = 30
}

resource "aws_codebuild_project" "runner" {
  name          = local.project_name
  description   = "Pause, resume or destroy one lab (ACTION, LAB_ID)."
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 100 # minutes; under the guard's 2 hour stuck-state rule

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type = "BUILD_GENERAL1_MEDIUM"
    image        = "aws/codebuild/amazonlinux-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"

    environment_variable {
      name  = "GUARD_BUCKET"
      value = aws_s3_bucket.guard.id
    }

    environment_variable {
      name  = "GUARD_REGION"
      value = var.region
    }

    environment_variable {
      name  = "EXPECTED_ACCOUNT_ID"
      value = local.account_id
    }

    environment_variable {
      name  = "TF_IN_AUTOMATION"
      value = "1"
    }

    environment_variable {
      name  = "ACTION"
      value = "none"
    }

    environment_variable {
      name  = "LAB_ID"
      value = "none"
    }
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.codebuild.name
    }
  }

  source {
    type      = "NO_SOURCE"
    buildspec = file("${path.module}/buildspec.yml")
  }

  depends_on = [aws_iam_role_policy.codebuild, aws_s3_object.code]
}

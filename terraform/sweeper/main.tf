# Account-level sweeper DETECTOR. Deploy once per account and region, separate
# from any lab, so destroying a lab never removes it.
#
# Design: an hourly Lambda finds resources whose AutoDestroyAfter tag is before
# today (UTC) and emails a list of expired LabIds. It has read-only tag access
# and cannot destroy anything. Destruction is done by scripts/sweep.sh, run by
# an operator or a CI job, because destroying a cluster needs the installer and
# Terraform state, which a Lambda does not have.

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

variable "region" {
  type        = string
  description = "Region to sweep. Tagging API results are per region."
}

variable "alert_email" {
  type        = string
  description = "Address that receives the expired-lab list (SNS email subscription must be confirmed)."
}

variable "schedule" {
  type        = string
  default     = "rate(1 hour)"
  description = "EventBridge schedule expression."
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      ManagedBy = "terraform"
      Purpose   = "lab-sweeper"
    }
  }
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda/sweeper.py"
  output_path = "${path.module}/sweeper.zip"
}

resource "aws_sns_topic" "expired" {
  name = "lab-sweeper-expired"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.expired.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sweeper" {
  name               = "lab-sweeper"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "sweeper" {
  statement {
    sid       = "ReadTags"
    actions   = ["tag:GetResources"]
    resources = ["*"]
  }

  statement {
    sid       = "Notify"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.expired.arn]
  }
}

resource "aws_iam_role_policy" "sweeper" {
  name   = "sweeper"
  role   = aws_iam_role.sweeper.id
  policy = data.aws_iam_policy_document.sweeper.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.sweeper.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "sweeper" {
  function_name    = "lab-sweeper"
  role             = aws_iam_role.sweeper.arn
  runtime          = "python3.13"
  handler          = "sweeper.handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      TOPIC_ARN = aws_sns_topic.expired.arn
    }
  }
}

resource "aws_cloudwatch_event_rule" "hourly" {
  name                = "lab-sweeper-schedule"
  schedule_expression = var.schedule
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule = aws_cloudwatch_event_rule.hourly.name
  arn  = aws_lambda_function.sweeper.arn
}

resource "aws_lambda_permission" "events" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sweeper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly.arn
}

output "sns_topic_arn" {
  value = aws_sns_topic.expired.arn
}

output "lambda_name" {
  value = aws_lambda_function.sweeper.function_name
}

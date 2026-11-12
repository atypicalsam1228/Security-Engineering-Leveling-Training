# Cost-guard permissions for the identity the learner's lab shell runs as.
# `lab shell` does not use the bastion role. It passes the learner's own AWS
# credentials (AWS_PROFILE, AWS_ACCESS_KEY_ID and so on) into the tools
# container, so Terraform cannot know that identity. Name it in
# learner_user_names or learner_role_names to attach the policy, or attach the
# policy ARN (output learner_guard_policy_arn) by hand.
# Everything here is skipped when guard_bucket is empty.

variable "learner_user_names" {
  type        = list(string)
  default     = []
  description = "IAM user names the learner's lab shell runs as. The learner guard policy is attached to each."
}

variable "learner_role_names" {
  type        = list(string)
  default     = []
  description = "IAM role names the learner's lab shell runs as. The learner guard policy is attached to each."
}

data "aws_iam_policy_document" "learner_guard" {
  count = var.guard_bucket != "" ? 1 : 0

  # Heartbeat, keep-alive and pause/resume requests for this lab only.
  statement {
    sid     = "GuardWriteOwnLab"
    effect  = "Allow"
    actions = ["s3:PutObject"]
    resources = [
      "arn:aws:s3:::${var.guard_bucket}/heartbeat/${var.lab_id}",
      "arn:aws:s3:::${var.guard_bucket}/keep/${var.lab_id}",
      "arn:aws:s3:::${var.guard_bucket}/requests/${var.lab_id}.json",
    ]
  }

  # Guard state and saves for this lab only.
  statement {
    sid     = "GuardReadOwnLab"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "arn:aws:s3:::${var.guard_bucket}/state/${var.lab_id}.json",
      "arn:aws:s3:::${var.guard_bucket}/saves/${var.lab_id}/*",
    ]
  }

  statement {
    sid       = "GuardListOwnSaves"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.guard_bucket}"]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["saves/${var.lab_id}/*", "saves/${var.lab_id}/", "state/${var.lab_id}.json"]
    }
  }
}

resource "aws_iam_policy" "learner_guard" {
  count = var.guard_bucket != "" ? 1 : 0

  name        = "${var.lab_id}-learner-guard"
  description = "Cost-guard permissions for the lab shell identity of lab ${var.lab_id}"
  policy      = data.aws_iam_policy_document.learner_guard[0].json
}

resource "aws_iam_user_policy_attachment" "learner_guard" {
  for_each   = var.guard_bucket != "" ? toset(var.learner_user_names) : toset([])
  user       = each.value
  policy_arn = aws_iam_policy.learner_guard[0].arn
}

resource "aws_iam_role_policy_attachment" "learner_guard" {
  for_each   = var.guard_bucket != "" ? toset(var.learner_role_names) : toset([])
  role       = each.value
  policy_arn = aws_iam_policy.learner_guard[0].arn
}

output "learner_guard_policy_arn" {
  description = "Attach this to the identity the lab shell runs as if you did not set learner_user_names or learner_role_names. Empty when the guard is off."
  value       = try(aws_iam_policy.learner_guard[0].arn, "")
}

# CPS-3 simulates a scoped IAM policy with `aws iam simulate-custom-policy`. The policy is passed inline and the
# call creates nothing, but the learner identity needs iam:SimulateCustomPolicy. The action has no resource-level
# scoping in IAM, so the resource is "*". Created only when a learner user or role is named; this is separate
# from the cost-guard policy so it also works when guard_bucket is empty.
locals {
  learner_cps_enabled = length(var.learner_user_names) + length(var.learner_role_names) > 0
}

data "aws_iam_policy_document" "learner_cps" {
  count = local.learner_cps_enabled ? 1 : 0

  statement {
    sid       = "SimulateInlinePolicyOnly"
    effect    = "Allow"
    actions   = ["iam:SimulateCustomPolicy"]
    resources = ["*"]
  }

  # CPS-4 reads the cluster volume encryption and the key state with two read-only describe calls.
  statement {
    sid       = "ReadOnlyDescribeForCps4"
    effect    = "Allow"
    actions   = ["ec2:DescribeVolumes", "kms:DescribeKey"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "learner_cps" {
  count = local.learner_cps_enabled ? 1 : 0

  name        = "${var.lab_id}-learner-iam-simulate"
  description = "Lets the lab shell identity of lab ${var.lab_id} run aws iam simulate-custom-policy (CPS-3) and the read-only describe calls in CPS-4"
  policy      = data.aws_iam_policy_document.learner_cps[0].json
}

resource "aws_iam_user_policy_attachment" "learner_cps" {
  for_each   = local.learner_cps_enabled ? toset(var.learner_user_names) : toset([])
  user       = each.value
  policy_arn = aws_iam_policy.learner_cps[0].arn
}

resource "aws_iam_role_policy_attachment" "learner_cps" {
  for_each   = local.learner_cps_enabled ? toset(var.learner_role_names) : toset([])
  role       = each.value
  policy_arn = aws_iam_policy.learner_cps[0].arn
}

output "learner_cps_policy_arn" {
  description = "Attach this to the identity the lab shell runs as if you did not set learner_user_names or learner_role_names (CPS-3 needs iam:SimulateCustomPolicy, CPS-4 needs ec2:DescribeVolumes and kms:DescribeKey). Empty when no learner is named."
  value       = try(aws_iam_policy.learner_cps[0].arn, "")
}

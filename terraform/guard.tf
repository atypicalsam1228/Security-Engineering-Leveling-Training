# Registration of this lab with the guard stack (COST-CONTROLS.md section 3).
# Everything here is skipped when guard_bucket is empty.

locals {
  guard_enabled = var.guard_bucket != ""
}

data "aws_kms_alias" "state" {
  count = local.guard_enabled && var.state_kms_key_arn == "" ? 1 : 0
  name  = "alias/${var.lab_id}-tfstate"
}

# Keeps the first-apply timestamp so registered_at does not change on every plan.
resource "terraform_data" "registered_at" {
  count = local.guard_enabled ? 1 : 0
  input = timestamp()

  lifecycle {
    ignore_changes = [input]
  }
}

locals {
  registered_state_bucket = var.state_bucket != "" ? var.state_bucket : "${var.lab_id}-tfstate-${local.account_id}"
  registered_state_kms    = var.state_kms_key_arn != "" ? var.state_kms_key_arn : try(data.aws_kms_alias.state[0].target_key_arn, "")

  # Every input variable except paused. CodeBuild re-applies with these plus
  # -var paused=true|false, so anything left out would revert to its default.
  registered_tf_vars = {
    lab_id                 = var.lab_id
    region                 = var.region
    destroy_after          = var.destroy_after
    alert_email            = var.alert_email
    budget_limit_usd       = var.budget_limit_usd
    cluster_name           = var.cluster_name
    instance_type          = var.instance_type
    bastion_instance_type  = var.bastion_instance_type
    bastion_ami_id         = var.bastion_ami_id
    ocp_channel            = var.ocp_channel
    log_retention_days     = var.log_retention_days
    log_archive_days       = var.log_archive_days
    log_expire_days        = var.log_expire_days
    enable_ssm_endpoints   = var.enable_ssm_endpoints
    guard_bucket           = var.guard_bucket
    guard_budget_topic_arn = var.guard_budget_topic_arn
    spend_destroy_pct      = var.spend_destroy_pct
    state_bucket           = var.state_bucket
    state_key              = var.state_key
    state_kms_key_arn      = var.state_kms_key_arn
    learner_user_names     = var.learner_user_names
    learner_role_names     = var.learner_role_names
  }
}

resource "aws_s3_object" "registration" {
  count        = local.guard_enabled ? 1 : 0
  bucket       = var.guard_bucket
  key          = "labs/${var.lab_id}/registration.json"
  content_type = "application/json"

  content = jsonencode({
    lab_id            = var.lab_id
    region            = var.region
    state_bucket      = local.registered_state_bucket
    state_key         = var.state_key
    state_kms_key_arn = local.registered_state_kms
    destroy_after     = var.destroy_after
    alert_email       = var.alert_email
    registered_at     = terraform_data.registered_at[0].output
    tf_vars           = local.registered_tf_vars
  })

  lifecycle {
    precondition {
      condition     = var.guard_budget_topic_arn != ""
      error_message = "guard_budget_topic_arn is required when guard_bucket is set."
    }
  }
}

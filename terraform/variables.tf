variable "lab_id" {
  type        = string
  description = "Short name of this lab. Used in names and tags."
}

variable "region" {
  type        = string
  description = "AWS region for every resource."
}

variable "destroy_after" {
  type        = string
  description = "Date (YYYY-MM-DD) after which this lab should be destroyed."

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.destroy_after))
    error_message = "destroy_after must look like 2026-10-26."
  }
}

variable "alert_email" {
  type        = string
  description = "Address that receives budget alerts."
}

variable "budget_limit_usd" {
  type        = string
  default     = "25"
  description = "Monthly budget in US dollars. Placeholder; the lab sets the real amount."
}

# ---- Variables added (the lab build owns these) ----

variable "cluster_name" {
  type        = string
  default     = ""
  description = "OpenShift cluster name (CLUSTER_NAME). Empty means the first 14 characters of lab_id."

  validation {
    condition     = var.cluster_name == "" || can(regex("^[a-z][a-z0-9-]{0,13}$", var.cluster_name))
    error_message = "cluster_name must be 1 to 14 lowercase letters, digits or hyphens, starting with a letter."
  }
}

variable "instance_type" {
  type        = string
  default     = "m6i.4xlarge"
  description = "Single-node cluster instance type. Must match install-config.yaml. Placeholder size; confirm on a live lab."
}

variable "bastion_instance_type" {
  type        = string
  default     = "m6i.large"
  description = "Instance type of the FIPS-mode RHEL 9 bastion that runs openshift-install-fips."
}

variable "bastion_ami_id" {
  type        = string
  default     = ""
  description = "Override the RHEL 9 AMI. Empty means look up the latest Red Hat RHEL 9 AMI."
}

variable "ocp_channel" {
  type        = string
  default     = "stable-4.22"
  description = "Directory under mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp used to find oc and the release image."
}

variable "log_retention_days" {
  type        = number
  default     = 1
  description = "Default S3 Object Lock retention (Compliance mode) on the log bucket. Short on purpose so a lab can be destroyed."
}

variable "log_archive_days" {
  type        = number
  default     = 7
  description = "Days before log objects move to Glacier."
}

variable "log_expire_days" {
  type        = number
  default     = 14
  description = "Days before log object versions expire so the bucket can empty and be destroyed. Must exceed log_retention_days."
}

variable "enable_ssm_endpoints" {
  type        = bool
  default     = true
  description = "Create ssm, ssmmessages and ec2messages interface endpoints so Session Manager works privately. Costs hourly per endpoint."
}

# ---- Cost controls (COST-CONTROLS.md). All optional. ----

variable "paused" {
  type        = bool
  default     = false
  description = "When true, the NAT gateway, its Elastic IP, the NAT route, the SSM interface endpoints and the bastion are not created (or are destroyed). Disks, subnets, KMS key, buckets and IAM stay."
}

variable "guard_bucket" {
  type        = string
  default     = ""
  description = "Guard bucket name (guard stack output guard_bucket). Empty disables registration, learner guard permissions, the export script and the GUARD_BUCKET output."

  validation {
    condition     = var.guard_bucket == "" || can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.guard_bucket))
    error_message = "guard_bucket must be empty or a valid S3 bucket name."
  }
}

variable "guard_budget_topic_arn" {
  type        = string
  default     = ""
  description = "ARN of the guard's budget SNS topic (guard stack output). Required when guard_bucket is set."
}

variable "spend_destroy_pct" {
  type        = number
  default     = 100
  description = "Percent of budget_limit_usd (ACTUAL spend) at which the guard destroys the lab. Only used when guard_bucket is set."

  validation {
    condition     = var.spend_destroy_pct >= 1 && var.spend_destroy_pct <= 1000
    error_message = "spend_destroy_pct must be between 1 and 1000."
  }
}

variable "state_bucket" {
  type        = string
  default     = ""
  description = "Terraform state bucket recorded in registration.json. Empty means <lab_id>-tfstate-<account id>, the name lab up creates. `lab up` passes the real name from its backend-config."
}

variable "state_key" {
  type        = string
  default     = "lab/terraform.tfstate"
  description = "State object key recorded in registration.json. Must match the key in versions.tf."
}

variable "state_kms_key_arn" {
  type        = string
  default     = ""
  description = "State KMS key ARN recorded in registration.json. Empty means look up alias/<lab_id>-tfstate. `lab up` passes the key ARN it gives to -backend-config=kms_key_id."
}

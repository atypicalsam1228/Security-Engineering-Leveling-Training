# Outputs added beyond the five in outputs.tf. These feed the
# lab environment variables in LAB-CONTRACT.md. `lab up` reads lab_env as JSON.

output "lab_id" {
  value = var.lab_id
}

output "aws_region" {
  value = var.region
}

output "cluster_name" {
  value = local.cluster_name
}

output "destroy_after" {
  description = "Date (YYYY-MM-DD) used for the AutoDestroyAfter tag; lab-install.sh copies it into install-config.yaml userTags."
  value       = var.destroy_after
}

output "instance_type" {
  description = "Cluster node instance type; lab-install.sh writes it into install-config.yaml so the two cannot disagree."
  value       = var.instance_type
}

output "availability_zone" {
  value = local.az
}

output "log_bucket" {
  description = "Object Lock (Compliance) log bucket for Loki."
  value       = aws_s3_bucket.log.id
}

output "artifacts_bucket" {
  description = "Handoff bucket between the lab shell and the bastion."
  value       = aws_s3_bucket.artifacts.id
}

output "bastion_instance_id" {
  description = "Empty string while paused (no bastion)."
  value       = try(aws_instance.bastion[0].id, "")
}

output "guard_bucket" {
  description = "Guard bucket name; empty when cost controls are not configured."
  value       = var.guard_bucket
}

output "installer_policy_arns" {
  value = [for p in aws_iam_policy.installer : p.arn]
}

output "state_bucket_hint" {
  description = "Name of the Terraform state bucket the lab creates."
  value       = "${var.lab_id}-tfstate-${local.account_id}"
}

# Env var names from LAB-CONTRACT.md, ready to export.
output "lab_env" {
  value = {
    LAB_ID           = var.lab_id
    AWS_REGION       = var.region
    CLUSTER_NAME     = local.cluster_name
    VPC_ID           = aws_vpc.lab.id
    KMS_KEY_ARN      = aws_kms_key.lab.arn
    LOG_BUCKET       = aws_s3_bucket.log.id
    ARTIFACTS_BUCKET = aws_s3_bucket.artifacts.id
    BASTION_ID       = try(aws_instance.bastion[0].id, "")
    GUARD_BUCKET     = var.guard_bucket
  }
}

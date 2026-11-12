output "guard_bucket" {
  value       = aws_s3_bucket.guard.id
  description = "Pass to each lab as Terraform variable guard_bucket."
}

output "budget_topic_arn" {
  value       = aws_sns_topic.budget.arn
  description = "SNS topic that lab budgets publish to at spend_destroy_pct."
}

output "notify_topic_arn" {
  value       = aws_sns_topic.notify.arn
  description = "SNS topic the guard emails through."
}

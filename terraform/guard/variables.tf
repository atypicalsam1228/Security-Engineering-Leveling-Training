variable "region" {
  type        = string
  description = "Region of the guard and of the labs it protects. The guard only acts on labs registered in this region."
}

variable "alert_email" {
  type        = string
  description = "Address that receives guard emails (SNS email subscription must be confirmed)."

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+$", var.alert_email))
    error_message = "alert_email must look like an email address."
  }
}

variable "idle_hours" {
  type        = number
  default     = 2
  description = "Hours without activity before a lab is saved and paused."

  validation {
    condition     = var.idle_hours >= 1 && var.idle_hours == floor(var.idle_hours)
    error_message = "idle_hours must be a whole number >= 1."
  }
}

variable "warn_minutes" {
  type        = number
  default     = 30
  description = "Warn this many minutes before the pause."

  validation {
    condition     = var.warn_minutes >= 0 && var.warn_minutes < var.idle_hours * 60 && var.warn_minutes == floor(var.warn_minutes)
    error_message = "warn_minutes must be a whole number >= 0 and less than idle_hours * 60."
  }
}

variable "build_grace_hours" {
  type        = number
  default     = 2
  description = "Hours after registration during which a lab is never paused for idleness."

  validation {
    condition     = var.build_grace_hours >= 0 && var.build_grace_hours == floor(var.build_grace_hours)
    error_message = "build_grace_hours must be a whole number >= 0."
  }
}

variable "pause_destroy_days" {
  type        = number
  default     = 7
  description = "Days a lab may stay paused before it is destroyed."

  validation {
    condition     = var.pause_destroy_days >= 1 && var.pause_destroy_days == floor(var.pause_destroy_days)
    error_message = "pause_destroy_days must be a whole number >= 1."
  }
}

variable "schedule" {
  type        = string
  default     = "rate(15 minutes)"
  description = "EventBridge schedule expression for the guard Lambda."
}

variable "dry_run" {
  type        = bool
  default     = true
  description = "When true the guard emails what it would do and changes nothing. Set false only after a first successful test."
}

variable "spend_destroy_pct" {
  type        = number
  default     = 100
  description = "Percent of a lab budget at which the lab (not the guard) notifies the budget topic. Informational here; the lab Terraform sets the real threshold."

  validation {
    condition     = var.spend_destroy_pct > 0 && var.spend_destroy_pct <= 1000
    error_message = "spend_destroy_pct must be between 1 and 1000."
  }
}

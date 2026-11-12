variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "eng-hosted-bastion"
}

variable "instance_type" {
  type        = string
  default     = "t3.large"
  description = "Runs rootless podman for up to 3 learners (lab shell containers). Size up if learners run heavy local tools."
}

variable "learners" {
  type        = map(string)
  description = "Linux user name -> SSH public key. Example: { eng-l1 = \"ssh-ed25519 AAAA...\" }"

  validation {
    condition     = alltrue([for k in keys(var.learners) : can(regex("^eng-l[0-9]{1,2}$", k))])
    error_message = "Learner user names must look like eng-l1."
  }
}

variable "ssh_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed to SSH in. Learners' source addresses are not known, so key-only login on 0.0.0.0/0 is the default."
  default     = ["0.0.0.0/0"]
}

variable "destroy_after" {
  type        = string
  description = "Date (YYYY-MM-DD) after which this bastion should be destroyed. Tag only."
}

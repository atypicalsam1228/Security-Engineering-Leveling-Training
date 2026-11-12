terraform {
  required_version = ">= 1.11"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "3.4.0"
    }
  }
}

variable "kubeconfig" {
  type    = string
  default = "/workspace/.lab/kubeconfig"
}

provider "kubernetes" {
  config_path = var.kubeconfig
  # OpenShift adds its own annotations and labels to a new namespace. Ignore them,
  # so the plan reports only changes to settings that this file sets.
  ignore_annotations = ["openshift[.]io/.*"]
  ignore_labels      = ["pod-security[.]kubernetes[.]io/.*", "security[.]openshift[.]io/.*", "openshift-pipelines[.]tekton[.]dev/.*"]
}

resource "kubernetes_namespace_v1" "iac_lab" {
  metadata {
    name = "iac-lab"
  }
}

resource "kubernetes_resource_quota_v1" "quota" {
  metadata {
    name      = "iac-quota"
    namespace = kubernetes_namespace_v1.iac_lab.metadata[0].name
  }
  spec {
    hard = {
      "pods"            = "10"
      "requests.cpu"    = "2"
      "requests.memory" = "2Gi"
      "limits.cpu"      = "4"
      "limits.memory"   = "4Gi"
    }
  }
}

resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = kubernetes_namespace_v1.iac_lab.metadata[0].name
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_role_v1" "reader" {
  metadata {
    name      = "iac-reader"
    namespace = kubernetes_namespace_v1.iac_lab.metadata[0].name
  }
  rule {
    api_groups = [""]
    resources  = ["pods", "services", "configmaps"]
    verbs      = ["get", "list", "watch"]
  }
}

resource "kubernetes_role_binding_v1" "reader" {
  metadata {
    name      = "iac-reader-binding"
    namespace = kubernetes_namespace_v1.iac_lab.metadata[0].name
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.reader.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = "iac-viewer"
    namespace = "iac-lab"
  }
}

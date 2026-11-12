resource "kubernetes_role_binding_v1" "reader" {
  metadata {
    name      = "pod-reader"
    namespace = kubernetes_namespace_v1.lab.metadata[0].name
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.reader.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = "default"
    namespace = kubernetes_namespace_v1.lab.metadata[0].name
  }
}

resource "kubernetes_role_v1" "reader" {
  metadata {
    name      = "pod-reader"
    namespace = kubernetes_namespace_v1.lab.metadata[0].name
  }

  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list"]
  }
}

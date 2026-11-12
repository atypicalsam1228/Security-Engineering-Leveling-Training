apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: gr-validate-images
spec:
  rules:
    - name: no-latest-tag
      match:
        any:
          - resources: {kinds: ["Pod"], namespaces: ["gr-*"]}
      validate:
        failureAction: Enforce
        message: "The latest tag is not allowed. Use a fixed version."
        pattern:
          spec:
            containers:
              - image: "!*:latest"
    - name: approved-registry
      match:
        any:
          - resources: {kinds: ["Pod"], namespaces: ["gr-*"]}
      validate:
        failureAction: Enforce
        message: "Images must come from the lab registry or registry.access.redhat.com."
        pattern:
          spec:
            =(initContainers):
              - image: "${REGISTRY_HOST}/* | registry.access.redhat.com/*"
            containers:
              - image: "${REGISTRY_HOST}/* | registry.access.redhat.com/*"

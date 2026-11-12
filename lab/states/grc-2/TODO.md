# TODO: start state for GRC-2 (Run Evidence Collection)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: OpenShift Pipelines, namespace build, service accounts evidence-runner and evidence-limited, the two cluster roles and bindings, the collector config map and the Task and Pipeline.
- [live] 1: The pipeline run as evidence-limited gets Forbidden on machineconfigs and apiservers but succeeds on namespaces and clusterpolicies; the pod starts under the default SCC for a new service account.
- [live] 2: Pipeline pods in build can pull quay.io/openshift/origin-cli:4.22.0 and registry.access.redhat.com/ubi9/python-312:1 (the cluster reaches the internet), /usr/bin/oc exists in the first image (verified 2026-11-02 by reading the image layers), and oc in the Python pod uses the service account token without a kubeconfig.
+ [done] 3: ClusterPolicy grc-no-latest-tag (Audit) in demo; Kyverno presence is checked, not installed.
- [live] 3: The Ready condition appears on ClusterPolicy status in Kyverno 1.19.2 (the collector counts it).
- [lab-build] 4: FIPS-mode install of the cluster. Confirm the newest rendered-master MachineConfig has spec.fips true (oc explain machineconfig.spec.fips).

+ [done] 5: ConfigMap evidence-reference (reference answer to the Step 5 writing exercise) in 55-reference-answer.yaml.
- [live] 5: Step 5 on a live cluster: the root_pods check reads the Deployments (pod templates, not live pods, because OpenShift adds runAsNonRoot to running pods) and lists the deployment with runAsNonRoot unset in grc2-workloads. Live run 2026-11-10 showed the live-pod version returns 0; the deployment version is not yet re-run. Verified 2026-11-05 on the earlier nodes_ready version only (count matched, broken copy errored cleanly, config map my-check created and read back); the root-pods version and 35-sample-workloads.yaml are checked by server dry run and a local test with real pod JSON, not yet applied by lab start.

Open items from review (live test or decision):
- Live check: tkn pipelinerun describe --last -o jsonpath, and status.results on a Tekton v1 PipelineRun.

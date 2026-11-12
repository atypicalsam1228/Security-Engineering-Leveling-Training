# TODO: start state for SDR-4 (Build Detections and Pipelines)

`+ [done]` lines are covered by files in this folder; `- [live]` lines can only be confirmed on a live cluster;
`- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Alloy instance files, scenarios, harness, timeline check.
- [live] 1: Alloy accepts a directory (alloy run /etc/alloy) and loki.process with no stages; loki.source.api keeps pushed labels with use_incoming_timestamp.
- [live] 1: Alloy image arguments (run, --storage.path, --server.http.listen-addr) match the image of Deployment alloy.
- [live] 1: stage.json expression objectRef.resource and stage.labels audit_resource produce the label values the detections use.
- [live] 1: oc port-forward svc/alloy-detect works from lab shell.
- [live] 4: Audit profile WriteRequestBodies, so audit records carry requestObject.roleRef (lab_needs in the module).
- [lab-build] 5: Deployment alloy in namespace siem (platform Alloy, installed by the lab build; its image is copied for alloy-detect); Alloy can write to Loki with the same credentials as LOKI_USER.
- [live] 2: Loki query stats field data.stats.summary.totalBytesProcessed in the query_range response.
+ [done] 2: incident records for one actor plus records of other actors.
+ [done] 3: ConfigMap sdr4-harness with harness, scenarios and timeline check.
+ [done] 6: Deployments suspect-app and probe, Service suspect-app (15-suspect.sh); the seeded audit and Falco records name the real suspect pod.
- [live] 6: OVN-Kubernetes enforces the deny-all policy so that curl from the probe pod to the isolated pod ends with a timeout (exit 28, status 000); oc exec returns curl's exit code; ubi9/ubi-minimal has curl; the python-311 image runs python3 -m http.server 8080 as non-root.
- [live] 6: After oc label pod ... app=suspect-app-isolated, the ReplicaSet releases the pod and starts a replacement within a few seconds, and the Service answers 200 from the replacement.
- Decision: records left in Loki after lab reset are ignored, not removed: every record has seed_run=<anchor> and the module searches pin to it (anchor.txt). Each lab start asks Loki to delete older copies (best effort). The suspect pod is the newest Running pod, never a Terminating one.
- [live] Check POST /loki/api/v1/delete with a seed_run!= matcher is accepted (HTTP 204). Nothing depends on it.

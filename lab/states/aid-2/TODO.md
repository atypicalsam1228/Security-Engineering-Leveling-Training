# TODO: start state for AID-2 (Check AI-Written Scripts Before Running)

Lab needs are numbered as in the module's lab_needs list.

+ [done] 1: stub model service code, manifest and deploy script (stub/, 10-ensure-stub.sh).
+ [done] 2: sandbox project ai-sandbox with sandbox-pod and sandbox-evidence (20-sandbox.yaml).
- [live] 1: image registry.access.redhat.com/ubi9/python-311:1 exists and runs python3 with a read-only root filesystem (confirm tag).
- [live] 1: the lab runner applies files in the folder only (stub/ is ignored) and does not choke on a subfolder.
- [live] 2: oc port-forward from lab shell to svc/stub-model works (oc 4.x port-forward accepts svc/NAME).
- [lab-build] 3: Mattermost incoming webhook MM_WEBHOOK_URL reachable from lab shell (issued by the lab chat service).

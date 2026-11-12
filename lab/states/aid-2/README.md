# AID-2 start state: Check AI-Written Scripts Before Running

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Subfolders (`stub/`) are not applied by themselves.

Implemented: the files listed below.
- 10-ensure-stub.sh deploys the deterministic stub model service (namespace ai-lab, Deployment and Service
  stub-model on port 8080). The code is stub/stub.py, the manifest is stub/stub-deployment.yaml. The AID-3, AID-4 and
  AID-5 start states call this same file, so there is one copy of the stub.
- 20-sandbox.yaml creates project ai-sandbox with a running pod and the config map sandbox-evidence.
- The stub serves every scripted answer by request id: script-a, script-b, script-c (this module), findings-1, summary-* and
  logql-good, logql-wrongfield, logql-wide (AID-3), triage-<scenario>-<step> (AID-4), eval-set (AID-5). stub.py was run and tested locally with python3.

Still needed (live cluster or lab build): see TODO.md.

Prerequisites: none. Scripts here have not been run on a live cluster. Shared helpers: ../_common/lib.sh.

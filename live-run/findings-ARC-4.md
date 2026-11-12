# ARC-4 live run (2026-11-10; run in parallel with ARC-3, timings not clean)

Every step and test passed on the first try; no reset. `lab start arc-4` 90 s. Captures: `live-run/captures/ARC-4/` (0-pre, 1a, 1b, 2a, 2b, 3a, test1, 4a, 4b, test2, test3, test3-restore, todo). Earlier mis-run captures (a CRLF slip in the agent's own scripts, see notes) were deleted.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 1.4 s | mesh.yaml 400 bytes; matches |
| 1b | 11.5 s | Netpols created (3 per project); `oc explain` prints the source fields; dry run and apply list peerauthentication and authorizationpolicy as created; arc-a pods 1/1; arc-b web, api, db and atk-copied-mesh 2/2; other two attack pods 1/1. Matches |
| 2a, 2b | 1.4 s each | `5`; "harness.py parses". Match |
| 3a | 35.9 s | arc-a: api-to-db 200, web-to-db fail, stranger fail, copied-label-plain 200, copied-label-mesh 200. arc-b: 200, fail, fail, copied-label-plain fail, copied-label-mesh 403. Matches the checkpoint |
| 4a | 45.2 s | arc-a leaks web-to-db, stranger, copied-label-plain and copied-label-mesh (all four attacks); arc-b leaks `[]`. Policies restored |
| 4b | 476 s (about 8 min) | istiod scaled to 0; arc-b codes unchanged (403 for copied-label-mesh, fail for copied-label-plain); new db pod in arc-a 1/1; arc-b has no db pod; FailedCreate on replicaset/db: `failed calling webhook "namespace.sidecar-injector.istio.io" ... no endpoints available for service "istiod"`; rollouts of istiod and db completed |
| Test 1 | 1.5 s | `true` |
| Test 2 | 5.7 s | 3, 3, 1 |
| Test 3 | 81.6 s | `["copied-label-mesh"]` then `["copied-label-plain","copied-label-mesh"]`. Matches; harness and Test 1 re-run afterwards (39 s) printed `true`, STRICT and ALLOW back |

## Bugs and mismatches (none blocking)
- 4b "takes a few minutes" is about 8 min wall (45 s sleeps plus pod delete and rollouts). The 3a "a minute or two" estimate held (36 s).
- 1b expected output says the policies are "created"; a re-run prints "unchanged".
- The 4b fail-closed claim holds: in arc-b no new db pod appears until istiod returns. The Sail operator did not restore istiod while it was at 0. Existing arc-b sidecars kept enforcing with istiod down (403 and 200 unchanged), which agrees with the module.
- Istio 1.31.1 uses native sidecars: `istio-proxy` and `istio-validation` show under `initContainers`, not `containers`, so a `jq` over `spec.containers` for `istio-proxy` finds nothing; `oc adm top pod --containers` still lists `istio-proxy`.
- `$HOME/arc` is a shared folder: ARC-2, ARC-3 and ARC-5 kit files (netpol.yaml, latency.py and others) sit next to ARC-4's, and `lab start` for another module overwrites netpol.yaml. A concurrent or later `lab start arc-N` could change ARC-4's netpol.yaml; did not break this run, not ruled out.

## Notes
- Mesh blast radius: only arc-b uses the mesh (one MutatingWebhook `istio-sidecar-injector`; only arc-b has `istio-injection=enabled`), so scaling istiod to 0 touched nothing outside arc-b. No shared cluster settings changed; ARC-3 was not affected.
- Agent's own slip, not a module bug: first extracted scripts had CRLF line endings, creating a stray directory named `arc` plus a carriage return in the lab home, which failed the first 1a, 1b, 2a and 2b runs; removed and re-run clean.
- Left in the lab: arc-a and arc-b as built, 3 netpols each, STRICT PeerAuthentication, the db-from-api policy, istiod at 1 replica, results-*.json in `$HOME/arc`.

## TODO [live] status
Confirmed: sailoperator.io/v1 field names (`oc get istio default` is apiVersion sailoperator.io/v1, version v1.31.1, namespace istio-system; the deployment is `istiod` in istio-system); AuthorizationPolicy and PeerAuthentication use security.istio.io/v1 (server dry run accepted v1); the copied-label pod with a sidecar gets HTTP 403 from the db sidecar and plaintext to a STRICT sidecar fails; with istiod at 0 the new arc-b db pod is refused by the injection webhook (FailedCreate) and no pod exists, and the Sail operator did not restore the replica count; `oc adm top pod --containers` lists istio-proxy; `registry.access.redhat.com/ubi9/python-311:1` pulled and ran in all pods (covers [live] 4).

## 2026-11-11 re-run
Pass: 1a, 2a, 2b, 1b, 3a, Test 1 (true), 4a, 4b, Test 2 (3, 3, 1), Test 3 (["copied-label-mesh"] then both). First pass failed only because Kyverno restarted (webhook connection refused) during another agent's CPS work; rerun clean.
Mismatch (step 4b): after istiod returns, the arc-b db ReplicaSet can stay in backoff (FailedCreate "no endpoints available for service istiod") and `oc rollout status deployment/db` waits a long time. A `oc rollout restart deployment/db -n arc-b` cleared it in 8 s. Suggest adding that command after the istiod rollout, with a note.
Captures: live-run/captures/ARC-4/r3b-*, r3c-test2, r3c-test3.

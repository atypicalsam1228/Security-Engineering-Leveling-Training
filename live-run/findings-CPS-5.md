# CPS-5 live run (2026-11-10; run in parallel with ARC-3, timings not clean)

Every step and test ran once, no reset. Only deviation: **Step 2b's cluster-setting patch was skipped on purpose** (bug 1). `lab start cps-5` 11.8 s, INCOMPLETE notice (11 items). Captures: `live-run/captures/CPS-5/` (labels 1a, 1b, 2a, 2b-nopatch, 3a-3d, 4a-4g, 5a, Test1-3, Test2-sim, 4d-placeholder, 4e-placeholder).

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 2.9 s | 31 score.py. Matches |
| 1b | 21.1 s | 2 of 8 (25 percent), 6 edits, 0 of 4 refused, object count 0. Matches |
| 2a | 2.7 s | 10 quota.yaml. Matches |
| 2b | 4.6 s | Template created; **patch skipped** (shared cluster setting, restarts openshift-apiserver while ARC-3 runs) |
| 3a | 2.9 s | 13-line ClusterRole |
| 3b, 3c | 2.3, 3.0 s | 20 and 22 lines. Match |
| 3d | 24.8 s | RBAC created, `can-i` yes, both policies dry-run, applied, Ready |
| 4a to 4c | 2.5 to 3.3 s | 28, 21, 24 lines. Match |
| 4d | 2.8 s | Own lines matched the reference rule; the placeholder run printed "The approved-registry rule has no line like: - image: ..." and exit 1 (sensible failure message) |
| 4e | 2.6 s | 6 of 6 handled as expected |
| 4f | 8.0 s | Dry run and apply pass; stored pattern read back correctly |
| 4g | 2.8 s | "same as the reference" |
| 5a | 116.2 s | Both namespaces 8 of 8, 0 edits, 4 of 4 refused; object count **2 for gr-direct but 1 for gr-after** (expected 2 for both) |
| Test 1 | 5.1 s | Refused by gr-validate-host-access with the autogen message; deployment not found. Matches (PodSecurity warning line first) |
| Test 2 | 21.2 s | Without the template the quota delete fails NotFound; default-deny comes back; quota count 0 |
| Test 3 | 6.1 s | allowed-web created, blocked-web refused naming gr-validate-images and autogen-approved-registry. Matches |

## Bugs
1. **Step 2b and Step 5a depend on a shared cluster setting.** `oc patch project.config.openshift.io cluster` changes `projectRequestTemplate` cluster-wide and restarts openshift-apiserver; not run per the ground rules (`projectRequestTemplate` was empty before and is still empty). Result: `gr-after` from `oc new-project` gets no template quota; object count 1, so the 5a checkpoint ("2 objects in both") fails for it. The Kyverno fallback quota correctly did not fire (exclude on `openshift.io/requester` saw the annotation). Test 2's NotFound with count 0 meant "never existed"; applying the quota to gr-after by hand and deleting it stayed deleted at count 0, matching the module's claim (capture Test2-sim). **Re-run 2b with the patch when the cluster is not shared and confirm the apiserver restart time.**
2. **4f count is wrong.** Module says "a table with five policies"; `oc get clusterpolicy` lists all 19 (agent-, arc-, grc-, gr-). Filter with `| grep '^gr-'`; the same applies to 3d's "table with one line per policy".
3. The Kyverno ClusterPolicy deprecation warning prints after every apply and get; the module mentions it once, for 3d only.
4. Test 1: extra "would violate PodSecurity baseline:latest (hostNetwork=true)" line before the Kyverno error. Test 1's block exits 1 because the apply fails (intended).
5. 5a took 116 s (`sleep 30`, `sleep 15`, 12 applies per namespace); under the module's estimate.

## Notes
- No overlap with ARC-3; existing arc-*, grc-*, agent-* policies are scoped to other namespaces.
- Left in the lab: namespaces gr-before, gr-after, gr-direct; the five gr- ClusterPolicies; ClusterRole gr-kyverno-generate; template guardrail-project-request in openshift-config; files in `/workspace/cps-5`.

## TODO [live] status
Confirmed: background controller account is kyverno-background-controller and the aggregation label works; `openshift.io/requester` is present at namespace creation; autogen applies Pod mutate and validate rules to Deployments including add-if-absent anchors (8 of 8 pass, 4 of 4 refused); the registry rule with `=(initContainers)` is accepted and enforced, learner rule equals the reference; check-registry.py 6 of 6; Kyverno refused the docker.io image and admitted the redhat one; python3 3.9.25 in the lab shell; ubi-minimal at zero replicas admitted (no pull needed); default-deny regeneration works (synchronize).
Not confirmed: apiserver restart time and project API outage from changing `projectRequestTemplate`; template quota applied to new projects; OVN enforcing NetworkPolicy (no traffic tested); REGISTRY_HOST allow-list admitting a built-in registry image; Kyverno version number.

---

# CPS-5 Step 2b re-run with the cluster patch (2026-11-10, alone on the lab)

Authorised by the user. Captures: `2b-patch`, `5a-patched`, `Test2-patched`.

- **Step 2b patch:** `projectRequestTemplate` was empty; after the `oc patch` it reads `guardrail-project-request`. `project.config.openshift.io/cluster patched`.
- **Restart timing:** the Kubernetes API stayed up throughout (60 of 60 probes, one every 5 s for 5 minutes, all up from t+6 s). `oc wait ... Progressing=False` returned at once, and the loop ended 355 s after the patch with `openshift-apiserver` Available True and the template in place. The project API outage the TODO feared was not seen with a plain `oc get ns`; creating a project during the restart window was not probed.
- **Step 5a (new project `gr-after2` created after the patch):** 8 of 8 (100 percent), 0 edits, 4 of 4 refused. Object count is **2 for both `gr-after2` and `gr-direct`**, and the listing shows `resourcequota/guardrail-quota` and `networkpolicy.networking.k8s.io/default-deny`. The checkpoint now holds (62 s). The template quota is applied to new projects (TODO item confirmed).
- **Test 2:** deleting the network policy in `gr-direct` and the quota in `gr-after2`, then waiting 15 s: the policy `default-deny` comes back (Kyverno regenerates it) and the quota count is **0**, matching the module's claim that the template quota does not come back. (20.2 s.)
- Note: the module's Step 5a creates `gr-after` and the earlier `gr-after` (made before the patch) was deleted and replaced by `gr-after2` for this check; a learner who patches first gets `gr-after` right.
- State left: the cluster-wide `projectRequestTemplate` stays set to `guardrail-project-request`, so every new project in this lab now gets the quota. `lab reset cps-5` should revert it (not checked); do so before running other modules that create projects.

---

# 2026-11-11 re-run

Captures: `live-run/captures/CPS-5/rr-*.txt`. `lab start cps-5` took 13.7 s. All commands run as written. For 4d I first ran the placeholder-comment block (4e then said "The approved-registry rule has no line like: - image"), then pasted 4c again and typed `=(initContainers)` plus `containers` image lines `"${REGISTRY_HOST}/* | registry.access.redhat.com/*"`.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 1.7 s | 31 lines, matches |
| 1b | 13.5 s | 2 of 8 (25 percent), 6 edits, 0 of 4 refused, object count 0. Matches |
| 2a / 2b | 1.3 s / 4.7 s | 10 lines; template created, cluster patched. Matches |
| 3a | 1.3 s | role prints (13 lines) |
| 3b / 3c | 1.4 s | 20 / 22 lines |
| 3d | 13.9 s | can-i yes; two gr- policies Ready |
| 4a, 4b, 4c | about 1.5 s | 28, 21, 24 lines |
| 4e | 2.0 s | 6 of 6 |
| 4f | 7.1 s | five gr- policies Ready; pattern read back |
| 4g | 1.9 s | same as the reference |
| 5a | 171.1 s | gr-after and gr-direct: 8 of 8 (100 percent), 0 edits, 4 of 4 refused, object count 2 each |
| Test 1 | 4.6 s | PASS (refused by gr-validate-host-access; PodSecurity warning first, as described) |
| Test 2 | 23.1 s | PASS (default-deny back, quota count 0) |
| Test 3 | 5.8 s | PASS (allowed created, blocked refused naming gr-validate-images) |

## Mismatches
1. 3d and 4f: every `oc apply` and `oc get clusterpolicy` prints `Warning: kyverno.io/v1 ClusterPolicy is deprecated ...` lines. 3d mentions this in its note; 4f's expected output does not. Suggested: add the same note to 4f (and Test 1 output is unaffected).
2. 3d: the table has extra columns (ADMISSION, BACKGROUND, MESSAGE); described as "a table", fine.
3. 5a: wall time was 171 s (the `sleep 30`, apiserver wait and two scoring runs). If the module quotes a duration for this step, it should say about 3 minutes.
4. Test 2 and Test 3: delete lines read `... deleted from <ns> namespace` rather than `deleted`. Update the examples.

Result: PASS (wording differences only).

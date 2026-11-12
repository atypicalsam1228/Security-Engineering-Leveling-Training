# ENG-0 live run (2026-11-10; run in parallel with AID-5, timings not clean)

`lab start eng-0` 23 s, INCOMPLETE notice. Every step ran once, no reset; 4b re-run once and failed the same way. ENG-0 has no Test sections. Captures: `live-run/captures/ENG-0/`. The lab shell was emulated with labrun.sh.

| Step | Wall | Result |
| --- | --- | --- |
| Before you start (install, cost guard, settings, SSO keys, `lab up`) | n/a | Not testable: runs on the learner's laptop |
| 1a `lab shell` | n/a | Interactive, not testable; LAB_ID is set in the emulated shell |
| 1b | 2.6 s | Matches (`ls -l` shows `total 0` with 18-byte files, harmless) |
| 1c | 1.8 s | Matches |
| 2a | 5.3 s | Mismatch: `git log --oneline` shows 4 commits, example shows one |
| 2b | 4.1 s | Matches; push prints the full Gitea URL (redact in screenshots) |
| 2c | 2.9 s | Matches |
| 3a | 6.0 s | Matches in substance (see notes) |
| 3b | 2.6 s | Matches; `yaml: line 5: did not find expected key`, exit 1 |
| 3c | 2.5 s | Matches |
| 4a | 1.7 s | Matches; all six line ranges agree with the script |
| 4b | 9.0 s, rerun 11.4 s | **FAIL**: `DOWN Trivy operator security-tools 1 of 1 pods not ready`, "1 tool(s) down.", exit 1; module expects ten UP lines and exit 0 |

## Bugs
1. **4b / CHECKPOINT fails: Trivy operator not Ready.** The `trivy-operator` pod in security-tools is in CrashLoopBackOff (14 restarts in 88 min), last termination OOMKilled (exit 137), limit 512Mi (request 128Mi), readiness and liveness probe timeouts. The health check flags a real fault. Likely a too-small lab-build memory limit, or load from parallel scans. Raise the limit in the Helm values or lab build and re-check on an idle lab.
2. 2a: the example shows one commit line, the sandbox repo has 4.

## Notes
- 3a: `oc projects` lists about 90 projects (module: "a list that includes demo"); kyverno log lines contain raw ANSI colour codes and one ERR line from AID-5's policy update; `Defaulted container "kyverno" out of: kyverno, kyverno-pre (init)` prints first.
- The start script prints INCOMPLETE although `states/eng-0/TODO.md` has no open [live] or [lab-build] lines.
- Left in the lab: Gitea `labadmin/eng-sandbox` now has commit 59dbabb, so re-running 2b appends a second README line; `~/eng-practice/` in lab-workspace/.lab/home.

## TODO [live] status
Confirmed: Gitea reachable and token can push; eng-sandbox repo has README.md, broken.yaml, health-check.sh; demo-app 1/1 Running with label app=demo-app. Item 4 (pod-name patterns match Running pods): 9 of 10 hold, Trivy operator is CrashLoopBackOff.

# SDR-4 start state: Build Detections and Pipelines

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Other files (python helpers and data folders) are read by the scripts and ignored by the loader.
Files in `reset.d/` run first on `lab reset` only.

Implemented: the files listed below.
- 10-alloy.sh + alloy/: second Alloy instance alloy-detect in siem (image copied from Deployment alloy). alloy-detect-base holds the intake (loki.source.api on port 3500) and the Loki writer; alloy-detect-label holds the labeling stage the learner writes (a pass-through at the start). Alloy loads every .alloy file in /etc/alloy.
- answer-secret-read.logql: reference answer for the detection the learner writes; 20-seed.sh puts it in ConfigMap sdr4-harness, so oc extract copies it in Step 3.
- 20-seed.sh + seed.py + events_sdr4.py + scenarios_sdr4.py + detect_test.py + timeline_check.py + replay.py + evlib.py + lokilib.py: push the incident records (sign-in failures, success, secret reads, exec, shell, role binding, plus decoys) to Loki and create ConfigMap sdr4-harness (also the seed marker).
- 15-suspect.sh + suspect-app.tpl: in the project demo, Deployment suspect-app (one pod serving HTTP on 8080) with Service suspect-app, and Deployment probe (a pod that only sleeps, used for oc exec curl). 20-seed.sh reads the real suspect pod name and seeds it into the audit and Falco records, so the timeline names a pod that exists. The learner writes the quarantine policy and swaps the labels (Step 5).
- reset.d: puts the labeling stage back to a pass-through and removes the quarantine policy, any pod labeled quarantine=true, the suspect-app and probe Deployments, and the Service.

The harness and the timeline check were tested against a local stand-in for Loki, with the Alloy label stage simulated; the Alloy files and the suspect-app workloads have not been run.

Prerequisites: ENG-0 Terminal, Git and Your Lab, and SDR-3. Needs the platform Alloy Deployment alloy in siem and Loki (installed by the lab build).

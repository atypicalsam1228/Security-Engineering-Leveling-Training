# SDR-3 start state: Investigate and Tune

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Other files (python helpers and data folders) are read by the scripts and ignored by the loader.
Files in `reset.d/` run first on `lab reset` only.

Implemented: the files listed below.
- 20-seed.sh + seed.py + events_sdr3.py + evlib.py + lokilib.py + replay.py + review_gate.py: push the exercise records (steady noise from a monitoring client, a small reconnaissance burst, one larger burst, a later sign-in and four secret reads) and create ConfigMap sdr-review in siem (the review gate and its helpers; also the seed marker).
- 30-grafana.sh: alert rule failed-login-burst (fires above 2 in 5 minutes, with a classic condition) and dashboard sdr-auth-overview with a threshold line at 2.
- reset.d: removes the marker, the rule and the dashboard.

The review gate computes its expected answers from events_sdr3.py, replays the Keycloak records under a fresh lab_replay label, and evaluates the live rule expression and threshold. Tested against a local stand-in for Loki with a stub Grafana, not live.

Valid thresholds: noise peaks at 4 failures per 5 minutes, the small burst at 9, the large burst at 16 (counts include the noise). Any value from 4 to 8 passes; 4 is borderline if Loki counts both edges of a window, so the module recommends more headroom.

Prerequisites: ENG-0 Terminal, Git and Your Lab, and SDR-2. Loki and Grafana (with a Loki data source named Loki) come from the lab platform; the rule, folder and dashboard are created here if missing.

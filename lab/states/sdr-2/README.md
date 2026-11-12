# SDR-2 start state: Triage an Alert by Runbook

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml/.json files are applied with `oc apply -f`. Other files (python helpers and data folders) are read by the scripts and ignored by the loader.
Files in `reset.d/` run first on `lab reset` only.

Implemented: the files listed below.
- 10-forwarder.sh: the log collector and forwarder to Loki, created only if missing, so the telemetry-path check reads a real collector.
- 20-seed.sh + seed.py + events_sdr2.py + evlib.py + lokilib.py: push the exercise records to Loki (all tagged lab_seed="sdr-2" so they never mix with real records), post four alert messages to the Mattermost webhook, then create ConfigMap sdr-runbook in siem (triage.py, approved.json, anchor.txt, lokilib.py). The ConfigMap is the seed marker.
- runbook/triage.py: the supplied triage commands (privilege, signin, shell, path, gaps). Tested against a local stand-in for Loki, not a live one.
- reset.d/10-remove-sdr-2-work.sh: removes the marker so the next start seeds fresh records.

Seeded story (minutes before the anchor): A-101 role binding by an approved actor; A-102 seven failed sign-ins then a success from one source; A-103 shell in demo-app with an audit exec record from an approved actor; A-104 shell in demo-batch while the audit stream has a gap (no audit record); infrastructure logs are 24 minutes late (newest record 24 minutes before the anchor).

Prerequisites: ENG-0 Terminal, Git and Your Lab. The collector and forwarder are created here if missing; Loki, Grafana and Mattermost come from the lab platform.

Scripts here have not been run on a live cluster or account. Shared helpers: ../_common/lib.sh.

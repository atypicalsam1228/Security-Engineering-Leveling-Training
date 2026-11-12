# lab platform: the in-lab services

`lab platform` (run by `lab up` after the cluster install) runs `install.sh`, which runs each `NN-name.sh` in order inside the tools container. Every script is safe to repeat. Add a service by adding a numbered script; do not edit finished ones to add something unrelated.

| Script | Does |
|---|---|
| 05-trust.sh | Saves the cluster ingress CA and a CA bundle so `lab shell` trusts the in-lab services |
| 20-gitea.sh to 90-final-check.sh | See `notes-<area>.md` next to each group; versions in `versions-<area>.txt` |

Helpers are in `lib.sh` (`lab_var`, `lab_var_set`, `require_var`, `wait_until`, `wait_rollout`, `route_host`, `helm_apply`, `ingress_ca_file`). Run one script with `lab platform --only 20`. Design and rules: `PLATFORM-BUILD-BRIEF.md` at the project root.

# ENG-1 start state: How Traffic Moves

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent;
.yaml files are applied with `oc apply -f`. Files in `reset.d/` run first on `lab reset` only.

Implemented: 10-namespace.yaml (net-lab), 20-app.sh (applies net-app.tpl: web, which serves HTTP on 8080, client, which only sleeps so the learner can run curl inside it, and the Service web on 8080; no network policy), 50-install-kit.sh (copies break.yaml and allow-client.yaml to $HOME/net).
break.yaml is applied by the learner in step 4: a default-deny policy, an allow rule that names the wrong label, and a Service that targets port 8081. allow-client.yaml is the correct rule, used in the verify section. The learner writes hop_check.py. The Route in step 3 is created by the learner and removed with the namespace.
Still needed (live cluster or lab build): see TODO.md. `lab start` prints it while TODO.md exists.

Prerequisites: ENG-0 (terminal, git, oc and lab basics). No platform tool beyond the OpenShift network plugin is needed.

Scripts here have not been run on a live cluster. Shared helpers: ../_common/lib.sh (sourced by the scripts).

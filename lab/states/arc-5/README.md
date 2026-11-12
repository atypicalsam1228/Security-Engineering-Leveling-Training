# ARC-5 start state: Verify a Reference Architecture

Implemented: 05-preflight.sh, 10-namespace.yaml (arc-ref), 20-app.sh (arc-app.tpl: web, api, db, cache with services and service accounts, NO policies),
50-install-kit.sh (kit/: check_flows.py, drift_timer.py, flows-bad.txt, copied to $HOME/arc). The learner writes flows.yaml, gen_netpol.py, gen_admission.py,
live_net.py, drift_rules.py and conformance.py. Reference versions of those files were run offline against fake cluster data (flow generation, the Kyverno policy shape,
conformance with no drift and with drift), and check_flows.py was run on good and bad files. Scripts have not been run on a live cluster.

# ARC-4 start state: Test Two Designs

Implemented: 10-service-mesh.sh (installs the Service Mesh 3 operator, Istio default and IstioCNI default), 20-namespaces.sh (arc-a plain, arc-b labelled istio-injection=enabled),
30-app.sh (arc-app.tpl into both: web, api, db, service accounts, and attack pods atk-stranger, atk-copied-plain, atk-copied-mesh; NO network or mesh policies),
50-install-kit.sh (latency.py and netpol.yaml to $HOME/arc). The learner writes mesh.yaml, cases.json and harness.py. Platform tool: Red Hat OpenShift Service Mesh 3 Operator (installed by 10-service-mesh.sh via the lab build). Prerequisite: ENG-0. Scripts have not been run on a live cluster.

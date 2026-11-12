# Open items: start state for ENG-1 (How Traffic Moves)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build (Terraform, images, Helm), not by start states.

+ [done] 1: Namespace net-lab with Deployments web and client and the Service web, and no network policy (10-namespace.yaml, 20-app.sh, net-app.tpl).
- [live] 2: OVN-Kubernetes enforces network policy on the cluster, and a dropped connection shows as a curl timeout (exit 28), not a reset.
- [live] 3: The default router certificate and the Route host are reachable from lab shell on port 443 (the apps wildcard is public in this lab).
+ [done] 4: break.yaml and allow-client.yaml are copied to $HOME/net (50-install-kit.sh).
- [live] 5: With the allow rule fixed and the Service still on 8081, curl gets a refused connection (exit 7) and not a timeout. The allow rule has no ports list on purpose, so port 8081 reaches the pod.
- [live] 6: registry.access.redhat.com/ubi9/ubi-minimal:9.5 has curl, and registry.access.redhat.com/ubi9/python-311:1 starts as non-root.

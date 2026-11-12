# TODO: start state for VM-4 (Prioritize by Context and Validate)

+ [done] 1: namespaces, workloads, Service and Route, vm-app repository, vm-tools (rank.py, deadlines.py).
- [live] 1: The workloads start (pods run sleep) and the Route admits; port 8080 is a stand-in.
- [live] 3: Trivy --ignorefile YAML with expired_at; docker.io/library/nginx:1.28-alpine and httpd:2.4.38 availability.
- [live] 2: Gitea branch, contents and pull request API calls with GITEA_TOKEN.
- [live] 2: A copy of rank.py and deadlines.py equals the VM-3 reference solution.
- [live] 4: Lab shell reaches the public KEV JSON feed (fields cveID, dueDate, count) and the EPSS API (api.first.org/data/v1/epss, BETA; 50 CVE IDs per call; behavior for an unknown CVE is not documented, the script stores null).

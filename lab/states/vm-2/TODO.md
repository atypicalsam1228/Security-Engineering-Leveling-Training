# TODO: start state for VM-2 (Scan and Hand Off)

+ [done] 1: legacy-web, vm-app repository, vm-tools ConfigMap.
- [live] 1: Trivy database and docker.io reachable from the lab shell; trivy fs on requirements.txt reports findings; trivy config on a folder; empty-folder JSON shape (the partial test).
- [live] 1: oc extract configmap --confirm; jq and trivy present in the lab shell image.
- [live] 1: Pins in requirements.txt (flask 0.12, pyyaml 5.3, requests 2.19.0, jinja2 2.10, urllib3 1.24.1) produce findings with fixes.
- [live] 2: Gitea reachable from the lab shell, certificate trusted, git clone works with the extra header.
- [live] 1: trivy image with the CycloneDX format writes components for nginx:1.16; trivy sbom reads it with --scanners vuln, --format json, --output; package names in the SBOM equal PkgName in the image report; a truncated SBOM makes trivy sbom exit non-zero (handoff.sh marks it failed either way).

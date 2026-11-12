#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Removes the pipeline runs and the my-check config map GRC-2 makes. The learner creates no other objects;
# files such as facts.json live in the lab shell, not the cluster.
set -euo pipefail
oc delete pipelinerun -n build -l tekton.dev/pipeline=collect-evidence --ignore-not-found
oc delete configmap my-check -n build --ignore-not-found

#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Puts the supplied files in /workspace/aid-5: the Kyverno permissions and the probe pod in guardrails/,
# and the reference answer for the guardrail the learner writes in answers/. It never touches files the learner wrote.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
REF="$(cd "$(dirname "$0")" && pwd)/ref"
mkdir -p /workspace/aid-5/guardrails /workspace/aid-5/answers
cp "$REF/kyverno-agent-baseline.yaml" /workspace/aid-5/guardrails/kyverno-agent-baseline.yaml
cp "$REF/agent-probe.yaml" /workspace/aid-5/guardrails/agent-probe.yaml
cp "$REF/agent-guardrails-cluster.answer.yaml" /workspace/aid-5/answers/agent-guardrails-cluster.answer.yaml
say "supplied files are in /workspace/aid-5"

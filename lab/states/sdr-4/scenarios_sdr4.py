"""Recorded test scenarios for SDR-4. Each scenario is a few audit records and the result a correct detection gives.

offset_s is seconds after the replay base time. DETECTIONS names the three detections the learner writes.
"""
import json

from evlib import SEC, audit_line

DETECTIONS = ("priv-escalation", "secret-read", "pod-exec")
HUMAN = "lab-tester"
SYSTEM = "system:serviceaccount:openshift-gitops:argocd-application-controller"


def _events(spec):
    """spec: [(offset_s, kwargs for audit_line)] -> [(offset_ns, line)]. Time text in the line is a fixed stamp."""
    return [(off * SEC, audit_line(1_700_000_000 * SEC + off * SEC, **kw)) for off, kw in spec]


def _bind(resource, user, role, verb="create", namespace=""):
    return dict(user=user, verb=verb, resource=resource, namespace=namespace, name="tmp-ops", code=201, role=role, subject=user)


def _secret(user, verb, name):
    return dict(user=user, verb=verb, resource="secrets", namespace="demo", name=name)


SCENARIOS = [
    {"id": "priv-cluster-admin", "detection": "priv-escalation", "expect": "fire",
     "events": _events([(60, _bind("clusterrolebindings", HUMAN, "cluster-admin"))])},
    {"id": "priv-namespace-admin", "detection": "priv-escalation", "expect": "fire",
     "events": _events([(60, _bind("rolebindings", HUMAN, "admin", namespace="demo"))])},
    {"id": "priv-view-only", "detection": "priv-escalation", "expect": "no_fire",
     "events": _events([(60, _bind("rolebindings", HUMAN, "view", namespace="demo"))])},
    {"id": "priv-by-controller", "detection": "priv-escalation", "expect": "no_fire",
     "events": _events([(60, _bind("rolebindings", SYSTEM, "admin", namespace="demo"))])},
    {"id": "priv-read-only", "detection": "priv-escalation", "expect": "no_fire",
     "events": _events([(60, _bind("clusterrolebindings", HUMAN, "cluster-admin", verb="get"))])},
    {"id": "secret-bulk-read", "detection": "secret-read", "expect": "fire",
     "events": _events([(30, _secret(HUMAN, "list", ""))] + [(40 + 20 * i, _secret(HUMAN, "get", "s%d" % i)) for i in range(5)])},
    {"id": "secret-single-read", "detection": "secret-read", "expect": "no_fire",
     "events": _events([(60, _secret("lab-user3", "get", "db-credentials"))])},
    {"id": "secret-controller-reads", "detection": "secret-read", "expect": "no_fire",
     "events": _events([(10 + 10 * i, _secret(SYSTEM, "get", "s%d" % i)) for i in range(20)])},
    {"id": "exec-by-person", "detection": "pod-exec", "expect": "fire",
     "events": _events([(60, dict(user=HUMAN, verb="create", resource="pods", namespace="demo", name="demo-app-1", sub="exec", code=101))])},
    {"id": "logs-by-person", "detection": "pod-exec", "expect": "no_fire",
     "events": _events([(60, dict(user=HUMAN, verb="get", resource="pods", namespace="demo", name="demo-app-1", sub="log"))])},
    {"id": "exec-by-controller", "detection": "pod-exec", "expect": "no_fire",
     "events": _events([(60, dict(user=SYSTEM, verb="create", resource="pods", namespace="demo", name="demo-app-1", sub="exec", code=101))])},
]


def labels_for(scenario):
    return {"log_type": "audit"}


if __name__ == "__main__":
    print(json.dumps([{"id": s["id"], "detection": s["detection"], "events": len(s["events"])} for s in SCENARIOS]))

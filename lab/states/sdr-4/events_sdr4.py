"""Exercise records for SDR-4: one sign-in attack that reaches the cluster, across three sources, plus decoys.

Offsets are minutes before the anchor. Every record is pushed straight to Loki with the label lab_seed.
"""
from evlib import MIN, SEC, add, audit_line, falco_line, keycloak_line, streams

SEED = "sdr-4"
USER = "lab-user9"
IP = "203.0.113.77"
POD = "demo-app-6d9f7c8b5d-x2k4q"
FAILURES = 6
KC = {"log_type": "application", "kubernetes_namespace_name": "keycloak", "kubernetes_container_name": "keycloak"}
FALCO = {"log_type": "application", "kubernetes_namespace_name": "security-tools"}
AUDIT = {"log_type": "audit"}


def timeline_rows(anchor):
    """The key events in order: (ts_ns, source, action) used by the timeline check."""
    rows = [(anchor + (-60 * MIN) + i * 15 * SEC, "keycloak", "LOGIN_ERROR") for i in range(FAILURES)]
    rows.append((anchor - 58 * MIN, "keycloak", "LOGIN"))
    rows.append((anchor - 55 * MIN, "audit", "list secrets"))
    rows.append((anchor - 54 * MIN, "audit", "get secrets"))
    rows.append((anchor - 50 * MIN, "audit", "create pods/exec"))
    rows.append((anchor - 50 * MIN + 6 * SEC, "falco", "Terminal shell in container"))
    rows.append((anchor - 45 * MIN, "audit", "create clusterrolebindings"))
    return rows


def build(anchor):
    b = {}
    for ts, source, action in timeline_rows(anchor):
        if source == "keycloak":
            add(b, dict(KC, lab_seed=SEED), ts, keycloak_line(ts, action, USER, IP))
        elif source == "falco":
            add(b, dict(FALCO, lab_seed=SEED), ts, falco_line(ts, "demo", POD))
        elif action == "list secrets":
            add(b, dict(AUDIT, lab_seed=SEED), ts, audit_line(ts, USER, "list", "secrets", "demo", ""))
        elif action == "get secrets":
            add(b, dict(AUDIT, lab_seed=SEED), ts, audit_line(ts, USER, "get", "secrets", "demo", "db-credentials"))
        elif action == "create pods/exec":
            add(b, dict(AUDIT, lab_seed=SEED), ts, audit_line(ts, USER, "create", "pods", "demo", POD, sub="exec", code=101))
        else:
            add(b, dict(AUDIT, lab_seed=SEED), ts,
                audit_line(ts, USER, "create", "clusterrolebindings", "", "tmp-ops", code=201, role="cluster-admin", subject=USER))
    # decoys that a careless filter would pull in
    t = anchor - 56 * MIN
    add(b, dict(AUDIT, lab_seed=SEED), t, audit_line(t, "lab-user3", "get", "secrets", "demo", "db-credentials"))
    t = anchor - 52 * MIN
    add(b, dict(KC, lab_seed=SEED), t, keycloak_line(t, "LOGIN", "lab-user3", "10.130.0.9"))
    t = anchor - 49 * MIN
    add(b, dict(FALCO, lab_seed=SEED), t, falco_line(t, "demo", "demo-batch-7f9c4d5b6-k2m8n"))
    return streams(b)

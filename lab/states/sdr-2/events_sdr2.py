"""Exercise records for SDR-2: three alert types, one late log type and one gap. Offsets are minutes before the anchor."""
from evlib import MIN, add, audit_line, falco_line, keycloak_line, streams

SEED = "sdr-2"
GAP_FROM, GAP_TO = -80, -55            # no audit record in this span
INFRA_LAST = -23                       # newest infrastructure record is this old (late)
POD_A = "demo-app-6d9f7c8b5d-x2k4q"
POD_D = "demo-batch-7f9c4d5b6-k2m8n"

# alert id -> (type, minutes before the anchor the alert was raised)
ALERTS = {
    "A-101": ("privilege-change", -44),
    "A-102": ("failed-signin-burst", -33),
    "A-103": ("shell-in-pod", -29),
    "A-104": ("shell-in-pod", -69),
}


def build(anchor):
    b = {}
    audit = {"log_type": "audit", "lab_seed": SEED}
    app_demo = {"log_type": "application", "kubernetes_namespace_name": "demo", "lab_seed": SEED}
    infra = {"log_type": "infrastructure", "lab_seed": SEED}
    kc = {"log_type": "application", "kubernetes_namespace_name": "keycloak", "lab_seed": SEED}
    falco = {"log_type": "application", "kubernetes_namespace_name": "security-tools", "lab_seed": SEED}
    for m in range(-180, 0, 2):
        t = anchor + m * MIN
        if not GAP_FROM <= m <= GAP_TO:
            add(b, audit, t, audit_line(t, "system:serviceaccount:openshift-monitoring:prometheus-k8s", "get", "pods", "demo", "demo-app"))
        add(b, app_demo, t, '{"level":"info","msg":"request served","path":"/health"}')
        if m <= INFRA_LAST:
            add(b, infra, t, "kubelet: syncLoop (PLEG): event for pod")
    # A-101: role binding created by an approved actor
    t = anchor - 45 * MIN
    add(b, audit, t, audit_line(t, "lab-admin1", "create", "rolebindings", "demo", "ops-view-temp", code=201, role="view", subject="lab-analyst"))
    # A-102: seven failures then a success from one source, three failures from another
    for i in range(7):
        t = anchor + int((-36 + i * 0.5) * MIN)
        add(b, kc, t, keycloak_line(t, "LOGIN_ERROR", "lab-user7", "203.0.113.50"))
    t = anchor - 32 * MIN
    add(b, kc, t, keycloak_line(t, "LOGIN", "lab-user7", "203.0.113.50"))
    for i in range(3):
        t = anchor + int((-50 + i * 0.5) * MIN)
        add(b, kc, t, keycloak_line(t, "LOGIN_ERROR", "lab-user3", "198.51.100.7"))
    for m, who in ((-100, "lab-user1"), (-75, "lab-user2"), (-20, "lab-user4")):
        t = anchor + m * MIN
        add(b, kc, t, keycloak_line(t, "LOGIN", who, "10.130.0.9"))
    # A-103: shell in a pod, attributed by an audit exec record from an approved actor
    t = anchor + int(-30.2 * MIN)
    add(b, audit, t, audit_line(t, "lab-oncall", "create", "pods", "demo", POD_A, sub="exec", code=101))
    t = anchor - 30 * MIN
    add(b, falco, t, falco_line(t, "demo", POD_A))
    # A-104: shell in a pod while the audit stream had a gap, so no audit record exists
    t = anchor - 70 * MIN
    add(b, falco, t, falco_line(t, "demo", POD_D))
    return streams(b)

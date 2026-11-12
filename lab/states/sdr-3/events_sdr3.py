"""Exercise records for SDR-3: steady noise from a monitoring client plus one low-to-medium incident.

Offsets are minutes before the anchor. The same builder feeds the lab seed and the review gate, so the
gate computes its expected answers from the records instead of keeping a second copy.
"""
from evlib import MIN, SEC, add, audit_line, keycloak_line, streams

SEED = "sdr-3"
ATTACKER_IP = "203.0.113.50"
MONITOR_IP = "10.130.2.15"
# Loki serves records older than about 3 hours only after it has flushed them (about 30 minutes after the push), so every
# record sits within 2 hours of the anchor and is searchable the moment lab start ends.
NOISE_START, NOISE_BLOCKS = -120, 24          # 24 blocks of 5 minutes, 4 failures in each
RECON = {"user": "lab-admin1", "start": -90, "count": 5, "gap_s": 30}
MAIN = {"user": "lab-user7", "start": -45, "count": 12, "gap_s": 15}
SUCCESS_AFTER_S = 225                         # the sign-in that works, after the main burst
SECRET_NAMES = ("db-credentials", "api-token", "tls-key", "registry-pull")
KC_LABELS = {"log_type": "application", "kubernetes_namespace_name": "keycloak", "kubernetes_container_name": "keycloak"}
WINDOW_S = 300                                 # the rule counts failures over 5 minutes


def _burst_times(burst):
    return [burst["start"] * MIN + i * burst["gap_s"] * SEC for i in range(burst["count"])]


def keycloak_events():
    """[(offset_ns, line_kind, user, ip, client)] for every Keycloak record, before text rendering."""
    rows = []
    for block in range(NOISE_BLOCKS):
        for k in range(4):
            rows.append((NOISE_START * MIN + block * 5 * MIN + k * 75 * SEC + 30 * SEC, "LOGIN_ERROR", "svc-monitor", MONITOR_IP, "lab-monitor"))
    for burst in (RECON, MAIN):
        rows += [(t, "LOGIN_ERROR", burst["user"], ATTACKER_IP, "lab-console") for t in _burst_times(burst)]
    rows.append((MAIN["start"] * MIN + SUCCESS_AFTER_S * SEC, "LOGIN", MAIN["user"], ATTACKER_IP, "lab-console"))
    for m, who in ((-115, "lab-user1"), (-70, "lab-user2"), (-20, "lab-user4")):
        rows.append((m * MIN, "LOGIN", who, "10.130.0.9", "lab-console"))
    return rows


def audit_events():
    rows = []
    t0 = MAIN["start"] * MIN + SUCCESS_AFTER_S * SEC
    rows.append((t0 + 60 * SEC, "lab-user7", "list", "secrets", "demo", ""))
    for i, name in enumerate(SECRET_NAMES):
        rows.append((t0 + 90 * SEC + i * 30 * SEC, "lab-user7", "get", "secrets", "demo", name))
    rows.append((-100 * MIN, "lab-user3", "get", "secrets", "demo", "db-credentials"))
    rows.append((-110 * MIN, "lab-admin1", "get", "secrets", "demo", "tls-key"))
    for m in range(-120, 0, 5):
        rows.append((m * MIN, "system:serviceaccount:openshift-monitoring:prometheus-k8s", "get", "pods", "demo", "demo-app"))
    return rows


def build(anchor):
    bucket = {}
    for off, kind, user, ip, client in keycloak_events():
        add(bucket, dict(KC_LABELS, lab_seed=SEED), anchor + off, keycloak_line(anchor + off, kind, user, ip, client))
    for off, user, verb, resource, namespace, name in audit_events():
        add(bucket, {"log_type": "audit", "lab_seed": SEED}, anchor + off,
            audit_line(anchor + off, user, verb, resource, namespace, name))
    return streams(bucket)


def replay_events():
    """Keycloak records only: [(offset_ns, text line)] for the review gate's replay."""
    return [(off, keycloak_line(1_700_000_000 * SEC + off, kind, user, ip, client)) for off, kind, user, ip, client in keycloak_events()]


def real_windows_s():
    """Spans, in seconds relative to the anchor, during which a firing rule is correct."""
    out = []
    for burst in (RECON, MAIN):
        times = _burst_times(burst)
        out.append((times[0] // SEC, times[-1] // SEC + WINDOW_S))
    return out


def truth():
    """What a correct findings.json holds. first_success_offset_s is relative to the anchor."""
    return {
        "account": MAIN["user"],
        "source_ip": ATTACKER_IP,
        "failed_attempts": MAIN["count"],
        "first_success_offset_s": (MAIN["start"] * MIN + SUCCESS_AFTER_S * SEC) // SEC,
        "secrets_read": len(SECRET_NAMES),
        "other_account_targeted": RECON["user"],
    }

"""Supplied triage commands for SDR-2. Usage:
  python3 triage.py privilege A-101    python3 triage.py signin A-102    python3 triage.py shell A-103
  python3 triage.py path               python3 triage.py gaps               python3 triage.py alerts
Each command prints the search it runs, the evidence, and CHECK lines. You decide; nothing is closed for you.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import lokilib as loki
from lokilib import MIN, NS

HERE = Path(__file__).resolve().parent
# Every record of the current seeding carries seed_run=<anchor>; pinning to it ignores copies from an earlier lab start.
SELECT = 'lab_seed="sdr-2", seed_run="%s"' % (HERE / "anchor.txt").read_text().strip()
STALE_MIN = 5      # a log type with no record for longer than this is late (lab value)
GAP_MIN = 10       # a quiet span longer than this is a gap (lab value)
ALERTS = {"A-101": ("privilege-change", -44), "A-102": ("failed-signin-burst", -33),
          "A-103": ("shell-in-pod", -29), "A-104": ("shell-in-pod", -69)}


TEXTS = {"A-101": "namespace=demo a role binding was created",
         "A-102": "namespace=keycloak sign-in failures above the limit",
         "A-103": "namespace=demo pod demo-app shell opened",
         "A-104": "namespace=demo pod demo-batch shell opened"}


def anchor():
    return int((HERE / "anchor.txt").read_text().strip()) * NS


def stamp(ts_ns):
    return time.strftime("%H:%M:%S", time.gmtime(ts_ns // NS)) + "Z"


def search(query, start, end):
    print("SEARCH  %s" % query)
    return loki.entries(query, start, end)


def window(alert_id, before, after):
    if alert_id not in ALERTS:
        sys.exit("Unknown alert id %s. Known: %s" % (alert_id, ", ".join(sorted(ALERTS))))
    kind, offset = ALERTS[alert_id]
    when = anchor() + offset * MIN
    print("ALERT   %s  type %s  raised %s" % (alert_id, kind, stamp(when)))
    return when - before * MIN, when + after * MIN


def check(label, ok):
    print("CHECK   %-58s %s" % (label, "yes" if ok else "NO"))
    return ok


def approved():
    return json.loads((HERE / "approved.json").read_text())


def privilege(alert_id):
    start, end = window(alert_id, 15, 10)
    rows = search('{log_type="audit", %s} |= "rolebindings"' % SELECT, start, end)
    hits = []
    for ts, _, line in rows:
        rec = json.loads(line)
        if rec["verb"] != "create":
            continue
        body = rec.get("requestObject", {})
        ref = rec["objectRef"]
        hits.append({"actor": rec["user"]["username"], "namespace": ref["namespace"], "name": ref["name"],
                     "role": body.get("roleRef", {}).get("name", "?"),
                     "subject": (body.get("subjects") or [{}])[0].get("name", "?")})
        print("EVENT   %s  %s created %s/%s  role=%s  subject=%s" % (
            stamp(ts), hits[-1]["actor"], ref["namespace"], ref["name"], hits[-1]["role"], hits[-1]["subject"]))
    if not hits:
        print("RESULT  no role binding found in the window. Do not close. Run: python3 triage.py gaps")
        sys.exit(2)
    for hit in hits:
        check("%s/%s matches an approved change (actor, name, role, subject)" % (hit["namespace"], hit["name"]),
              hit in approved()["privilege"])
        check("role is admin-level (admin or cluster-admin)", hit["role"] in ("admin", "cluster-admin"))


def signin(alert_id):
    start, end = window(alert_id, 20, 30)
    rows = search('{log_type="application", kubernetes_namespace_name="keycloak", %s} |~ "LOGIN"' % SELECT, start, end)
    stats = {}
    for ts, _, line in rows:
        fields = dict(part.strip().split("=", 1) for part in line.split(") ", 1)[1].split(", ") if "=" in part)
        key = (fields["username"].strip('"'), fields["ipAddress"].strip('"'))
        row = stats.setdefault(key, {"fail": 0, "last_fail": 0, "success": 0})
        if 'type="LOGIN_ERROR"' in line:
            row["fail"] += 1
            row["last_fail"] = ts
        elif row["last_fail"] and ts > row["last_fail"]:
            row["success"] = ts
    print("%-12s %-16s %-9s %-11s %s" % ("USER", "SOURCE_IP", "FAILURES", "LAST_FAIL", "LATER_SUCCESS"))
    for (user, ip), row in sorted(stats.items(), key=lambda kv: -kv[1]["fail"]):
        if row["fail"]:
            print("%-12s %-16s %-9d %-11s %s" % (user, ip, row["fail"], stamp(row["last_fail"]),
                                                  stamp(row["success"]) if row["success"] else "none"))
    check("a source with failures was later followed by a success", any(r["success"] for r in stats.values()))


def shell(alert_id):
    start, end = window(alert_id, 5, 5)
    falco = search('{log_type="application", kubernetes_namespace_name="security-tools", %s} |= "Terminal shell"' % SELECT, start, end)
    if not falco:
        sys.exit("No runtime-detector record in the window. Do not close. Run: python3 triage.py path")
    for ts, _, line in falco:
        fields = json.loads(line)["output_fields"]
        print("EVENT   %s  shell in %s/%s as %s" % (stamp(ts), fields["k8s.ns.name"], fields["k8s.pod.name"], fields["user.name"]))
    pod, ns = fields["k8s.pod.name"], fields["k8s.ns.name"]
    audit = search('{log_type="audit", %s} |= "%s" |= "exec"' % (SELECT, pod), start, end)
    check("an API audit record names who opened the shell", bool(audit))
    if not audit:
        print("RESULT  no audit record. The person cannot be named. Run: python3 triage.py gaps")
        sys.exit(2)
    actor = json.loads(audit[0][2])["user"]["username"]
    print("EVENT   %s  %s ran exec on %s" % (stamp(audit[0][0]), actor, pod))
    check("actor is on the approved shell list for %s" % ns, {"actor": actor, "namespace": ns} in approved()["shell"])


def newest(log_type):
    # The exercise records are fixed in time, so their age is measured from the moment the exercise
    # started (the anchor), not from the wall clock. Otherwise every log type would turn LATE a few
    # minutes after lab start.
    now = anchor()
    rows = loki.entries('{log_type="%s", %s}' % (log_type, SELECT), anchor() - 200 * MIN, now, limit=5000)
    return (now - rows[-1][0]) // MIN if rows else None


def path():
    bad = 0
    pods = subprocess.run(["oc", "get", "pods", "-n", "openshift-logging", "-l", "app.kubernetes.io/component=collector", "-o", "json"],
                          capture_output=True, text=True)
    items = json.loads(pods.stdout or '{"items":[]}')["items"] if pods.returncode == 0 else []
    running = sum(1 for p in items if p["status"]["phase"] == "Running")
    print("HOP 1 collector  %d of %d pods Running" % (running, len(items)))
    bad += running == 0 or running < len(items)
    ready = loki.ready()
    print("HOP 2 Loki       %s" % ("ready" if ready else "NOT READY"))
    bad += not ready
    for kind in ("audit", "infrastructure", "application"):
        age = newest(kind)
        late = age is None or age > STALE_MIN
        print("HOP 3 %-14s newest record %s minutes old  %s" % (kind, age, "LATE" if late else "ok"))
        bad += late
    hops = (("Grafana", os.environ["GRAFANA_URL"].rstrip("/") + "/api/health"),
            ("Mattermost", os.environ["MM_URL"].rstrip("/") + "/api/v4/system/ping"))
    for name, url in hops:
        out = subprocess.run(["curl", "-s", "-m", "10", url], capture_output=True, text=True).stdout
        good = '"ok"' in out or "OK" in out
        print("HOP 4 %-10s %s" % (name, "answers" if good else "NO ANSWER"))
        bad += not good
    print("SUMMARY %d hop(s) need attention" % bad)


def gaps():
    now = int(time.time() * NS)
    for kind in ("audit", "infrastructure", "application"):
        times = [r[0] for r in loki.entries('{log_type="%s", %s}' % (kind, SELECT), anchor() - 190 * MIN, now, limit=5000)]
        found = [(a, b) for a, b in zip(times, times[1:]) if b - a > GAP_MIN * MIN]
        for a, b in found:
            print("GAP     %-14s %s to %s  (%d minutes with no record)" % (kind, stamp(a), stamp(b), (b - a) // MIN))
        if not found:
            print("ok      %-14s no span longer than %d minutes" % (kind, GAP_MIN))


def alerts():
    """Print the four alerts that lab start posted to the alert channel, so no web login is needed."""
    for alert_id, (kind, offset) in sorted(ALERTS.items()):
        when = anchor() + offset * MIN
        print("ALERT   %s  %-20s raised %s  %s" % (alert_id, kind, stamp(when), TEXTS[alert_id]))


COMMANDS = {"alerts": alerts, "privilege": privilege, "signin": signin, "shell": shell, "path": path, "gaps": gaps}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](*sys.argv[2:])

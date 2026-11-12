"""Review gate for SDR-3. Run: python3 review_gate.py   (from the folder that holds your findings.json)

It fails (exit code 1) unless:
  1. findings.json states the facts of the incident correctly,
  2. the alert rule failed-login-burst fires on every real burst when the recorded events are replayed,
  3. it does not fire on the steady noise, and
  4. the dashboard panel shows the same threshold as the rule.
"""
import base64
import calendar
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import events_sdr3 as ev
import lokilib as loki
import replay

HERE = Path(__file__).resolve().parent
RULE_TITLE = "failed-login-burst"
DASHBOARD_UID = "sdr-auth-overview"
TIME_TOLERANCE_S = 30
FINDING_KEYS = ("account", "source_ip", "failed_attempts", "first_success_utc", "secrets_read", "other_account_targeted")
results = []


def report(label, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", label, ("  (" + detail + ")") if detail else ""))
    return ok


def grafana(path):
    pair = "%s:%s" % (os.environ["GRAFANA_USER"], os.environ["GRAFANA_PASSWORD"])
    req = urllib.request.Request(os.environ["GRAFANA_URL"].rstrip("/") + path,
                                 headers={"Authorization": "Basic " + base64.b64encode(pair.encode()).decode()})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def parse_utc(text):
    return calendar.timegm(time.strptime(text[:19], "%Y-%m-%dT%H:%M:%S"))


def check_findings(anchor_s):
    try:
        found = json.loads(Path("findings.json").read_text())
    except (OSError, ValueError) as err:
        return report("findings.json can be read", False, str(err))
    truth = ev.truth()
    missing = [k for k in FINDING_KEYS if k not in found]
    if not report("findings.json has all six keys", not missing, "missing: %s" % ", ".join(missing) if missing else ""):
        return False
    for key in ("account", "source_ip", "failed_attempts", "secrets_read", "other_account_targeted"):
        report("finding %s" % key, found[key] == truth[key], "you wrote %r" % (found[key],))
    try:
        gap = abs(parse_utc(str(found["first_success_utc"])) - (anchor_s + truth["first_success_offset_s"]))
    except ValueError:
        gap = None
    report("finding first_success_utc within %d seconds" % TIME_TOLERANCE_S, gap is not None and gap <= TIME_TOLERANCE_S,
           "off by %s s" % gap if gap is not None else "not an ISO time such as 2026-10-29T14:03:11Z")
    return True


def check_rule():
    rules = [r for r in grafana("/api/v1/provisioning/alert-rules") if r["title"] == RULE_TITLE]
    if not report("rule %s exists" % RULE_TITLE, bool(rules)):
        return None
    cond = rules[0]["data"][1]["model"]["conditions"][0]["evaluator"]
    return rules[0]["data"][0]["model"]["expr"], cond["type"], cond["params"][0]


def check_replay(expr, op, threshold):
    run = replay.new_run()
    base = int(time.time() * loki.NS) - 15 * loki.MIN
    replay.push(ev.replay_events(), base, run, ev.KC_LABELS)
    time.sleep(3)
    start, end = base + (ev.NOISE_START - 5) * loki.MIN, base + 10 * loki.MIN
    steps = replay.evaluate(expr, op, threshold, run, start, end)
    base_s = base // loki.NS
    windows = [(base_s + a, base_s + b) for a, b in ev.real_windows_s()]
    inside = lambda t: any(a <= t <= b for a, b in windows)
    noise = sum(1 for t, fired in steps.items() if fired and not inside(t))
    report("noise: evaluations that fire outside the real bursts is 0", noise == 0, "%d minutes fired" % noise)
    for number, (a, b) in enumerate(windows, start=1):
        hit = any(fired for t, fired in steps.items() if a <= t <= b)
        report("real burst %d of %d is detected" % (number, len(windows)), hit)


def check_panel(threshold):
    try:
        steps = grafana("/api/dashboards/uid/" + DASHBOARD_UID)["dashboard"]["panels"][0]["fieldConfig"]["defaults"]["thresholds"]["steps"]
    except (KeyError, IndexError, OSError) as err:
        return report("dashboard panel has threshold steps", False, repr(err))
    report("panel threshold matches the rule", steps[-1].get("value") == threshold, "panel %s, rule %s" % (steps[-1].get("value"), threshold))


def main():
    anchor_s = int((HERE / "anchor.txt").read_text().strip())
    check_findings(anchor_s)
    rule = check_rule()
    if rule:
        print("      rule fires when the count is %s %s" % (rule[1], rule[2]))
        check_replay(*rule)
        check_panel(rule[2])
    print("GATE " + ("PASSED" if all(results) else "FAILED"))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

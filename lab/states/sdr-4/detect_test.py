"""Test your detections against the recorded scenarios. Run: python3 detect_test.py [detections-folder]

Each detection file holds comment lines and one LogQL metric expression, for example:
  # op gt
  # threshold 3
  sum(count_over_time({log_type="audit", audit_resource="secrets"} | json | verb="get" [5m]))
The scenarios are pushed through the Alloy intake (so your labeling stage runs on them), then Loki evaluates
your expression every minute. A scenario passes when the detection fires exactly when the scenario says it should.
Give a detection name (for example secret-read) after the folder to run only that detection.
Set PUSH_URL if the intake is not on http://127.0.0.1:3500 (use: oc port-forward -n siem svc/alloy-detect 3500:3500).
"""
import os
import sys
import time
from pathlib import Path

import lokilib as loki
import replay
from scenarios_sdr4 import DETECTIONS, SCENARIOS, labels_for

PUSH_URL = os.environ.get("PUSH_URL", "http://127.0.0.1:3500/loki/api/v1/push")
WAIT_S = 20


def load(path):
    op, threshold, expr = "gt", 0.0, ""
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if line.startswith("# op "):
            op = line[5:].strip()
        elif line.startswith("# threshold "):
            threshold = float(line[12:])
        elif line and not line.startswith("#"):
            expr = line
    if not expr:
        raise ValueError("%s has no expression line" % path)
    return op, threshold, expr


def settle(run, want):
    """Wait until Loki holds every pushed record of this run."""
    now = int(time.time() * loki.NS)
    for _ in range(WAIT_S):
        if len(loki.entries('{lab_replay="%s"}' % run, now - 60 * loki.MIN, now + loki.MIN)) >= want:
            return True
        time.sleep(1)
    return False


def run_scenario(scenario, op, threshold, expr):
    run = replay.new_run()
    base = int(time.time() * loki.NS) - 15 * loki.MIN
    replay.push(scenario["events"], base, run, labels_for(scenario), url=PUSH_URL, auth=False)
    arrived = settle(run, len(scenario["events"]))
    series = loki.matrix(replay.inject(expr, run), base - loki.MIN, base + 12 * loki.MIN, 60)
    peak = max(series.values(), default=0.0)
    fired = any(replay.compare(op, v, threshold) for v in series.values())
    return fired, peak, arrived


def main(folder, only=None):
    failures = 0
    for name in (n for n in DETECTIONS if only in (None, n)):
        path = Path(folder) / (name + ".logql")
        if not path.is_file():
            print("FAIL  %s: file %s not found" % (name, path))
            failures += 1
            continue
        op, threshold, expr = load(path)
        print("%s  fires when the count is %s %s" % (name, op, threshold))
        for scenario in (s for s in SCENARIOS if s["detection"] == name):
            fired, peak, arrived = run_scenario(scenario, op, threshold, expr)
            ok = fired == (scenario["expect"] == "fire")
            failures += not ok
            note = "" if arrived else "  (records did not arrive: check the intake and the Alloy log)"
            print("  %s  %-24s expected %-8s peak count %-4g%s" % ("PASS" if ok else "FAIL", scenario["id"], scenario["expect"], peak, note))
    print("TESTS " + ("PASSED" if not failures else "FAILED (%d)" % failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "detections", sys.argv[2] if len(sys.argv) > 2 else None))

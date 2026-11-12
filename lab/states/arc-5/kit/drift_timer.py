#!/usr/bin/env python3
"""Usage: drift_timer.py FLOWS KIND   (KIND is policy, admission or component)

Measures how fast the conformance test notices one kind of drift. It runs conformance.py to confirm a clean start,
causes the drift, then runs conformance.py every INTERVAL seconds until it fails, and finally undoes the drift.
Prints one JSON line. Changes only the arc-ref project and the arc-ref-flows policy.
"""
import json
import os
import subprocess
import sys
import time

INTERVAL = 10
GIVE_UP = 180
HOME = os.path.expanduser("~/arc")
IMAGE = "registry.access.redhat.com/ubi9/ubi-minimal:9.5"
CAUSE = {
    "policy": ["oc", "delete", "networkpolicy", "default-deny-ingress", "-n", "arc-ref"],
    "admission": ["oc", "delete", "clusterpolicy", "arc-ref-flows"],
    "component": ["oc", "create", "deployment", "intruder", "-n", "arc-ref", "--image=" + IMAGE, "--", "sleep", "infinity"],
}
UNDO = {
    "policy": ["oc", "apply", "-f", HOME + "/generated/networkpolicies.yaml"],
    "admission": ["oc", "apply", "-f", HOME + "/generated/admission.yaml"],
    "component": ["oc", "delete", "deployment", "intruder", "-n", "arc-ref"],
}


def conformance(flows):
    start = time.perf_counter()
    done = subprocess.run(["python3", HOME + "/conformance.py", flows], capture_output=True, text=True)
    return done.returncode, time.perf_counter() - start


def main():
    flows, kind = sys.argv[1], sys.argv[2]
    if conformance(flows)[0] != 0:
        print(json.dumps({"kind": kind, "error": "the clean start already fails conformance; fix that first"}))
        return 2
    subprocess.run(CAUSE[kind], capture_output=True, text=True, check=True)
    caused = time.perf_counter()
    detected, run_seconds = None, 0.0
    while time.perf_counter() - caused < GIVE_UP:
        code, run_seconds = conformance(flows)
        if code != 0:
            detected = time.perf_counter() - caused
            break
        time.sleep(INTERVAL)
    subprocess.run(UNDO[kind], capture_output=True, text=True)
    time.sleep(INTERVAL)
    print(json.dumps({
        "kind": kind,
        "interval_s": INTERVAL,
        "detected_after_s": None if detected is None else round(detected, 1),
        "worst_case_s": round(INTERVAL + run_seconds, 1),
        "recovered": conformance(flows)[0] == 0,
    }))
    return 0 if detected is not None else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Usage: snapshot.py MODE. Adds records and memory numbers to results/MODE.json (written by measure.py).

Creates 20 rule-breaking pods (load.yaml), waits, counts what the cluster recorded, reads Kyverno memory,
then removes the load. It changes only the arc-measure namespace.
"""
import json
import os
import subprocess
import sys
import time

NS = "arc-measure"
HERE = os.path.dirname(os.path.abspath(__file__))
SETTLE_SECONDS = 60
UNITS = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024}


def oc(args):
    done = subprocess.run(["oc", *args], capture_output=True, text=True, timeout=120)
    return done.returncode, done.stdout


def oc_items(args):
    code, out = oc(args + ["-o", "json"])
    return json.loads(out)["items"] if code == 0 and out.strip() else []


def count_fail_results(reports, pod_names):
    """Failed results that belong to pods that exist now. Reports for deleted pods are ignored."""
    total = 0
    for report in reports:
        # Kyverno 1.19 puts the pod in report.scope; older versions list it in each result's resources.
        scope_name = (report.get("scope") or {}).get("name")
        for result in report.get("results") or []:
            names = {r.get("name") for r in result.get("resources") or []}
            if scope_name:
                names.add(scope_name)
            if result.get("result") == "fail" and names & pod_names:
                total += 1
    return total


def memory_mib(top_text):
    """Sum memory per Kyverno component. The pod name minus its two random suffixes is the component."""
    out = {}
    for line in top_text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[2][-2:] not in UNITS:
            continue
        component = "-".join(parts[0].split("-")[:-2])
        out[component] = round(out.get(component, 0) + float(parts[2][:-2]) * UNITS[parts[2][-2:]], 1)
    return out


def count_events(events):
    policy = failed = 0
    for event in events:
        in_scope = event.get("metadata", {}).get("namespace") == NS or NS in event.get("message", "")
        if in_scope and "PolicyViolation" in event.get("reason", ""):
            policy += 1
        if in_scope and event.get("reason") == "FailedCreate":
            failed += 1
    return policy, failed


def main():
    mode = sys.argv[1]
    path = os.path.join(os.path.expanduser("~/arc/results"), mode + ".json")
    with open(path) as handle:
        result = json.load(handle)
    code, _ = oc(["apply", "-f", os.path.join(HERE, "load.yaml")])
    result["load_created"] = code == 0
    print("waiting %d seconds for pods, reports and metrics ..." % SETTLE_SECONDS, file=sys.stderr)
    time.sleep(SETTLE_SECONDS)
    pods = oc_items(["get", "pods", "-n", NS, "-l", "arc-role=load"])
    names = {p["metadata"]["name"] for p in pods}
    reports = oc_items(["get", "policyreport", "-n", NS])
    policy_events, failed_events = count_events(oc_items(["get", "events", "-A"]))
    memory = memory_mib(oc(["adm", "top", "pods", "-n", "kyverno", "--no-headers"])[1])
    result.update({
        "load_pods_created": len(names),
        "report_objects": len(reports),
        "report_fail_results": count_fail_results(reports, names),
        "policy_events": policy_events,
        "failed_create_events": failed_events,
        "memory_mib": memory,
        "memory_total_mib": round(sum(memory.values()), 1),
    })
    oc(["delete", "deployment", "load", "-n", NS, "--ignore-not-found"])
    with open(path, "w") as handle:
        json.dump(result, handle, indent=2)
    print("snapshot saved to %s" % path)


if __name__ == "__main__":
    main()

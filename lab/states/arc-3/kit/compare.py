#!/usr/bin/env python3
"""Usage: compare.py [RESULTS_DIR]. Prints none, audit and enforce side by side. Exit 2 if a result is missing or too small."""
import json
import os
import sys

MODES = ["none", "audit", "enforce"]
MIN_SAMPLES = 20
ROWS = [
    ("samples used", lambda r: r["n"]),
    ("median admit ms", lambda r: r["median_ms"]),
    ("p95 admit ms", lambda r: r["p95_ms"]),
    ("case ok", lambda r: r["outcomes"]["ok"]),
    ("case root", lambda r: r["outcomes"]["root"]),
    ("case latest", lambda r: r["outcomes"]["latest"]),
    ("case nolimits", lambda r: r["outcomes"]["nolimits"]),
    ("load pods created", lambda r: r["load_pods_created"]),
    ("report objects", lambda r: r["report_objects"]),
    ("report fail results", lambda r: r["report_fail_results"]),
    ("policy events", lambda r: r["policy_events"]),
    ("failed-create events", lambda r: r["failed_create_events"]),
    ("kyverno memory MiB", lambda r: r["memory_total_mib"]),
]


def load(directory):
    results = {}
    for mode in MODES:
        path = os.path.join(directory, mode + ".json")
        if not os.path.isfile(path):
            raise SystemExit("missing %s: run all three conditions before comparing" % path)
        with open(path) as handle:
            results[mode] = json.load(handle)
        if results[mode].get("n", 0) < MIN_SAMPLES - 1 or "memory_total_mib" not in results[mode]:
            raise SystemExit("%s is incomplete: need at least %d timing samples and the snapshot step" % (path, MIN_SAMPLES - 1))
    return results


def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/arc/results")
    try:
        results = load(directory)
    except SystemExit as err:
        print("STOP: %s" % err, file=sys.stderr)
        return 2
    print("%-22s %12s %12s %12s" % ("measure", *MODES))
    for label, pick in ROWS:
        print("%-22s %12s %12s %12s" % (label, *(pick(results[m]) for m in MODES)))
    base = results["none"]["median_ms"]
    for mode in ("audit", "enforce"):
        print("delay added by %s: %.1f ms over none" % (mode, results[mode]["median_ms"] - base))
    return 0


if __name__ == "__main__":
    sys.exit(main())

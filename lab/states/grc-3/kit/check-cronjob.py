"""Checks a CronJob file against the GRC-3 spec. Usage: check-cronjob.py FILE
Prints one line per property and exits 1 if any property fails. It reads the file only; it never contacts the cluster."""
import re
import sys

import yaml

SERVICE_ACCOUNT = "evidence-runner"
EVIDENCE_DIR = "/evidence"


def find(items, name):
    return next((i for i in items or [] if isinstance(i, dict) and i.get("name") == name), {})


def problems(doc):
    pod = doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    box = find(pod.get("containers"), "collect")
    env = {e.get("name"): e.get("value") for e in box.get("env") or [] if isinstance(e, dict)}
    args = box.get("args") or []
    line = args[0] if args and isinstance(args[0], str) else ""
    mount = find(box.get("volumeMounts"), "evidence").get("mountPath")
    checks = [
        ("service account", pod.get("serviceAccountName") == SERVICE_ACCOUNT, "serviceAccountName must be " + SERVICE_ACCOUNT),
        ("evidence folder", env.get("EVIDENCE_DIR") == EVIDENCE_DIR, "env EVIDENCE_DIR must be " + EVIDENCE_DIR),
        ("path holds oc", str(env.get("PATH") or "").startswith("/oc-bin:"), "env PATH must start with /oc-bin:"),
        ("volume mount", mount == EVIDENCE_DIR, "the evidence volume must be mounted at " + EVIDENCE_DIR),
        ("fetch from main", "raw/branch/main/collect_evidence.py" in line, "args must fetch .../raw/branch/main/collect_evidence.py"),
        ("address from variables", "$GITEA_URL" in line and "$GITEA_USER" in line, "args must use $GITEA_URL and $GITEA_USER, not a typed address"),
        ("stop on bad download", bool(re.search(r"curl\s+-\w*f", line)) and "&&" in line, "args must use curl -f and join the run with &&"),
        ("runs the collector", "python3" in line, "args must run the file with python3"),
    ]
    return [(name, ok, why) for name, ok, why in checks]


def main(path):
    try:
        doc = yaml.safe_load(open(path))
        results = problems(doc)
    except (OSError, yaml.YAMLError, KeyError, TypeError, AttributeError) as error:
        print("FAIL file: cannot read the CronJob (" + type(error).__name__ + "): " + str(error).splitlines()[0])
        return 1
    for name, ok, why in results:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else ": " + why))
    return 0 if all(ok for _, ok, _ in results) else 1


sys.exit(main(sys.argv[1]))

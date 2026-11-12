import json
import time

from ailog import push


def audit(kind, **fields):
    line = json.dumps({"kind": kind, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **fields})
    print("AUDIT", line)
    try:
        push({"app": "triage-agent", "kind": kind}, line)
    except OSError as exc:
        raise RuntimeError("audit log unavailable, stopping: " + str(exc)) from exc

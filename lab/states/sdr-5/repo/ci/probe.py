import json
import time

import gf
import lokilib as loki

UID = "det-pod-exec"


def exec_line(ts_ns):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts_ns // loki.NS)) + ".000000Z"
    ref = {"resource": "pods", "namespace": "demo", "name": "demo-app-1", "subresource": "exec"}
    return json.dumps({"kind": "Event", "verb": "create", "user": {"username": "lab-tester"},
                       "objectRef": ref, "stageTimestamp": stamp})


def evaluation_interval_s():
    status, rule = gf.call("GET", "/api/v1/provisioning/alert-rules/" + UID)
    if status != 200:
        raise SystemExit("FAIL  Grafana has no rule %s (status %s)" % (UID, status))
    url = "/api/v1/provisioning/folder/%s/rule-groups/%s" % (rule["folderUID"], rule["ruleGroup"])
    status, group = gf.call("GET", url)
    if status != 200:
        raise SystemExit("FAIL  cannot read the rule group (status %s)" % status)
    return group["interval"]

"""Builders for exercise log records in the shapes the lab collector produces. Standard library only."""
import json
from datetime import datetime, timezone

MIN = 60 * 10**9
SEC = 10**9
KEYCLOAK_NS = "keycloak"


def iso(ts_ns):
    sec, rem = divmod(int(ts_ns), SEC)
    return datetime.fromtimestamp(sec, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".%06dZ" % (rem // 1000)


def audit_line(ts_ns, user, verb, resource, namespace="", name="", sub="", code=200,
               role=None, subject=None, source_ip="10.128.0.12"):
    uri = "/api/v1/namespaces/%s/%s/%s" % (namespace, resource, name) if namespace else "/apis/x/%s/%s" % (resource, name)
    if sub:
        uri += "/" + sub
    rec = {
        "kind": "Event", "apiVersion": "audit.k8s.io/v1", "stage": "ResponseComplete",
        "verb": verb, "requestURI": uri,
        "user": {"username": user}, "sourceIPs": [source_ip],
        "objectRef": {"resource": resource, "namespace": namespace, "name": name},
        "responseStatus": {"code": code},
        "requestReceivedTimestamp": iso(ts_ns), "stageTimestamp": iso(ts_ns),
    }
    if sub:
        rec["objectRef"]["subresource"] = sub
    if role:
        rec["requestObject"] = {"roleRef": {"kind": "ClusterRole", "name": role},
                                "subjects": [{"kind": "User", "name": subject or ""}]}
    return json.dumps(rec, separators=(",", ":"))


def keycloak_line(ts_ns, event, user, ip, client="lab-console"):
    stamp = iso(ts_ns)[:23].replace("T", " ").replace(".", ",")
    if event == "LOGIN_ERROR":
        return ('%s WARN  [org.keycloak.events] (executor-thread-1) type="LOGIN_ERROR", realmId="lab", '
                'clientId="%s", userId="null", ipAddress="%s", error="invalid_user_credentials", '
                'auth_method="openid-connect", username="%s"' % (stamp, client, ip, user))
    return ('%s INFO  [org.keycloak.events] (executor-thread-1) type="%s", realmId="lab", '
            'clientId="%s", userId="%s", ipAddress="%s", auth_method="openid-connect", username="%s"'
            % (stamp, event, client, "u-" + user, ip, user))


def falco_line(ts_ns, namespace, pod, user="root"):
    out = ("A shell was spawned in a container with an attached terminal (user=%s k8s.ns=%s k8s.pod=%s shell=sh)"
           % (user, namespace, pod))
    return json.dumps({"rule": "Terminal shell in container", "priority": "Notice", "time": iso(ts_ns),
                       "output": out,
                       "output_fields": {"k8s.ns.name": namespace, "k8s.pod.name": pod,
                                         "user.name": user, "proc.cmdline": "sh"}}, separators=(",", ":"))


def add(bucket, labels, ts_ns, line):
    """Append one record to the stream with these labels (bucket maps label-set to a list)."""
    key = json.dumps(labels, sort_keys=True)
    bucket.setdefault(key, (labels, []))[1].append((int(ts_ns), line))


def streams(bucket):
    return [(labels, sorted(values)) for labels, values in bucket.values()]

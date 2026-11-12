"""Grafana helper for the detections pipeline. Reads GRAFANA_URL, GRAFANA_USER, GRAFANA_PASSWORD. Standard library only."""
import base64
import json
import os
import urllib.error
import urllib.request

GROUP = "detections-as-code"
FOLDER = "siem-detect"


def call(method, path, body=None):
    """Return (status, parsed JSON or None). Never raises on an HTTP error status."""
    pair = "%s:%s" % (os.environ["GRAFANA_USER"], os.environ["GRAFANA_PASSWORD"])
    headers = {"Authorization": "Basic " + base64.b64encode(pair.encode()).decode(),
               "Content-Type": "application/json", "X-Disable-Provenance": "true"}
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(os.environ["GRAFANA_URL"].rstrip("/") + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as err:
        text = err.read().decode()
        try:
            return err.code, json.loads(text)
        except ValueError:
            return err.code, None


def folder_uid():
    status, folders = call("GET", "/api/folders")
    for folder in folders or []:
        if folder["title"] == FOLDER:
            return folder["uid"]
    status, made = call("POST", "/api/folders", {"title": FOLDER})
    return made["uid"]


def loki_uid():
    status, source = call("GET", "/api/datasources/name/Loki")
    return source["uid"]


def rule_payload(rule):
    """Build the Grafana alert-rule body for one detection file."""
    query = {"refId": "A", "datasourceUid": loki_uid(), "relativeTimeRange": {"from": 600, "to": 0},
             "model": {"refId": "A", "expr": rule["expr"], "queryType": "instant", "instant": True}}
    condition = {"refId": "B", "datasourceUid": "-100", "relativeTimeRange": {"from": 0, "to": 0},
                 "model": {"refId": "B", "type": "classic_conditions", "datasource": {"type": "__expr__", "uid": "-100"},
                           "conditions": [{"type": "query", "query": {"params": ["A"]}, "reducer": {"type": "last", "params": []},
                                           "evaluator": {"type": rule["op"], "params": [rule["threshold"]]}, "operator": {"type": "and"}}]}}
    return {"orgID": 1, "uid": rule["uid"], "title": rule["title"], "ruleGroup": GROUP, "folderUID": folder_uid(),
            "noDataState": "OK", "execErrState": "Error", "for": rule.get("for", "0s"), "condition": "B",
            "labels": {"control": rule["control"], "severity": rule["severity"], "source": "detections-repo"},
            "annotations": {"summary": rule["title"]}, "data": [query, condition]}

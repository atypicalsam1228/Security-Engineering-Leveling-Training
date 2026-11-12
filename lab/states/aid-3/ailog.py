import base64
import json
import os
import ssl
import time
import urllib.parse
import urllib.request


def loki_access():
    login = os.environ["LOKI_USER"] + ":" + os.environ["LOKI_PASSWORD"]
    headers = {"Authorization": "Basic " + base64.b64encode(login.encode("utf-8")).decode("ascii")}
    return headers, ssl.create_default_context(cafile=os.environ["LOKI_CA_FILE"])


def post(url, body, headers=None, context=None):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data, {"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=10, context=context) as response:
        return response.read().decode("utf-8")


def push(labels, line):
    headers, context = loki_access()
    stream = {"stream": labels, "values": [[str(time.time_ns()), line]]}
    post(os.environ["LOKI_URL"] + "/loki/api/v1/push", {"streams": [stream]}, headers, context)


def log_event(kind, request_id, text):
    line = json.dumps({"kind": kind, "request_id": request_id, "text": text})
    push({"app": "ai-summarizer", "kind": kind}, line)


def query(expr):
    headers, context = loki_access()
    url = os.environ["LOKI_URL"] + "/loki/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10, context=context) as response:
        return json.loads(response.read().decode("utf-8"))

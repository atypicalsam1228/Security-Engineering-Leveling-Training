"""Small Loki helpers for the SDR lab files. Standard library only.

Reads LOKI_URL, LOKI_USER, LOKI_PASSWORD and LOKI_CA_FILE from the environment (set by lab shell).
Nothing here prints a secret.
"""
import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

NS = 10**9
MIN = 60 * NS


def _headers(auth):
    if not auth:
        return {}
    pair = "%s:%s" % (os.environ["LOKI_USER"], os.environ["LOKI_PASSWORD"])
    return {"Authorization": "Basic " + base64.b64encode(pair.encode()).decode()}


def _context():
    ca = os.environ.get("LOKI_CA_FILE")
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


def call(method, url, params=None, body=None, auth=True, timeout=60):
    """Return (status, text). Never raises on an HTTP error status."""
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None if body is None else json.dumps(body).encode()
    headers = _headers(auth)
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_context()) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()


def base_url():
    return os.environ["LOKI_URL"].rstrip("/")


def push(streams, url=None, auth=True):
    """streams: list of (labels dict, [(ts_ns, line), ...]). Returns the HTTP status."""
    body = {"streams": [{"stream": labels, "values": [[str(ts), line] for ts, line in values]}
                        for labels, values in streams]}
    target = url or base_url() + "/loki/api/v1/push"
    status, text = call("POST", target, body=body, auth=auth)
    if status not in (200, 204):
        raise RuntimeError("push failed: HTTP %s %s" % (status, text[:200]))
    return status


def tag_run(streams, run):
    """Return the streams with the label seed_run added, so a search can pin itself to one seeding."""
    return [(dict(labels, seed_run=str(run)), values) for labels, values in streams]


def purge_older_seeds(seed, keep_run, lookback_s=7 * 86400):
    """Ask Loki to delete earlier copies of a seed (same lab_seed, other seed_run). Best effort.

    The newest copy is excluded by its seed_run, so a delete request that Loki processes later cannot
    remove it. Searches never depend on this: they pin to seed_run. Returns (accepted, http status).
    """
    now = int(time.time())
    selector = '{lab_seed="%s", seed_run!="%s"}' % (seed, keep_run)
    status, _ = call("POST", base_url() + "/loki/api/v1/delete",
                     params={"query": selector, "start": str(now - lookback_s), "end": str(now)})
    return status in (200, 204), status


def _range(query, start_ns, end_ns, extra):
    params = {"query": query, "start": str(int(start_ns)), "end": str(int(end_ns))}
    params.update(extra)
    status, text = call("GET", base_url() + "/loki/api/v1/query_range", params=params)
    if status != 200:
        raise RuntimeError("query failed: HTTP %s %s" % (status, text[:200]))
    return json.loads(text)


def entries(query, start_ns, end_ns, limit=5000):
    """Log query. Returns [(ts_ns, labels, line)] oldest first."""
    data = _range(query, start_ns, end_ns, {"limit": str(limit), "direction": "forward"})
    rows = []
    for series in data["data"]["result"]:
        for ts, line in series["values"]:
            rows.append((int(ts), series["stream"], line))
    return sorted(rows, key=lambda r: r[0])


def matrix(query, start_ns, end_ns, step_s):
    """Metric query. Returns {ts_seconds: summed value} over all series."""
    data = _range(query, start_ns, end_ns, {"step": str(step_s)})
    out = {}
    for series in data["data"]["result"]:
        for ts, value in series["values"]:
            out[int(float(ts))] = out.get(int(float(ts)), 0.0) + float(value)
    return out


def ready():
    status, text = call("GET", base_url() + "/ready")
    return status == 200 and "ready" in text

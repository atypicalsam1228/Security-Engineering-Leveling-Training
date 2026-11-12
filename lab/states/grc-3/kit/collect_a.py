import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone


def oc_json(*args):
    out = subprocess.run(["oc", *args, "-o", "json"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def names(kind):
    return sorted(i["metadata"]["name"] for i in oc_json("get", kind)["items"])


def cm6_fips():
    items = oc_json("get", "machineconfigs")["items"]
    rendered = [i for i in items if i["metadata"]["name"].startswith("rendered-master-")]
    newest = max(rendered, key=lambda i: i["metadata"]["creationTimestamp"])
    return {"machineconfig": newest["metadata"]["name"], "fips": newest["spec"].get("fips") is True}


def cm7_policies():
    return {"names": names("clusterpolicies.kyverno.io")}


def cm8_namespaces():
    return {"names": names("namespaces")}

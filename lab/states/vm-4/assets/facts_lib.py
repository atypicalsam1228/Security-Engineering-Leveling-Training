"""Helpers that read cluster objects with oc."""
import json
import subprocess


def oc_items(*args):
    result = subprocess.run(["oc", "get", *args, "-o", "json"], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)["items"]


def selects(selector, labels):
    """True when a Service selector matches the pod labels."""
    return bool(selector) and all(labels.get(key) == value for key, value in selector.items())


def critical_namespaces():
    named = oc_items("namespaces")
    return {n["metadata"]["name"] for n in named if (n["metadata"].get("labels") or {}).get("criticality") == "high"}

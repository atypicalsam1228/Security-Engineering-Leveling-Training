"""Exceptions as code: read the file and decide which entries count today."""
import datetime
import json
import os

REQUIRED = ("id", "package", "reason", "owner")


def load_exceptions(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return json.load(handle).get("exceptions", [])


def classify(entry, today, max_days):
    """Return active, expired or invalid for one entry."""
    if any(not str(entry.get(name, "")).strip() for name in REQUIRED):
        return "invalid"
    try:
        expires = datetime.date.fromisoformat(entry["expires"])
    except (KeyError, ValueError):
        return "invalid"
    if expires < today:
        return "expired"
    return "invalid" if (expires - today).days > max_days else "active"


def active_keys(entries, today, max_days):
    return {(e["id"], e["package"]) for e in entries if classify(e, today, max_days) == "active"}

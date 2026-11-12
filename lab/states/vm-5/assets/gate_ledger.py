"""A ledger of when each finding was first seen and when it stopped appearing."""
import datetime
import json
import os


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save(path, ledger):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(ledger, handle, indent=2, sort_keys=True)


def update(ledger, keys, today):
    """Return a new ledger. New or returning findings start today; findings that vanished get a fixed date."""
    now = today.isoformat()
    out = {}
    for key in keys:
        rec = ledger.get(key, {})
        out[key] = rec if "first_seen" in rec and "fixed" not in rec else {"first_seen": now}
    for key, rec in ledger.items():
        if key not in keys:
            out[key] = rec if "fixed" in rec else {**rec, "fixed": now}
    return out


def time_to_fix(ledger):
    spans = [(datetime.date.fromisoformat(r["fixed"]) - datetime.date.fromisoformat(r["first_seen"])).days for r in ledger.values() if "fixed" in r]
    mean = round(sum(spans) / len(spans), 1) if spans else None
    return {"fixed_count": len(spans), "mean_days": mean, "max_days": max(spans, default=None)}

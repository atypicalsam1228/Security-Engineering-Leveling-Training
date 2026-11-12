def compare(base, now):
    added = sorted(now.keys() - base.keys())
    removed = sorted(base.keys() - now.keys())
    changed = sorted(k for k in base.keys() & now.keys() if base[k] != now[k])
    drift = bool(added or removed or changed)
    return {"drift": drift, "added": added, "removed": removed, "changed": changed}

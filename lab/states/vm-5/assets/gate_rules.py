"""List the findings that block, using matches() from rule_match.py."""
import datetime

from rule_match import matches


def evaluate(findings, ledger, excepted, rules, exposure, today, listed):
    """Return one record for each blocking finding: the rules it matched and its age."""
    blocking = []
    for f in findings:
        if (f["id"], f["package"]) in excepted:
            continue
        key = f"{f['id']}|{f['package']}"
        age = (today - datetime.date.fromisoformat(ledger[key]["first_seen"])).days
        flagged = {**f, "exploited": f["id"] in listed}
        names = [r["name"] for r in rules if matches(r, flagged, age, exposure)]
        if names:
            blocking.append({"finding": key, "severity": f["severity"], "age_days": age, "rules": names})
    return blocking

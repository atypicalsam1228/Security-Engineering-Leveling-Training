import json
import sys
from datetime import datetime, timezone

TIME = "%Y-%m-%dT%H:%M:%SZ"
run = json.load(open(sys.argv[1]))["assessment-results"]["results"][0]
scope = json.load(open(sys.argv[2]))
as_of = datetime.now(timezone.utc)
if len(sys.argv) > 3:
    as_of = datetime.strptime(sys.argv[3], TIME).replace(tzinfo=timezone.utc)


def age_minutes(finding):
    seen = {r["observation-uuid"] for r in finding["related-observations"]}
    newest = max(o["collected"] for o in run["observations"] if o["uuid"] in seen)
    return round((as_of - datetime.strptime(newest, TIME).replace(tzinfo=timezone.utc)).total_seconds() / 60)


ages = {f["title"]: age_minutes(f) for f in run["findings"]}
ids = [c["id"] for c in scope["controls"]]
fresh = [c for c in ids if c in ages and ages[c] <= scope["max_age_minutes"]]
percent = lambda part: round(100 * len(part) / len(ids))
print(json.dumps({
    "as_of": as_of.strftime(TIME), "controls_in_scope": len(ids),
    "automated_percent": percent(ages), "fresh_percent": percent(fresh),
    "oldest_age_minutes": max(ages.values(), default=None),
    "no_evidence": [c for c in ids if c not in ages],
    "stale": [c for c in ages if ages[c] > scope["max_age_minutes"]],
    "not_satisfied": [f["title"] for f in run["findings"] if f["target"]["status"]["state"] == "not-satisfied"],
}))

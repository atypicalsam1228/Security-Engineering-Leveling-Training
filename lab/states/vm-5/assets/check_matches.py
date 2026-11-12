"""Check rule_match.matches() against known answers. Prints ok, or the cases that came out wrong."""
from rule_match import matches

CRIT = {"severity": "CRITICAL", "fix": "2.0", "exploited": False}
HIGH = {"severity": "HIGH", "fix": "2.0", "exploited": False}
NOFIX = {"severity": "CRITICAL", "fix": "", "exploited": False}
MED_LISTED = {"severity": "MEDIUM", "fix": "2.0", "exploited": True}
FIXABLE = {"name": "critical-fixable", "severity": ["CRITICAL"], "fix": True}
LISTED = {"name": "known-exploited", "exploited": True}
OVERDUE = {"name": "high-fixable-overdue", "severity": ["HIGH"], "fix": True, "min_age_days": 30}
EXPOSED = {"name": "critical-exposed", "severity": ["CRITICAL"], "exposure": "external"}

CASES = [
    ("critical with a fix matches critical-fixable", FIXABLE, CRIT, 0, "internal", True),
    ("high does not match critical-fixable", FIXABLE, HIGH, 0, "internal", False),
    ("critical with no fix does not match critical-fixable", FIXABLE, NOFIX, 0, "internal", False),
    ("listed finding matches known-exploited", LISTED, MED_LISTED, 0, "internal", True),
    ("unlisted finding does not match known-exploited", LISTED, CRIT, 0, "internal", False),
    ("high at 29 days is not yet overdue", OVERDUE, HIGH, 29, "internal", False),
    ("high at 30 days is overdue", OVERDUE, HIGH, 30, "internal", True),
    ("critical-exposed matches when external", EXPOSED, NOFIX, 0, "external", True),
    ("critical-exposed does not match when internal", EXPOSED, NOFIX, 0, "internal", False),
    ("a rule with no exposure matches when internal", FIXABLE, CRIT, 0, "internal", True),
]

wrong = [name for name, rule, finding, age, where, want in CASES if matches(rule, finding, age, where) is not want]
if wrong:
    print("not yet right:")
    for name in wrong:
        print("  " + name)
else:
    print(f"ok: all {len(CASES)} cases")

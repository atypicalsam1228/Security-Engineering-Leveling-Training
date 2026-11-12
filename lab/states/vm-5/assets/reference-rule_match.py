"""One rule against one finding. Part of the gate."""


def matches(rule, finding, age_days, exposure):
    """True only when every condition the rule names holds. A condition the rule does not name is ignored."""
    if finding["severity"] not in rule.get("severity", [finding["severity"]]):
        return False
    if "fix" in rule and bool(finding["fix"]) != rule["fix"]:
        return False
    if "exploited" in rule and finding["exploited"] != rule["exploited"]:
        return False
    if age_days < rule.get("min_age_days", 0):
        return False
    return rule.get("exposure", exposure) == exposure

"""Due dates and tracking-item titles."""
import datetime

DUE_DAYS = {"CRITICAL": 15, "HIGH": 30, "MEDIUM": 90}


def due_date(severity, today):
    days = DUE_DAYS.get(severity)
    if days is None:
        return None
    return today + datetime.timedelta(days=days)


def item_title(finding):
    return f"{finding['severity']} {finding['id']} in {finding['package']}"

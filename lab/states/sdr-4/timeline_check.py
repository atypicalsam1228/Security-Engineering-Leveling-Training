"""Check timeline.tsv. Run: python3 timeline_check.py [timeline.tsv]

Columns, tab separated: time (UTC, ISO), source (keycloak, audit or falco), actor, action, object.
The check fails unless the key events appear in the right order and nothing from an unrelated actor is mixed in.
"""
import calendar
import sys
import time
from pathlib import Path

import events_sdr4 as ev

HERE = Path(__file__).resolve().parent
OWN_ACTORS = {ev.USER, "root"}


def main(path):
    anchor = int((HERE / "anchor.txt").read_text().strip())
    rows = [line.rstrip("\n").split("\t") for line in Path(path).read_text().splitlines() if line.strip()]
    problems = [i + 1 for i, r in enumerate(rows) if len(r) != 5]
    if problems:
        print("FAIL  rows with other than 5 columns: %s" % problems)
        return 1
    stamps = [calendar.timegm(time.strptime(r[0][:19], "%Y-%m-%dT%H:%M:%S")) for r in rows]
    bad = []
    if stamps != sorted(stamps):
        bad.append("rows are not in time order")
    strangers = sorted({r[2] for r in rows} - OWN_ACTORS)
    if strangers:
        bad.append("rows from unrelated actors: %s" % ", ".join(strangers))
    wanted = [(s, a) for _, s, a in ev.timeline_rows(anchor * 10**9)]
    have = [(r[1], r[3]) for r in rows]
    failures = sum(1 for r in have if r == ("keycloak", "LOGIN_ERROR"))
    if failures != ev.FAILURES:
        bad.append("expected %d LOGIN_ERROR rows, found %d" % (ev.FAILURES, failures))
    position = -1
    for key in dict.fromkeys(wanted):
        if key not in have:
            bad.append("missing event: %s %s" % key)
        elif have.index(key) < position:
            bad.append("out of order: %s %s" % key)
        else:
            position = have.index(key)
    for line in bad:
        print("FAIL  " + line)
    print("TIMELINE " + ("PASSED (%d rows)" % len(rows) if not bad else "FAILED"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "timeline.tsv"))

"""Load recorded samples and ask Loki whether a detection fires on them. Standard library only."""
import json
import time
from pathlib import Path

import lokilib as loki
import replay

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
ARRIVE_WAIT_S = 20


def load_sample(name, case):
    """Return (events, labels) for one case. events is [(offset_ns, line)] relative to the replay base time."""
    events, labels = [], {}
    for raw in (SAMPLES / (name + ".jsonl")).read_text().splitlines():
        rec = json.loads(raw)
        if rec["case"] == case:
            events.append((rec["offset_s"] * loki.NS, rec["line"]))
            labels = rec["labels"]
    if not events:
        raise KeyError("no events for case %s in samples/%s.jsonl" % (case, name))
    return events, labels


def fires(rule, events, labels):
    """Replay events under a fresh run label and report whether the rule would have fired."""
    run = replay.new_run()
    base = int(time.time() * loki.NS) - 15 * loki.MIN
    replay.push(events, base, run, labels)
    for _ in range(ARRIVE_WAIT_S):
        got = loki.entries('{lab_replay="%s"}' % run, base - loki.MIN, base + 12 * loki.MIN)
        if len(got) >= len(events):
            break
        time.sleep(1)
    steps = replay.evaluate(rule["expr"], rule["op"], rule["threshold"], run, base - loki.MIN, base + 12 * loki.MIN)
    return any(steps.values())

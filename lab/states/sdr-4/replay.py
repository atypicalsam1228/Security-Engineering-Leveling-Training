"""Replay recorded events against a detection expression. Standard library only.

A replay pushes the events into Loki under a label unique to this run (lab_replay), then asks Loki to
evaluate the detection expression every step over the replayed span, with that label added to the selector.
Nothing real is touched: other records never carry the run label.
"""
import random
import time

import lokilib as loki

STEP_S = 60


def new_run():
    return "r%d%04d" % (int(time.time()), random.randint(0, 9999))


def inject(expr, run):
    """Add the run label to the first stream selector in the expression."""
    if "{" not in expr:
        raise ValueError("expression has no stream selector")
    return expr.replace("{", '{lab_replay="%s", ' % run, 1)


def push(events, base_ns, run, labels, url=None, auth=True):
    """events: [(offset_ns, line)] relative to base_ns. labels: stream labels without lab_replay."""
    stream = dict(labels, lab_replay=run)
    loki.push([(stream, sorted((base_ns + off, line) for off, line in events))], url=url, auth=auth)


def compare(op, value, threshold):
    if op == "gt":
        return value > threshold
    if op == "lt":
        return value < threshold
    raise ValueError("unsupported comparison %r (use gt or lt)" % op)


def evaluate(expr, op, threshold, run, start_ns, end_ns, step_s=STEP_S):
    """Return {ts_seconds: fired} for every step. A step with no data counts as value 0."""
    first = (start_ns // loki.NS // step_s + 1) * step_s      # steps start on a multiple of step_s
    last = end_ns // loki.NS
    series = loki.matrix(inject(expr, run), first * loki.NS, end_ns, step_s)
    return {t: compare(op, series.get(t, 0.0), threshold) for t in range(first, last + 1, step_s)}

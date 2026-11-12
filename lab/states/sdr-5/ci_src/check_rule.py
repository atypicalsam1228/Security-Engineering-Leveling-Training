"""Offline check of one rule file against its recorded samples. No Loki needed. Standard library only.

It imitates the filter part of the query on the recorded events: the stages after "| json |" of the form
field="x", field=~"regex", field!="x", field!~"regex". It is a quick local check; the pipeline test runner
(replay in Loki) stays the real proof.
"""
import json
import re
import sys
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
STAGE = re.compile(r'\s*(\w+)\s*(=~|!~|!=|=)\s*"(.*)"\s*$')
NEEDED = ("objectRef_resource", "objectRef_subresource", "verb", "user_username")


def flatten(obj, prefix=""):
    flat = {}
    for key, value in obj.items():
        name = prefix + key
        if isinstance(value, dict):
            flat.update(flatten(value, name + "_"))
        else:
            flat[name] = str(value)
    return flat


def passes(stages, event):
    for field, op, value in stages:
        got = event.get(field, "")
        hit = re.fullmatch(value, got) is not None if "~" in op else got == value
        if hit == op.startswith("!"):
            return False
    return True


def parse(expr):
    if "| json |" not in expr:
        raise ValueError('the expr must contain "| json |"')
    body = expr.split("| json |", 1)[1].rsplit("[", 1)[0]
    stages = []
    for text in body.split(" | "):
        found = STAGE.match(text)
        if not found:
            raise ValueError("cannot read this filter: %r (write field=\"x\" or field!~\"x\")" % text.strip())
        stages.append(found.groups())
    return stages


def problems(rule):
    if "FILL" in json.dumps(rule):
        return ["a FILL-IN marker is still in the file"]
    stages = parse(rule["expr"])
    missing = [n for n in NEEDED if n not in [s[0] for s in stages]]
    if missing:
        return ["the expr does not filter on: " + ", ".join(missing)]
    tests = rule.get("tests") or []
    out = []
    for test in tests:
        events = [json.loads(json.loads(l)["line"]) for l in (SAMPLES / (test["sample"] + ".jsonl")).read_text().splitlines()
                  if json.loads(l)["case"] == test["case"]]
        count = sum(1 for e in events if passes(stages, flatten(e)))
        fired = count > rule["threshold"]
        want = test["expect"] == "fire"
        print("%s  %s: expected %s, local check says %s" % ("OK  " if fired == want else "WRONG", test["case"], test["expect"], "fire" if fired else "no_fire"))
        if fired != want:
            out.append("%s gives the wrong answer" % test["case"])
    if len(tests) < 3:
        out.append("write all three tests")
    return out


def main():
    rule = json.loads(Path(sys.argv[1]).read_text())
    found = problems(rule)
    print("PASS  %s looks right" % rule["title"] if not found else "FAIL  " + "; ".join(found))
    sys.exit(1 if found else 0)


main()

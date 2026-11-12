#!/usr/bin/env python3
"""Usage: review_gate.py measure.py [result.json]. Fails (exit 1) when the script or its output is not acceptable."""
import ast
import json
import sys

MAX_CODE_LINES = 35
CASES = {"ok", "root", "latest", "nolimits"}


def static_problems(path):
    source = open(path).read()
    code_lines = [l for l in source.splitlines() if l.strip() and not l.strip().startswith("#")]
    problems = []
    if len(code_lines) > MAX_CODE_LINES:
        problems.append("%d code lines; keep it under %d" % (len(code_lines), MAX_CODE_LINES + 1))
    try:
        tree = ast.parse(source)
    except SyntaxError as err:
        return problems + ["does not parse: %s" % err]
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    strings = " ".join(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str))
    ints = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool)]
    drops_first = any(isinstance(n, ast.Slice) and isinstance(n.lower, ast.Constant) and n.lower.value == 1 for n in ast.walk(tree))
    wall_clock = any(isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "time" for n in ast.walk(tree))
    if "perf_counter" not in attrs:
        problems.append("time with time.perf_counter, not a wall clock")
    if wall_clock:
        problems.append("time.time() is not allowed for timing")
    if "--dry-run=server" not in strings:
        problems.append("measure with --dry-run=server so no object is created")
    if "median" not in attrs:
        problems.append("report the median, not one reading or the mean")
    if not any(v >= 20 for v in ints):
        problems.append("take at least 20 samples")
    if not drops_first:
        problems.append("discard the first sample (a [1:] slice); it includes warm-up")
    return problems


def output_problems(path):
    try:
        data = json.load(open(path))
    except (OSError, ValueError) as err:
        return ["result file unreadable: %s" % err]
    problems = [("missing key " + k) for k in ("mode", "n", "median_ms", "p95_ms", "outcomes") if k not in data]
    if problems:
        return problems
    if data["n"] < 19:
        problems.append("only %s samples in the result" % data["n"])
    if not data["median_ms"] > 0:
        problems.append("median_ms must be above 0")
    if set(data["outcomes"]) != CASES or not set(data["outcomes"].values()) <= {"allowed", "denied"}:
        problems.append("outcomes must list the four cases as allowed or denied")
    return problems


def main():
    problems = static_problems(sys.argv[1])
    if len(sys.argv) > 2:
        problems += output_problems(sys.argv[2])
    for problem in problems:
        print("FAIL: " + problem)
    print("review gate: %s" % ("FAILED" if problems else "PASSED"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

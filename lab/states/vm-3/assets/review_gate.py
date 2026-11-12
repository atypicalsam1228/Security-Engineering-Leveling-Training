"""Review gate for the triage tool (VM-3).

Usage: python3 review_gate.py <folder holding rank.py deadlines.py gitea_api.py gitea_items.py triage.py>

The gate does not trust the learner's code. It re-states the rules in its own words and checks the
tool's real behaviour against them. It exits 0 when every check passes and 1 when any check fails.
Nothing here talks to Gitea: the tool is only run with --dry-run, or with no token.
"""
import datetime
import json
import os
import subprocess
import sys

FIXTURE = "fixture-findings.json"
EMPTY = "fixture-empty.json"
SECRET = "gate-test-secret-value"
DAYS = {"CRITICAL": 15, "HIGH": 30, "MEDIUM": 90}
RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else ": " + detail))
    if not ok:
        failures.append(name)


def raw_findings():
    with open(FIXTURE, encoding="utf-8") as handle:
        report = json.load(handle)
    rows = {}
    for result in report["Results"]:
        for v in result.get("Vulnerabilities") or []:
            scores = [s.get("V3Score", 0) for s in (v.get("CVSS") or {}).values()]
            rows[(v["VulnerabilityID"], v["PkgName"])] = (RANK[v["Severity"]], max(scores, default=0.0), bool(v.get("FixedVersion")), v["VulnerabilityID"], v["Severity"], v["PkgName"])
    return list(rows.values())


def run_tool(folder, *args, token=SECRET):
    env = dict(os.environ, GITEA_TOKEN=token, GITEA_URL="http://127.0.0.1:9", GITEA_USER="gate")
    return subprocess.run([sys.executable, os.path.join(folder, "triage.py"), *args], capture_output=True, text=True, env=env, timeout=60)


def main(folder):
    expected = sorted((r for r in raw_findings() if r[4] in DAYS), key=lambda r: (-r[0], -r[1], not r[2], r[3]))
    dry = run_tool(folder, FIXTURE, "--dry-run")
    check("dry run exits 0", dry.returncode == 0, dry.stderr.strip()[-200:])
    lines = [json.loads(x) for x in dry.stdout.splitlines() if x.strip().startswith("{")]
    titles = [x["title"] for x in lines]
    want = [f"{r[4]} {r[3]} in {r[5]}" for r in expected]
    check("one item per finding, no duplicates", len(titles) == len(set(titles)) == len(want), f"got {len(titles)} items, expected {len(want)}")
    check("items are ranked by severity, score, then fix first", titles == want, f"got {titles[:3]} ...")
    today = datetime.date.today()
    bad = [x["title"] for x in lines if x["due"] != (today + datetime.timedelta(days=DAYS[x["title"].split()[0]])).isoformat()]
    check("due dates follow the severity table", not bad, f"wrong due date on {bad[:2]}")
    check("low findings get no item", not any(x["title"].startswith("LOW") for x in lines))
    check("the token is never printed", SECRET not in dry.stdout + dry.stderr)
    nothing = run_tool(folder, FIXTURE, token="")
    check("missing token stops with a message", nothing.returncode != 0 and "GITEA_TOKEN" in nothing.stderr and "Traceback" not in nothing.stderr, nothing.stderr.strip()[-200:])
    empty = run_tool(folder, EMPTY, "--dry-run")
    check("a scan that analyzed nothing is refused", empty.returncode != 0 and "Traceback" not in empty.stderr, "exit code " + str(empty.returncode))
    print("RESULT: " + ("PASS" if not failures else f"FAIL ({len(failures)} checks failed)"))
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))

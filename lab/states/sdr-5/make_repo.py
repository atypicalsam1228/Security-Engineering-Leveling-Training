"""Developer tool, not run by lab start. Regenerates repo/: the starting contents of the Gitea repository `detections`.

Run from this folder: python3 make_repo.py
The recorded samples reuse the SDR-4 scenarios (same audit shapes) and are written as JSON lines.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sdr-4"))

from scenarios_sdr4 import SCENARIOS  # noqa: E402

RULES = {
    "priv-escalation": {
        "expr": 'sum(count_over_time({log_type="audit"} | json | objectRef_resource=~"rolebindings|clusterrolebindings" '
                '| verb=~"create|patch|update" | user_username!~"system:.*" | requestObject_roleRef_name=~"admin|cluster-admin" [5m]))',
        "op": "gt", "threshold": 0, "severity": "high", "control": "SI-4",
    },
    "secret-read": {
        "expr": 'sum(count_over_time({log_type="audit"} | json | objectRef_resource="secrets" '
                '| verb=~"get|list" | user_username!~"system:.*" [5m]))',
        "op": "gt", "threshold": 3, "severity": "medium", "control": "SI-4",
    },
}
LABELS = {"log_type": "audit"}
README = """# detections

Detections as code. One file per detection in rules/, recorded sample events in samples/, the test and deploy
scripts in ci/. A change is merged only after its tests pass; the pipeline then publishes the rules to Grafana.

rules/NAME.json   uid, title, expr (LogQL), op, threshold, severity, control, tests
samples/NAME.jsonl   one recorded event per line: case, offset_s, labels, line
ci/               helpers (lokilib.py, replay.py, detlib.py, gf.py, mm.py, probe.py); ci/task.yaml (the Tekton Task) is added by 20-gitea-repo.sh from ci_src/task.yaml.tpl; ci/check_rule.py checks a rule file offline against its samples; you write rules/pod-exec.json, then add run_tests.py, deploy.py, pipeline.yaml and measure.py
"""


def main():
    out = HERE / "repo"
    shutil.rmtree(out, ignore_errors=True)
    for sub in ("rules", "samples", "ci"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    (out / "README.md").write_text(README)
    for name in list(RULES) + ["pod-exec"]:
        lines = []
        tests = []
        for sc in (s for s in SCENARIOS if s["detection"] == name):
            tests.append({"sample": name, "case": sc["id"], "expect": "fire" if sc["expect"] == "fire" else "no_fire"})
            for off_ns, line in sc["events"]:
                lines.append(json.dumps({"case": sc["id"], "offset_s": off_ns // 10**9, "labels": LABELS, "line": line}, separators=(",", ":")))
        (out / "samples" / (name + ".jsonl")).write_text("\n".join(lines) + "\n")
        if name in RULES:
            rule = dict(RULES[name], uid="det-" + name, title=name, tests=tests)
            (out / "rules" / (name + ".json")).write_text(json.dumps(rule, indent=2) + "\n")
    for lib in ("lokilib.py", "replay.py"):
        shutil.copy(HERE / lib, out / "ci" / lib)
    for lib in ("detlib.py", "gf.py", "mm.py", "probe.py", "check_rule.py"):
        shutil.copy(HERE / "ci_src" / lib, out / "ci" / lib)
    print("wrote", out)


main()

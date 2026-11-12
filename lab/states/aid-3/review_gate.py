"""Review gate for scripts that call a model (AID-3). Lab-provided: it lives in a ConfigMap, not in the
repository under review, so the author cannot weaken it. Usage: python3 review_gate.py <repo folder>.
Exit 0 when every check passes, 1 when any check fails. Standard library only."""

import pathlib
import re
import subprocess
import sys

SECRET = re.compile(r"(?i)(password|passwd|token|secret|api_?key)\w*\s*=\s*[\"'][^\"']{8,}[\"']")
BANNED = ("shell=True", "eval(", "exec(", "os.system", "verify=False", "_create_unverified_context")
REQUIRED = {  # file name -> text that must appear in it
    "summarize.py": ('log_event("prompt"', 'log_event("reply"', "parse_reply("),
}
MIN_REJECT_TESTS = 4


def check_sources(root):
    problems = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if SECRET.search(text):
            problems.append(f"{path.name}: looks like a hardcoded secret")
        problems += [f"{path.name}: banned call {item}" for item in BANNED if item in text]
        problems += [f"{path.name}: missing {item}" for item in REQUIRED.get(path.name, ()) if item not in text]
        if subprocess.run([sys.executable, "-m", "py_compile", str(path)], capture_output=True).returncode:
            problems.append(f"{path.name}: does not compile")
    return problems


def check_tests(root):
    tests = list((root / "tests").glob("test_*.py"))
    if sum(path.read_text(encoding="utf-8").count("assertRaises") for path in tests) < MIN_REJECT_TESTS:
        return [f"tests: need at least {MIN_REJECT_TESTS} tests that expect a rejection"]
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=root, capture_output=True, text=True)
    return [] if result.returncode == 0 else ["tests: failing\n" + result.stderr[-400:]]


def main(folder):
    root = pathlib.Path(folder)
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    problems = [f"{name}: file not found" for name in missing] + check_sources(root) + check_tests(root)
    for line in problems:
        print("FAIL", line)
    print("GATE", "FAILED" if problems else "PASSED")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))

"""Pick one real capture per step (and per test) for each module and render it into modules/img.

Usage: python pick_shots.py [ID ...]     (no ID = every module except ENG-0, which names its own)
Names: <ID>-shot-<step><letter>.png and <ID>-shot-test<n>.png; render.py picks them up by name.
"""
import re
import sys
from pathlib import Path

import capture_png as cp

ROOT = cp.ROOT
IMG = ROOT / "modules" / "img"
SKIP_SUFFIX = ("stacked", "retry", "rerun", "again", "diag", "prev", "usedefault", "placeholder", "patch", "sim", "redo", "with")
VERSION_RANK = ["-v3", "-r3", "-v2", "-r2", ""]
SENSITIVE = re.compile(r"(?i)(password\s*[:=]\s*\S{4,}|BEGIN [A-Z ]*PRIVATE KEY|[\w.+-]+@[\w-]+\.[\w.]+|eyJ[A-Za-z0-9_-]{10,}|AKIA[0-9A-Z]{16}|sha256:[0-9a-f]{20,}|xox[bp]-)")
STEP = re.compile(r"^(?:step|i)?(\d+)([a-z])(?:(-v3|-r3|-v2|-r2))?$")
TEST = re.compile(r"^(?:test|t|stept)-?(\d)(?:(-v3|-r3|-v2|-r2))?$", re.I)


def out_lines(path):
    _, out, _ = cp.parse(path)
    return [l for l in out if l.strip()]


def candidates(folder):
    steps, tests = {}, {}
    for f in folder.glob("*.txt"):
        stem = f.stem
        if any(s in stem for s in SKIP_SUFFIX):
            continue
        m = STEP.match(stem)
        if m:
            key, ver = m.group(1) + m.group(2), m.group(3) or ""
            steps.setdefault(key, {})[ver] = f
            continue
        m = TEST.match(stem)
        if m:
            tests.setdefault(m.group(1), {})[m.group(2) or ""] = f
    return steps, tests


def best(versions):
    for v in VERSION_RANK:
        if v in versions:
            return versions[v]


def choose(group, per_step):
    """Per step number keep the block with the most informative output (3 to 45 lines)."""
    picked = {}
    for key, versions in group.items():
        f = best(versions)
        n = len(out_lines(f))
        if n < 2:
            continue
        step = re.match(r"\d+", key).group() if per_step else key
        score = n if n <= 45 else 45 - (n - 45) * 0.1
        if step not in picked or score > picked[step][0]:
            picked[step] = (score, key, f)
    return {k: v[1:] for k, v in picked.items()}


def main(argv):
    ids = argv or sorted(d.name for d in cp.CAPTURES.iterdir() if d.is_dir() and d.name not in ("ENG-0", "WALK") and not d.name.endswith("-prev"))
    flagged = []
    for mod in ids:
        steps, tests = candidates(cp.CAPTURES / mod)
        chosen = [(k, f, f"{mod}-shot-{k}.png") for k, f in choose(steps, True).values()]
        chosen += [(f"test{k}", f, f"{mod}-shot-test{k}.png") for k, (_, f) in choose(tests, False).items()]
        for key, f, name in chosen:
            raw = f.read_text(encoding="utf-8", errors="replace")
            for hit in SENSITIVE.findall(raw):
                flagged.append((mod, f.name, hit if isinstance(hit, str) else hit[0]))
            cp.render(f, IMG / name)
        print(mod, len(chosen), "shots:", " ".join(c[0] for c in chosen))
    if flagged:
        print("\nREVIEW THESE (possible sensitive text):")
        for item in flagged:
            print("  ", item)


if __name__ == "__main__":
    main(sys.argv[1:])

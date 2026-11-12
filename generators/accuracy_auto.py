"""Scripted accuracy checks (the AUTO items in ACCURACY-CHECK.md): C2, C3, C4, C6, C9, X1-X5.

Usage: python accuracy_auto.py     Prints one line per failed check and a count per check id; exit 1 on any failure.
Does not run validate.py (that is C1) or the framework and vendor checks (those need a reader).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT

import sources
from order import TRACK
from render import load_module
from tool_links import missing_tools

ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = ROOT / "modules"
STATES = ROOT / "lab" / "states"
EXTRA_BANNED = ["Rev 3", "Rev. 3", "Revision 3", "Rev 4", "Rev. 4", "Revision 4", "US-CERT"]
TEXT_SUFFIXES = {".md", ".py", ".sh", ".yaml", ".yml", ".json", ".txt", ".tpl", ".tf", ".alloy"}
SKIP_DIRS = {"__pycache__", ".terraform", ".pytest_cache"}
SHELL_FALSE_POSITIVES = {"IFS "}
CONTROL_OK = re.compile(r"\b[A-Z]{2}-\d{1,2}(?:\(\d+\)|\([a-z]\))?")
TWIPS_PER_INCH = 1440


def ids() -> list[str]:
    return list(TRACK)


def contract_vars() -> set[str]:
    text = (ROOT / "LAB-CONTRACT.md").read_text(encoding="utf-8")
    return set(re.search(r"^VARS:\s*(.+)$", text, re.M).group(1).split())


def check_c2(fail) -> None:
    """Titles, controls and minutes in the track overview match the module files."""
    track = (ROOT / "ENGINEERING-TRACK.md").read_text(encoding="utf-8")
    for mid in ids():
        m = load_module(mid)
        mins = m["minutes"]["hands_on"] + m["minutes"]["verify"]
        controls = ", ".join(m["controls"])
        row = re.search(rf"^\| {re.escape(mid)} \| (.+?) \| (.+?) \| (\d+) \|$", track, re.M)
        if not row:
            fail("C2", mid, "no overview row")
            continue
        if row.group(1) != m["title"]:
            fail("C2", mid, f"overview title '{row.group(1)}' vs '{m['title']}'")
        if row.group(2) != (controls or "none"):
            fail("C2", mid, f"overview controls '{row.group(2)}' vs '{controls}'")
        if int(row.group(3)) != mins:
            fail("C2", mid, f"overview minutes {row.group(3)} vs {mins}")


def check_c3(fail) -> None:
    """Prerequisites do not name a module that comes later in the track."""
    for i, mid in enumerate(TRACK):
        m = load_module(mid)
        later = set(TRACK[i + 1:])
        for text in m["prereq"]:
            for ref in re.findall(r"\b([A-Z]{2,4}-\d)\b", text):
                if ref in later:
                    fail("C3", mid, f"prerequisite names later module {ref}")


def check_c4(fail) -> None:
    contract = contract_vars()
    for mid in ids():
        m = load_module(mid)
        state = STATES / mid.lower()
        for name in ("README.md", "TODO.md"):
            if not (state / name).is_file():
                fail("C4", mid, f"missing {state.name}/{name}")
        if mid.lower() not in m["lab"]["start"].lower():
            fail("C4", mid, f"lab.start '{m['lab']['start']}' does not name the module")
        for var in m["lab"].get("env", []):
            if var not in contract:
                fail("C4", mid, f"lab.env {var} not in LAB-CONTRACT.md")


def check_c6(fail) -> None:
    for mid in ids():
        m = load_module(mid)
        mins = m["minutes"]["hands_on"] + m["minutes"]["verify"]
        if len(m["steps"]) > 5:
            fail("C6", mid, f"{len(m['steps'])} steps")
        if mins > 90:
            fail("C6", mid, f"{mins} minutes (limit 90)")
        elif mins > 75:
            fail("C6", mid, f"{mins} minutes (target 75)")


def check_c9(fail) -> None:
    """Every entry in a module's `tools` list has a row in the 'Tools used' table."""
    for mid in ids():
        missing = missing_tools(load_module(mid))
        if missing:
            fail("C9", mid, "no tool row for: " + "; ".join(missing))


def text_files() -> list[Path]:
    return [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES and not SKIP_DIRS & set(p.parts)]


def check_x1_x2(fail) -> None:
    names = [n for n in sources.banned_names() if n != "SOP"] + ["SOP "]
    for p in text_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        rel = p.relative_to(ROOT).as_posix()
        if p.name in {"accuracy_auto.py", "validate.py", "sources.py", "ACCURACY-CHECK.md", "REVIEW-BRIEF.md", "REVIEW-CHECKLIST.md"}:
            continue
        # Rendered files carry callout icons by design; the source text and start states must be ASCII.
        if "modules" not in p.parts and p.suffix in {".py", ".sh", ".yaml", ".yml", ".json", ".tpl", ".alloy"} and "generators" in p.parts + ("generators",) and ("content" in p.parts or "states" in p.parts):
            bad = sorted({c for c in text if ord(c) > 126})
            if bad:
                fail("X1", rel, f"non-ASCII {bad[:5]}")
        for n in names:
            if n.strip() in {s.strip() for s in SHELL_FALSE_POSITIVES} and p.suffix == ".sh":
                continue
            if re.search(r"\b" + re.escape(n.strip()) + r"\b", text):
                fail("X2", rel, f"banned name '{n.strip()}'")
        for n in EXTRA_BANNED:
            if n in text:
                fail("X2", rel, f"outdated term '{n}'")


def check_x3_x4_x5(fail) -> None:
    for mid in ids():
        m = load_module(mid)
        docx = next(MODULES_DIR.glob(f"{mid}-*.docx"), None)
        md = next(MODULES_DIR.glob(f"{mid}-*.md"), None)
        content = ROOT / "generators" / "content" / (mid.lower().replace("-", "_") + ".py")
        if not docx or not md:
            fail("X5", mid, "rendered docx or md missing")
            continue
        if md.stat().st_mtime + 1 < content.stat().st_mtime:
            fail("X5", mid, "rendered md is older than the content file (re-render)")
        doc = Document(str(docx))
        sec = doc.sections[0]
        usable = (sec.page_width - sec.left_margin - sec.right_margin) / 914400
        widest = 0.0
        for table in doc.tables:
            widths = [c.width for c in table.rows[0].cells if c.width]
            if widths:
                widest = max(widest, sum(widths) / 914400)
        if widest > usable + 0.05:
            fail("X3", mid, f"table {widest:.2f} in wider than usable {usable:.2f} in")
        if sec.orientation == WD_ORIENT.PORTRAIT and sec.page_width > sec.page_height:
            fail("X3", mid, "orientation flag disagrees with page size")
        body = md.read_text(encoding="utf-8")
        for token in re.findall(r"\b([A-Z]{2})[ _](\d{1,2})\b", body):
            if token[0] in {c.split("-")[0] for c in m["controls"]}:
                fail("X4", mid, f"control written without hyphen: {token[0]} {token[1]}")


def main() -> int:
    failures: list[tuple[str, str, str]] = []

    def fail(check: str, where: str, msg: str) -> None:
        failures.append((check, where, msg))

    for fn in (check_c2, check_c3, check_c4, check_c6, check_c9, check_x1_x2, check_x3_x4_x5):
        fn(fail)
    for check, where, msg in failures:
        print(f"{check} {where}: {msg}")
    counts = Counter(c for c, _, _ in failures)
    print("summary:", json.dumps(dict(sorted(counts.items()))) if counts else "all AUTO checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

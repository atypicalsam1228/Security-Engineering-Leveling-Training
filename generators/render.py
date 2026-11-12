"""Render a module content file (content/<id>.py defining MODULE) to .docx and .md.

Usage: python render.py GRC-2 [MOD-ID ...]   (or: python render.py --all)
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from common_terms import extras
from doc_builder import DocBuilder
from module_diagrams import render_concept_diagram, render_diagrams, render_step_diagram
from order import position
from tool_links import tool_rows

HERE = Path(__file__).resolve().parent
CONTENT_DIR = HERE / "content"
OUT_DIR = HERE.parent / "modules"

INTENT_LABELS = (
    ("feared", "Control Intent"),
    ("scope", "Is it in scope for the system"),
    ("question", "The operational question"),
    ("evidence", "What evidence proves it"),
    ("sufficient", "How much is enough"),
    ("tieoff", "Who is told when it fails"),
    ("tool", "How the tool in this module satisfies it"),
)


def load_module(module_id: str) -> dict:
    path = CONTENT_DIR / f"{module_id.lower().replace('-', '_')}.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MODULE


def _header(b: DocBuilder, m: dict) -> None:
    mins = m["minutes"]
    suffix = f" ({', '.join(m['controls'])})" if m["controls"] else ""
    b.title(f"{m['id']}: {m['title']}{suffix}")
    if m.get("draft") and not m.get("hide_draft"):
        b.note(f"DRAFT. {m['draft']}")
    b.table(
        ["Item", "Detail"],
        [
            ["Sequence", "Module {} of {} in the recommended order".format(*position(m["id"]))],
            ["Timed work", f"About {mins['hands_on'] + mins['verify']} minutes ({mins['hands_on']} hands-on, {mins['verify']} verify)"
             if mins["verify"] else f"About {mins['hands_on']} minutes"],
            ["Standalone start", f"`{m['lab']['start']}`"],
            ["Combined start", "Continue from the end state of the previous module"],
            ["Tools", ", ".join(m["tools"])],
            ["Prerequisites", ", ".join(m["prereq"])],
        ] + ([["Status", "Optional. No other module needs it."]] if m.get("optional") else [])
        + ([["Extra lab needs", "; ".join(m["lab_needs"])]] if m.get("lab_needs") else []),
    )


def _intent(b: DocBuilder, m: dict) -> None:
    b.h1("Section 1. Module Overview")
    if m.get("requirement_bullets"):
        for item in m["requirement_bullets"]:
            b.bullet(item)
        b._md("")
    else:
        b.para(m["requirement"])
    if m.get("objectives"):
        b.objectives([(o["label"], o["text"]) for o in m["objectives"]])
    if m.get("architect_inline") and m.get("architect"):
        b.para(m["architect"])
    if not m["mapping"] or m.get("intent_at_end"):
        return
    _mapping(b, m)
    if not m.get("intent_at_end"):
        b.h2("What each control is for")
        b.para("Read these answers first. They explain what each control is trying to prevent and how this module's tool meets it.")
        for item in m["intent"]:
            b.h3(item["control"])
            b.table(["Question", "Answer"], [[label, item[key]] for key, label in INTENT_LABELS])
    if m.get("architect") and not m.get("architect_inline"):
        b.h2("Architect mode brief")
        b.para(m["architect"])


def _mapping(b: DocBuilder, m: dict) -> None:
    b.h2("Control mapping")
    if all(r.get("tool") for r in m["mapping"]):
        b.table(
            ["Control", "What it requires, in plain words", "Tool or service", "Where this module covers it"],
            [[r["control"], r["plain"], r["tool"], r["covered"]] for r in m["mapping"]],
        )
    else:
        b.table(
            ["Control", "What it requires, in plain words", "Source of the value", "Where this module covers it"],
            [[r["control"], r["plain"], r["source"], r["covered"]] for r in m["mapping"]],
        )


def _terms_and_concepts(b: DocBuilder, m: dict) -> None:
    if not m.get("terms_at_end"):
        _terms_table(b, m, m["terms"], heading="h2")
    b.h1("Section 2. The Tools")
    b.h2("Tools used in this module")
    if m.get("tool_why"):
        b.para("Each tool name links to its official overview. The table columns say how each tool is used in the lab and why the lab uses it instead of another way of doing the same job.")
    else:
        b.para("Each tool name links to its official overview. The last column of the table says how each tool is used in the lab.")
    b.tool_table(tool_rows(m))
    render_diagrams(b, m)
    for c in m["concepts"]:
        b.h2(c["heading"], ", ".join(c["id"] for c in c.get("controls", [])))
        for p in c["paras"]:
            if isinstance(p, dict) and "bullets" in p:
                for item in p["bullets"]:
                    b.bullet(item)
            elif isinstance(p, dict) and "code" in p:
                b.code(p["code"], "text")
            elif isinstance(p, dict):
                b.h3(p["control"])
                b.para(p["text"], italic=True)
            else:
                b.para(p)
        if c.get("diagram_id"):
            render_concept_diagram(b, m, c["diagram_id"])
        if c.get("table"):
            b.table(c["table"]["headers"], [list(r) for r in c["table"]["rows"]])
        if c.get("diagram"):
            b.para(c.get("diagram_caption", "This is a picture. It is not a command, so do not type it anywhere."), italic=True)
            b.code(c["diagram"], "text")
        if c.get("production"):
            b.production(c["production"])
    _design(b, m)


def _terms_table(b: DocBuilder, m: dict, rows: list, heading: str, number: int | None = None) -> None:
    """The quick-lookup term table, as a section of its own."""
    if heading == "h1":
        b.h1(f"Section {number}. Terms", collapsed=True)
    else:
        b.h2("Terms in this module")
    if m.get("hover"):
        b.para("Each term is also explained the first time it appears. In Word, hover over an underlined term to see its meaning, or Ctrl+click it to jump to this table.")
        b.doc.paragraphs[-1].paragraph_format.keep_with_next = True
        b.terms_table([tuple(t) for t in rows], side_by_side=bool(m.get("terms_at_end")))
    else:
        b.para("Each term is also explained the first time it appears. This table is a quick lookup.")
        b.table(["Term", "Plain meaning"], [list(t) for t in rows])


def _merged_terms(m: dict) -> list:
    """The module terms plus the glossary entries that are not already terms, sorted for lookup."""
    seen = {t[0].lower() for t in m["terms"]}
    extra = [g for g in m["glossary"] if g[0].lower() not in seen]
    return sorted([*m["terms"], *extra], key=lambda t: t[0].lower())


def _design(b: DocBuilder, m: dict) -> None:
    """Short design decisions: how it is built, why, and the alternatives with their pros and cons."""
    if not m.get("design"):
        return
    b.h2("Design decisions")
    for d in m["design"]:
        b.h3(d["decision"])
        b.bullet("How: " + d["how"])
        b.bullet("Why: " + d["why"])
        b.bullet("Alternatives: " + d["alternatives"])


def _code(b: DocBuilder, block: dict) -> None:
    b.code(block["code"], block.get("lang", "bash"))
    if block.get("expect"):
        b.output(block["expect"])
    if block.get("lines"):
        rows = [list(r) for r in block["lines"]]
        if all(len(r) == 3 for r in rows):
            b.table(["Part", "What it does", "Why you run it"], rows)
        else:
            b.table(["Part", "What it does"], rows)


def _shot(b: DocBuilder, block: dict, auto: str = "", label: str = "") -> None:
    """A cropped screenshot of the relevant part of a real run, shown under the block's expected output.
    With no explicit screenshot key, a file named <ID>-shot-<step>.png in img/ is used when it exists."""
    shot = block.get("screenshot")
    if not shot and auto and (OUT_DIR / "img" / f"{auto}.png").exists():
        shot = {"file": f"{auto}.png", "alt": f"Output from a real lab run: {label or auto}", "width": 6.3}
    if shot:
        b.image(OUT_DIR / "img" / shot["file"], shot["alt"], "", width_in=shot.get("width", 6.0))


def _intro(b: DocBuilder, block: dict) -> None:
    """The block intro, then its short sequence (each line starts First, Then, Next or Finally) and any look-for bullets."""
    first, *rest = re.split(r"(?<=[.!?])\s+(?=[A-Za-z`])", block["intro"].strip())
    b.para(first)
    for sentence in rest:
        b.bullet(sentence)
    for item in block.get("sequence", []):
        b.bullet(item)
    if block.get("look_for"):
        b.para("Look for these as you read:")
        for item in block["look_for"]:
            b.bullet(item)


def _setup(b: DocBuilder, m: dict) -> None:
    """Optional install-and-start section shown before Step 1 (first module only)."""
    setup = m.get("setup")
    if not setup:
        return
    b.h2(setup["title"])
    b.para(setup["intro"])
    if setup.get("needs"):
        b.para("You need these before you start:")
        for item in setup["needs"]:
            b.bullet(item)
    for block in setup["blocks"]:
        b.h3(block["label"])
        _intro(b, block)
        _code(b, block)
        _shot(b, block)
    b.checkpoint(setup["checkpoint"])


def _steps(b: DocBuilder, m: dict) -> None:
    b.h1("Section 3. Implement")
    b.bullet(f"Start: type `{m['lab']['start']}` in the terminal on your own computer (PowerShell on Windows, Terminal on Mac), not in the lab shell.")
    b.bullet("Enter lab shell with `lab shell`. Every other command in this module runs inside lab shell.")
    if m.get("architect"):
        b.bullet("Architect learners design each step first using the brief in Section 1.")
    b.bullet(f"If a step fails: run `lab reset {m['id'].lower()}` on your own computer and repeat the step once. If it still fails, copy the whole command and error and ask your AI assistant. Do not skip the step.")
    _setup(b, m)
    for n, s in enumerate(m["steps"], start=1):
        b.h2(f"Step {n}. {s['title']}", ", ".join(c["id"] for c in s.get("controls", [])))
        if s.get("learn"):
            b.learning_point(s["learn"])
        if s.get("why"):
            b.prose(s["why"])
        render_step_diagram(b, m, n)
        for index, block in enumerate(s["blocks"]):
            if block.get("label"):
                b.h3(f"{n}{chr(97 + index)}. {block['label']}")
                _intro(b, block)
            _code(b, block)
            _shot(b, block, f"{m['id']}-shot-{n}{chr(97 + index)}", block.get("label", ""))
        if s.get("note"):
            b.note(s["note"])
        if s.get("security"):
            b.security(s["security"])
        if s.get("tip"):
            b.tip(s["tip"])
        if s.get("action"):
            b.action(s["action"])
        b.checkpoint(s["checkpoint"])
        if s.get("takeaway"):
            b.takeaway(s["takeaway"])
        b.control_notes([(c["id"], c["how"]) for c in s.get("controls", []) if c.get("how")])


def _section_shift(m: dict) -> int:
    """Section numbers after Implement drop by one when the module has no separate Verify section."""
    return 0 if m["verify"] else -1


def _verify(b: DocBuilder, m: dict) -> None:
    if not m["verify"]:
        return
    b.h1("Section 4. Verify It Works")
    for n, v in enumerate(m["verify"], start=1):
        b.h2(f"Test {n} ({v['kind']}). {v['title']}", ", ".join(c["id"] for c in v.get("controls", [])))
        b.prose(v["why"])
        _code(b, v)
        _shot(b, v, f"{m['id']}-shot-test{n}", v["title"])
        b.checkpoint(v["checkpoint"])
        b.control_notes([(c["id"], c["how"]) for c in v.get("controls", []) if c.get("how")])


def _faults(b: DocBuilder, m: dict) -> None:
    if not m.get("faults"):
        return
    b.h1("Section 5. Break It and Watch (optional)")
    b.note("This section is optional. You can skip all of it, or do only the faults you choose, and nothing later depends on it. If you apply a fault, restore it before you move on: `lab status` shows any fault still active, and `lab start` warns you.")
    b.para(m["faults_intro"])
    b.para("List the faults and see which are active: `lab break " + m["id"].lower() + " --list`.")
    gap = m["fault_gap"]
    b.h2(gap["heading"])
    b.para(gap["why"])
    _code(b, {"code": gap["code"], "lines": gap["lines"]})
    b.checkpoint(gap["see"])
    for n, f in enumerate(m["faults"], start=1):
        b.h2(f"Fault {n}. {f['title']}")
        b.para("What it simulates: " + f["simulates"])
        b.para("Apply it:")
        b.code(f"lab break {m['id'].lower()} {f['id']}", "bash")
        b.para("This is what the command runs, so you can see exactly what changed:")
        b.code(f["break_code"], "bash")
        b.para(f["wait"])
        for sig in f["signals"]:
            b.para("Look here: " + sig["where"])
            if sig.get("code"):
                b.code(sig["code"], "bash")
            b.checkpoint(sig["see"])
        b.note("How to tell this fault apart from the others: " + f["tells_apart"])
        b.tip("If the evidence does not appear: " + f["if_silent"])
        b.para("Restore it:")
        b.code(f"lab restore {m['id'].lower()} {f['id']}", "bash")
        b.code(f["restore_code"], "bash")
        b.checkpoint(f["recovered"])


SHORT_INTENT_KEYS = ("feared", "question", "evidence", "sufficient", "tool")


def _control_intent(b: DocBuilder, m: dict) -> None:
    """The short per-control answers, placed after the hands-on work when the module sets intent_at_end."""
    number = (6 if m.get("faults") else 5) + _section_shift(m)
    b.h1(f"Section {number}. What Each Control Is For")
    if m.get("mapping"):
        _mapping(b, m)
        b.h2("What each control is for")
    b.para("Each table below says what the control is trying to prevent and how this module's tool meets it.")
    for item in m["intent"]:
        b.h3(item["control"])
        b.table(["Question", "Answer"], [[label, item[key]] for key, label in INTENT_LABELS if key in SHORT_INTENT_KEYS])


def _portability(b: DocBuilder, m: dict) -> None:
    """Optional: what changes when the module's scripts run outside the lab."""
    p = m.get("portability")
    if not p:
        return
    b.h2("Using this in other environments")
    for item in p["bullets"]:
        b.bullet(item)
    b._md("")
    b.para(p.get("lead", "The table shows what changes on each platform:"))
    b.table(p["headers"], [list(row) for row in p["rows"]])


def _closing(b: DocBuilder, m: dict) -> None:
    shift = 1 if m.get("intent_at_end") else 0
    number = (6 if m.get("faults") else 5) + shift + _section_shift(m)
    if m.get("terms_at_end"):
        b.h1(f"Section {number}. Next Steps")
        _portability(b, m)
        if m.get("production"):
            b.production(m["production"])
        b.tip(m["next"])
        number += 1
        if m.get("command_list"):
            _command_list(b, m, number)
            number += 1
        _terms_table(b, m, _merged_terms(m), heading="h1", number=number)
        return
    b.h1(f"Section {number}. Glossary and Next Steps")
    b.table(["Term", "Meaning"], [list(g) for g in m["glossary"]])
    _portability(b, m)
    if m.get("production"):
        b.production(m["production"])
    b.tip(m["next"])
    _command_list(b, m, number + 1)


def _command_list(b: DocBuilder, m: dict, number: int) -> None:
    """Optional last section: every command of the steps in order, with no explanation."""
    groups = m.get("command_list")
    if not groups:
        return
    b.h1(f"Section {number}. Command List (optional)", collapsed=True)
    b.prose(m["command_list_intro"])
    for group in groups:
        b.h3(group["heading"])
        b.code(group["code"], group.get("lang", "bash"))


def render(m: dict) -> tuple[Path, Path]:
    b = DocBuilder()
    aliases: dict[str, str] = {}
    if m.get("hover"):
        rows, aliases = extras(m)
        m = {**m, "terms": [*m["terms"], *rows]}
    _header(b, m)
    if m.get("hover"):
        b.preregister_terms([tuple(t) for t in m["terms"]], aliases)
    _intent(b, m)
    _terms_and_concepts(b, m)
    _steps(b, m)
    _verify(b, m)
    _faults(b, m)
    if m.get("intent_at_end"):
        _control_intent(b, m)
    _closing(b, m)
    return b.save(OUT_DIR, f"{m['id']}-{m['slug']}")


def main(argv: list[str]) -> int:
    ids = [p.stem.replace("_", "-").upper() for p in sorted(CONTENT_DIR.glob("*.py"))] if argv == ["--all"] else argv
    for module_id in ids:
        docx_path, md_path = render(load_module(module_id))
        print(f"{module_id}: {docx_path.name}, {md_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

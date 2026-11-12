"""Static checks for engineering leveling training module content files.

Usage: python validate.py GRC-2 [MOD-ID ...]   (or: python validate.py --all)

Checks: schema, source citations (quotes must exist in the cited file), source-label
coherence, ASCII-only text, spelling, banned words, control-ID consistency, numeric
parameters traced to citations, env-var and command consistency, and syntax of every
code block (bash -n, YAML, JSON, Python, Terraform). It cannot run the commands: live
testing still needs the lab.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from spellchecker import SpellChecker

import sources
from module_diagrams import check_diagrams
from render import CONTENT_DIR, load_module

CHECKS_DIR = Path(__file__).resolve().parent / "checks"
SOURCE_ROOTS = [Path(p) for p in os.environ.get("ENG_PUBLIC_SOURCES", "").split(os.pathsep) if p] + sources.source_dirs()
SOURCE_FOLDERS = {"NIST": "NIST-800-53", "FedRAMP": "FedRAMP"}
BANNED = ["squishy", "Ruling on record", "US-CERT", "TODO", "TBD", "lorem", *sources.banned_names()]
SKIP_KEYS = {"dot", "a", "b", "zone", "parent", "kind", "rankdir", "lab_needs", "code", "cite", "lang", "quote", "file", "start", "env", "id", "icon", "slug", "controls", "mentions", "unit_values_ok", "expect", "break_code", "restore_code"}
CONTROL_RE = re.compile(r"\b([A-Z]{2}-\d{1,2})(?:\(\d+\))?")
UNIT_RE = re.compile(r"\b(\d+)[ -]?(days?|minutes?|hours?|attempts?|characters?|years?|months?|seconds?|milliseconds?)\b", re.I)
REQUIRED = ["id", "slug", "title", "controls", "minutes", "tools", "prereq", "requirement", "mapping", "intent", "terms",
            "concepts", "steps", "verify", "glossary", "next", "lab"]
INTENT_KEYS = ["control", "feared", "scope", "question", "evidence", "sufficient", "tieoff", "tool"]


class Report:
    def __init__(self, module_id: str) -> None:
        self.module_id = module_id
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*`_]", "", text)).strip().lower()


def find_source(name: str) -> Path | None:
    for root in SOURCE_ROOTS:
        hit = next(root.rglob(sources.real_name(name)), None) if root.exists() else None
        if hit:
            return hit
    return None


def prose(node, key: str = ""):
    """Yield (path, text) for every prose string, skipping code and citation fields."""
    if isinstance(node, str):
        yield key, node
    elif isinstance(node, dict):
        for k, v in node.items():
            if k not in SKIP_KEYS:
                yield from prose(v, f"{key}.{k}" if key else k)
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            yield from prose(v, f"{key}[{i}]")


def code_blocks(m: dict):
    for s in m["steps"]:
        for blk in s["blocks"]:
            yield f"step '{s['title']}'", blk["code"], blk.get("lang", "bash"), blk.get("lines")
    for v in m["verify"]:
        yield f"test '{v['title']}'", v["code"], v.get("lang", "bash"), True
    if m.get("fault_gap"):
        yield "fault gap search", m["fault_gap"]["code"], "bash", m["fault_gap"].get("lines")
    for f in m.get("faults", []):
        yield f"fault '{f['id']}' break", f["break_code"], "bash", True
        yield f"fault '{f['id']}' restore", f["restore_code"], "bash", True
        for sig in f.get("signals", []):
            if sig.get("code"):
                yield f"fault '{f['id']}' signal", sig["code"], "bash", True


def check_design(m: dict, r: Report) -> None:
    """Optional 'design': 1 to 3 decisions, each with how, why and alternatives, 4 to 6 sentences in total."""
    design = m.get("design")
    if design is None:
        return
    if not isinstance(design, list) or not 1 <= len(design) <= 3:
        r.err("design: use a list of 1 to 3 decisions")
        return
    for i, d in enumerate(design):
        missing = [k for k in ("decision", "how", "why", "alternatives") if not d.get(k)]
        if missing:
            r.err(f"design[{i}] missing {missing}")
            continue
        sentences = sum(len(re.findall(r"[.!?](?:\s|$)", d[k])) for k in ("how", "why", "alternatives"))
        if not 4 <= sentences <= 6:
            r.err(f"design[{i}] '{d['decision']}': {sentences} sentences; use 4 to 6 in how + why + alternatives")
        alt = d["alternatives"].lower()
        if "pro" not in alt and "advantage" not in alt and "benefit" not in alt:
            r.warn(f"design[{i}]: alternatives should state pros and cons")


def check_schema(m: dict, r: Report) -> bool:
    missing = [k for k in REQUIRED if k not in m]
    if missing:
        r.err(f"missing keys: {missing}")
        return False
    if len(m["steps"]) > 5:
        r.err(f"{len(m['steps'])} steps; limit is 5 (split the module)")
    mins = m["minutes"]
    if mins["hands_on"] + mins["verify"] > 90:
        r.err(f"timed work {mins['hands_on'] + mins['verify']} min exceeds 90")
    if m.get("faults"):
        if not 1 <= len(m["faults"]) <= 3:
            r.err(f"{len(m['faults'])} faults; use 1 to 3")
        if not (m.get("faults_intro") and m.get("fault_gap")):
            r.err("faults need faults_intro and fault_gap")
        for f in m["faults"]:
            for k in ("id", "title", "simulates", "break_code", "restore_code", "wait", "signals", "tells_apart", "if_silent", "recovered"):
                if not f.get(k):
                    r.err(f"fault '{f.get('id')}' missing '{k}'")
    check_design(m, r)
    waivers = m.get("waivers", {})
    kinds = {v["kind"] for v in m["verify"]}
    needed = {"negative"} if waivers.get("verify_positive") else {"positive", "negative"}
    if not needed <= kinds and not waivers.get("verify"):
        r.err("verify needs at least one positive and one negative test")
    if waivers.get("verify") and m["verify"]:
        r.err("waivers.verify is set but the module has verify tests; remove the waiver")
    mapped = [row["control"].split()[0] for row in m["mapping"]]
    intent = [i["control"].split()[0] for i in m["intent"]]
    for c in m["controls"]:
        if c not in mapped:
            r.err(f"control {c} has no mapping row")
        if c not in intent:
            r.err(f"control {c} has no intent entry")
    for i in m["intent"]:
        for k in INTENT_KEYS:
            if not i.get(k):
                r.err(f"intent {i.get('control')} missing '{k}'")
    for s in m["steps"]:
        for k in ("title", "why", "blocks", "action", "checkpoint"):
            if not s.get(k) and not (k == "action" and waivers.get("your_turn")) and not (k == "why" and s.get("learn")):
                r.err(f"step '{s.get('title')}' missing '{k}'")
        for blk in s.get("blocks", []):
            if not blk.get("lines"):
                r.err(f"step '{s['title']}' has a code block with no line-by-line table")
    return True


def check_citations(m: dict, r: Report) -> str:
    """Verify each cite quote exists in its file; return all cited text for number tracing."""
    cited = []
    for row in m["mapping"]:
        cites = row.get("cite") or []
        if not cites:
            r.err(f"mapping {row['control']}: no citation")
        labels = [s.strip() for s in re.split(r"[;+,]", row["source"])]
        for c in cites:
            if sources.is_internal_reference(c["file"]):
                r.err(f"mapping {row['control']}: cite {c['file']} is not a framework document; cite NIST or FedRAMP")
                continue
            path = find_source(c["file"])
            if not path and not SOURCE_ROOTS:
                r.warn(f"mapping {row['control']}: quote not checked, no source folders configured")
                continue
            if not path:
                r.err(f"mapping {row['control']}: source file not found: {c['file']}")
                continue
            text = norm(path.read_text(encoding="utf-8", errors="replace"))
            if norm(sources.unalias_quote(c["quote"])) not in text:
                r.err(f"mapping {row['control']}: quote not found in {c['file']}: {c['quote'][:70]}")
            cited.append(c["quote"])
        for label in labels:
            base = next((k for k in SOURCE_FOLDERS if label.startswith(k)), None)
            if base:
                folder = SOURCE_FOLDERS[base]
                if not any(folder in str(find_source(c["file"]) or "") for c in cites):
                    r.err(f"mapping {row['control']}: source says '{label}' but no cite comes from {folder}")
            elif label:
                r.err(f"mapping {row['control']}: unknown source label '{label}' (use NIST, FedRAMP)")
    return " ".join(cited)


def check_text(m: dict, r: Report, cited: str) -> None:
    spell = SpellChecker()
    allow = set((CHECKS_DIR / "allowlist.txt").read_text(encoding="utf-8").lower().split())
    controls_ok = set(m["controls"]) | set(m.get("mentions", []))
    ok_units = {u.lower() for u in m.get("unit_values_ok", [])}
    cited_n = norm(cited)
    outputs = [(f"code:expect:{v['title']}", v["expect"]) for v in m["verify"]]
    for path, text in list(prose(m)) + [(f"code:{w}", c) for w, c, _, _ in code_blocks(m)] + outputs:
        bad = [ch for ch in text if ord(ch) > 126 or (ord(ch) < 32 and ch not in "\n\t")]
        if bad:
            r.err(f"{path}: special characters {sorted(set(bad))}: {text[:50]!r}")
        for word in BANNED:
            if word.lower() in text.lower():
                r.err(f"{path}: banned text '{word}'")
        if path.startswith("code:"):
            continue
        clean = re.sub(r"`[^`]*`", " ", text)
        for cid in CONTROL_RE.findall(clean):
            if cid not in controls_ok:
                r.err(f"{path}: control {cid} not in controls/mentions")
        for num, unit in UNIT_RE.findall(clean):
            phrase = f"{num} {unit}".lower()
            if phrase not in ok_units and not re.search(rf"\b{num}\b", cited_n):
                r.err(f"{path}: value '{num} {unit}' not traceable to a citation (add to unit_values_ok if lab-only)")
        for word in re.findall(r"[A-Za-z][a-z']+", re.sub(r"\b[A-Za-z]*[A-Z][A-Za-z]*[A-Z][A-Za-z]*\b", " ", clean)):
            w = word.lower().strip("'")
            if len(w) > 2 and w not in allow and w not in spell:
                r.warn(f"{path}: spelling '{word}'")
    body = " ".join(t for _, t in prose({k: v for k, v in m.items() if k not in ("glossary", "terms")})).lower()
    for table in ("terms", "glossary"):
        for term, _ in m[table]:
            head = re.split(r"[ (/]", term.lower())[0]
            if head not in body and term.lower() not in body:
                r.warn(f"{table}: '{term}' never used in the module text")


def contract_vars() -> set[str]:
    text = (CHECKS_DIR.parent.parent / "LAB-CONTRACT.md").read_text(encoding="utf-8")
    hit = re.search(r"^VARS:\s*(.+)$", text, re.M)
    return set(hit.group(1).split()) if hit else set()


HEREDOC = re.compile(r"(<<-?\s*(['\"]?)(\w+)\2[^\n]*\n)(?:.*?\n)?\3[ \t]*(?=\n|$)", re.S)


def check_code(m: dict, r: Report) -> None:
    for var in m["lab"].get("env", []):
        if var not in contract_vars():
            r.err(f"lab.env '{var}' is not in LAB-CONTRACT.md (add it to lab_needs instead)")
    known_cmds = set((CHECKS_DIR / "commands.txt").read_text(encoding="utf-8").split())
    defined = set(m["lab"].get("env", [])) | {"HOME", "PATH", "PWD", "USER"}
    for where, code, lang, _ in code_blocks(m):
        if lang == "bash":
            code_cmds = HEREDOC.sub(lambda h: h.group(1), code)  # file text inside a heredoc is data, not commands
            joined = re.sub(r"\\\n\s*", " ", code_cmds)
            proc = subprocess.run(["bash", "-n"], input=code.encode("utf-8"), capture_output=True)
            proc.stderr = proc.stderr.decode("utf-8", "replace")
            if proc.returncode:
                r.err(f"{where}: bash syntax: {proc.stderr.strip()[:120]}")
            for var in re.findall(r"(?:^|[\s;])(?:export\s+)?([A-Z][A-Z0-9_]*)=", joined, re.M):
                defined.add(var)
            for var in re.findall(r"\$\{?([A-Z][A-Z0-9_]*)", joined):
                if var not in defined:
                    r.err(f"{where}: ${var} used but not provided by lab env or defined earlier")
            for line in joined.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for seg in re.split(r"\|\||&&|\||;", re.sub(r"\$\([^)]*\)|'[^']*'|\"[^\"]*\"", "X", line)):
                    toks = [t for t in seg.split() if not re.match(r"^[A-Za-z_]+=", t) and t not in ("sudo", "!", "(", "{", "}", "then", "do", "done", "fi", "if", "else")]
                    if toks and toks[0] not in known_cmds and not toks[0].startswith(("$", "-", "<", ">", "X")):
                        r.err(f"{where}: command '{toks[0]}' not in checks/commands.txt (verify it, then add it)")
        elif lang == "yaml":
            try:
                list(yaml.safe_load_all(code))
            except yaml.YAMLError as e:
                r.err(f"{where}: YAML: {str(e)[:120]}")
        elif lang == "json":
            try:
                json.loads(code)
            except ValueError as e:
                r.err(f"{where}: JSON: {e}")
        elif lang == "python":
            try:
                ast.parse(code)
            except SyntaxError as e:
                r.err(f"{where}: Python: {e}")
        elif lang in ("hcl", "terraform"):
            with tempfile.TemporaryDirectory() as d:
                Path(d, "main.tf").write_text(code, encoding="utf-8")
                proc = subprocess.run(["terraform", "fmt", "-check", "-diff", "-no-color", d], capture_output=True, text=True)
                if proc.returncode:
                    (r.err if "Error" in proc.stderr + proc.stdout else r.warn)(f"{where}: terraform fmt: {(proc.stderr or proc.stdout)[:120]}")


def _sentences(text: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", text.strip()))


def check_format(m: dict, r: Report) -> None:
    """The learner-facing format: lettered steps with a lead line and expected output, and control links."""
    for n, s in enumerate(m["steps"], start=1):
        for i, blk in enumerate(s.get("blocks", [])):
            where = f"step {n} block {chr(97 + i)}"
            if re.match(r"^\d+[a-z]\.", blk.get("label", "")):
                r.err(f"{where}: the label must not start with the letter; the renderer adds it")
            if not blk.get("label") or not blk.get("intro"):
                r.err(f"{where}: needs a label and an intro that says what the learner is about to do and where to type it")
            if blk.get("lang") != "python" and not blk.get("expect"):
                r.err(f"{where}: needs expect (the output the learner should see, marked Example only)")
    for n, v in enumerate(m["verify"], start=1):
        if not v.get("lines"):
            r.err(f"test {n}: needs lines (a table that explains each command or output line of the test)")
    if not m.get("mapping"):
        return
    if not m.get("intent_at_end"):
        r.err("intent_at_end must be true: the control intent section goes at the end")
    ids = [row["control"].split(" ")[0] for row in m["mapping"]]
    for row in m["mapping"]:
        for k in ("tool", "covered"):
            if not row.get(k):
                r.err(f"mapping {row['control']}: needs '{k}' (the Tool or service column, and where this module covers it with section names)")
    described, tagged = set(), set()
    for c in m["concepts"]:
        for p in c["paras"]:
            if isinstance(p, dict) and "control" in p:
                cid = p["control"].split(":")[0].split(" ")[0]
                described.add(cid)
                if _sentences(p["text"]) > 4:
                    r.err(f"concept '{c['heading']}': control description {cid} is over 4 sentences")
        for ctl in c.get("controls", []):
            tagged.add(ctl["id"].split(" ")[0])
    for kind, items in (("step", m["steps"]), ("test", m["verify"])):
        for n, it in enumerate(items, start=1):
            for ctl in it.get("controls", []):
                cid = ctl["id"].split(" ")[0]
                tagged.add(cid)
                if not ctl.get("how"):
                    r.err(f"{kind} {n}: control {cid} needs 'how' (what the control asks, what the learner does here, what it produces)")
                elif _sentences(ctl["how"]) > 4:
                    r.err(f"{kind} {n}: control {cid} note is over 4 sentences")
    for cid in ids:
        if cid not in described:
            r.err(f"control {cid}: no full description block (a concept paragraph dict with control and text) where it is first addressed")
        if cid not in tagged:
            r.err(f"control {cid}: not tagged on any concept, step or test")
    for cid in tagged - set(ids):
        r.err(f"control tag {cid} is not in the mapping")


def validate(module_id: str) -> Report:
    r = Report(module_id)
    m = load_module(module_id)
    if check_schema(m, r):
        cited = check_citations(m, r)
        check_text(m, r, cited)
        check_code(m, r)
        check_diagrams(m, r.err, r.warn)
        check_format(m, r)
    return r


def main(argv: list[str]) -> int:
    ids = [p.stem.replace("_", "-").upper() for p in sorted(CONTENT_DIR.glob("*.py"))] if argv == ["--all"] else argv
    failed = 0
    for module_id in ids:
        r = validate(module_id)
        print(f"== {module_id}: {len(r.errors)} errors, {len(r.warnings)} warnings")
        for e in r.errors:
            print(f"  ERROR {e}")
        for w in r.warnings:
            print(f"  warn  {w}")
        failed += bool(r.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

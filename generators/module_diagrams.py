"""Learner diagrams inside a module: Graphviz rendering and checks.

A module may define `diagrams`, a list of at most MAX_DIAGRAMS dicts:
  id       short slug, unique in the module
  title    what the picture shows (the claim); starts with a capital letter
  caption  one or two plain sentences telling the learner what to look for
  reading  list of plain sentences that say the same thing in words (alt text and the .md text)
  rankdir  "LR" (default) or "TB"
  zones    list of boundaries: {"id", "label", "parent"?, "kind"?, "s"?}; kind is "boundary" (dashed, default)
           or "group" (solid, light)
  nodes    list of boxes: {"id", "title", "sub"?, "zone"?, "kind"?, "s"?, "icon"?}; icon is a name under generators/icons, such as "k8s/pod" or "brands/python"
  key      optional {icon name: what it is}; the renderer adds a "Key to the icons" row under the picture for the icons on visible nodes
  edges    list of arrows: {"a", "b", "label"?, "n"?, "kind"?, "s"?, "pad"?, "minlen"?, "beside"?}; beside puts the label next to the arrow, pad adds blank space before the label,
           minlen lengthens the arrow; n is the flow number shown as a badge
  flat     True on an edge keeps both ends on the same row or column
  kind     neutral (default), ok, bad, warn
  per_step True to draw one picture per module step; "step_notes": {1: "...", ...} adds one sentence under it.

Every node must sit inside a zone, so nothing is accidentally drawn outside the boundary. Every title, sub and
label starts with a capital letter. `s=N` on a zone, node or edge means "added in step N": for step k the renderer
draws parts with s<=k, outlines the ones with s==k in blue, and keeps later parts invisible so nothing moves.
"""

from __future__ import annotations

import re

import html
import shutil
import subprocess
from pathlib import Path

import sources

MAX_DIAGRAMS = 3
MAX_NODES = 12
MAX_WIDTH_IN = 6.3
MAX_HEIGHT_IN = 5.2
DPI = 200
FONT = "Segoe UI,Arial,sans-serif"
STEP_ACCENT = "#1565C0"
IMG_DIR = Path(__file__).resolve().parent.parent / "modules" / "img"
ICON_DIR = Path(__file__).resolve().parent / "icons"
ICON_PX = 44
ZONE_ICON_PX = 34
KEY_FONT = "C:/Windows/Fonts/segoeui.ttf"
KEY_FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
REQUIRED_KEYS = ("id", "title", "caption", "reading", "nodes", "edges", "zones")
DOT_CANDIDATES = (
    "dot",
    "C:/Program Files/Graphviz/bin/dot.exe",
    "/usr/bin/dot",
    "/opt/homebrew/bin/dot",
)
# kind -> (fill, line, header text)
KINDS = {
    "neutral": ("#F4F6F8", "#455A64", "#263238"),
    "ok": ("#E8F5E9", "#2E7D32", "#1B5E20"),
    "bad": ("#FFEBEE", "#C62828", "#8E1B1B"),
    "warn": ("#FFF8E1", "#B26A00", "#7A4A00"),
}
ZONE_STYLE = {
    "boundary": ('"dashed,rounded"', "#455A64", "#FFFFFF"),
    "group": ('"rounded,filled"', "#B0BEC5", "#F8FAFB"),
}


def find_dot() -> str | None:
    for candidate in DOT_CANDIDATES:
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    return None


def _run_dot(source: str, fmt: str, out: Path | None = None) -> subprocess.CompletedProcess:
    dot = find_dot()
    if dot is None:
        raise FileNotFoundError("Graphviz dot not found")
    args = [dot, f"-T{fmt}"]
    if fmt == "png":
        args += [f"-Gdpi={DPI}"]
    if out is not None:
        args += ["-o", str(out)]
    return subprocess.run(args, input=source.encode("ascii"), capture_output=True, check=False)


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _icon_path(name: str) -> str | None:
    """Absolute forward-slash path of icons/<name>.png (for example k8s/pod), or None if missing."""
    path = ICON_DIR / f"{name}.png"
    return path.as_posix() if path.is_file() else None


def _node_label(node: dict, text_color: str) -> str:
    title = html.escape(node["title"])
    rows = ""
    icon = _icon_path(node["icon"]) if node.get("icon") else None
    if icon:
        rows += f'<TR><TD FIXEDSIZE="TRUE" WIDTH="{ICON_PX}" HEIGHT="{ICON_PX}"><IMG SRC="{icon}" SCALE="TRUE"/></TD></TR>'
    rows += f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="15" COLOR="{text_color}"><B>{title}</B></FONT></TD></TR>'
    if node.get("sub"):
        sub = html.escape(node["sub"])
        rows += f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="12" COLOR="#546E7A">{sub}</FONT></TD></TR>'
    return f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">{rows}</TABLE>>'


def _visible(part: dict, k: int | None) -> bool:
    if k is None:
        return "until" not in part
    return part.get("s", 0) <= k and k < part.get("until", 10**6)


def _is_new(part: dict, k: int | None) -> bool:
    return k is not None and part.get("s", 0) == k and k > 0


def _node_line(node: dict, k: int | None) -> str:
    fill, line, text = KINDS[node.get("kind", "neutral")]
    if not _visible(node, k):
        return f'  {node["id"]} [label={_node_label(node, text)}, style=invis];'
    pen = 1.6
    if _is_new(node, k):
        line, pen = STEP_ACCENT, 4.0
    return (
        f'  {node["id"]} [label={_node_label(node, text)}, fillcolor="{fill}", color="{line}", penwidth={pen}];'
    )


def _edge_label(text: str, color: str, pad: int = 0, trailing: bool = False) -> str:
    """HTML label on a white box, so an arrow or a boundary line never runs through the words."""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe + "&#160;" * pad if trailing else "&#160;" * pad + safe
    return (
        f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">'
        f'<TR><TD BGCOLOR="white"><FONT COLOR="{color}">{safe}</FONT></TD></TR></TABLE>>'
    )


def _edge_line(edge: dict, k: int | None) -> str:
    kind = edge.get("kind", "neutral")
    _, line, text = KINDS[kind]
    label = edge.get("label", "")
    if edge.get("n"):
        label = f'{edge["n"]}  {label}'.strip()
    flat = ", constraint=false" if edge.get("flat") else ""
    flat += f", minlen={edge['minlen']}" if edge.get("minlen") else ""
    attr = "xlabel" if edge.get("beside") else "label"
    lab = f", {attr}={_edge_label(label, text, edge.get('pad', 0), bool(edge.get('beside')))}" if label else ""
    if not _visible(edge, k):
        # Same attributes as a visible edge, so the layout does not shift between steps.
        return f'  {edge["a"]} -> {edge["b"]} [style=invis{lab}{flat}];'
    pen = 4.0 if _is_new(edge, k) else 2.0
    color = line
    style = "dashed" if kind == "bad" else "solid"
    return f'  {edge["a"]} -> {edge["b"]} [color="{color}", fontcolor="{text}", penwidth={pen}, style={style}{lab}{flat}];'


def _zone_label(zone: dict) -> str:
    """Zone title as a quoted string, or an HTML label with the zone icon in front of it."""
    icon = _icon_path(zone["icon"]) if zone.get("icon") else None
    if not icon:
        return _q(zone["label"])
    text = html.escape(zone["label"])
    return (
        f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2"><TR>'
        f'<TD FIXEDSIZE="TRUE" WIDTH="{ZONE_ICON_PX}" HEIGHT="{ZONE_ICON_PX}"><IMG SRC="{icon}" SCALE="TRUE"/></TD>'
        f'<TD><FONT POINT-SIZE="13" COLOR="#37474F">{text}</FONT></TD></TR></TABLE>>'
    )


def _zone_block(zone: dict, zones: list[dict], nodes: list[dict], k: int | None, indent: int = 1) -> list[str]:
    pad = "  " * indent
    style, line, fill = ZONE_STYLE[zone.get("kind", "boundary")]
    if not _visible(zone, k):
        out = [f'{pad}subgraph cluster_{zone["id"]} {{ style=invis; label={_zone_label(zone)}; labeljust={zone.get("labeljust", "l")}; labelloc={zone.get("labelloc", "t")}; fontsize=13; margin=18;']
    else:
        out = [
            f'{pad}subgraph cluster_{zone["id"]} {{',
            f'{pad}  label={_zone_label(zone)}; labeljust={zone.get('labeljust', 'l')}; labelloc={zone.get('labelloc', 't')}; fontsize=13; fontcolor="#37474F";',
            f'{pad}  style={style}; color="{line}"; fillcolor="{fill}"; penwidth=1.6; margin=18;',
        ]
    for child in (z for z in zones if z.get("parent") == zone["id"]):
        out += _zone_block(child, zones, nodes, k, indent + 1)
    for node in (n for n in nodes if n.get("zone") == zone["id"]):
        out.append("  " * (indent + 1) + _node_line(node, k).strip())
    out.append(f"{pad}}}")
    return out


def full_source(diagram: dict, k: int | None = None) -> str:
    """DOT source for the finished picture (k=None) or for module step k."""
    zones, nodes = diagram["zones"], diagram["nodes"]
    lines = [
        "digraph G {",
        f'  graph [rankdir={diagram.get("rankdir", "LR")}, bgcolor="white", pad=0.3, nodesep=0.6, ranksep=1.0, '
        f'fontname="{FONT}", forcelabels=true, splines=true];',
        f'  node [shape=box, style="rounded,filled", fontname="{FONT}", margin="0.25,0.14", width=1.6, height=0.7];',
        f'  edge [fontname="{FONT}", fontsize=13, arrowsize=1.0];',
    ]
    for top in (z for z in zones if not z.get("parent")):
        lines += _zone_block(top, zones, nodes, k)
    lines += [_edge_line(e, k) for e in diagram["edges"]]
    lines.append("}")
    return "\n".join(lines) + "\n"


def _step_diagram(m: dict) -> dict | None:
    return next((d for d in (m.get("diagrams") or []) if d.get("per_step")), None)


def _width_for(png: Path) -> float:
    """Fit the image into the page, keeping its shape."""
    from PIL import Image

    with Image.open(png) as im:
        w, h = im.size
    return min(MAX_WIDTH_IN, MAX_HEIGHT_IN * w / h)


def _draw(diagram: dict, k: int | None, png: Path, label: str) -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    result = _run_dot(full_source(diagram, k), "png", png)
    if result.returncode != 0:
        raise RuntimeError(f"{label}: {result.stderr.decode(errors='replace')[:200]}")
    _append_key(diagram, k, png)


def _key_entries(diagram: dict, k: int | None) -> list[tuple[Path, str]]:
    """One (icon file, meaning) pair for each distinct icon on a visible node, in node order."""
    meanings = diagram.get("key") or {}
    seen: list[str] = []
    entries: list[tuple[Path, str]] = []
    for node in [*diagram["zones"], *diagram["nodes"]]:
        name = node.get("icon")
        if name and name in meanings and name not in seen and _visible(node, k) and _icon_path(name):
            seen.append(name)
            entries.append((ICON_DIR / f"{name}.png", meanings[name]))
    return entries


def _append_key(diagram: dict, k: int | None, png: Path) -> None:
    """Add a one-row-per-icon key under the picture so the learner knows what each icon is."""
    entries = _key_entries(diagram, k)
    if not entries:
        return
    from PIL import Image, ImageDraw, ImageFont

    icon_px, gap, pad = 60, 22, 40
    with Image.open(png) as base:
        base = base.convert("RGB")
    probe = ImageDraw.Draw(base)
    row_h = icon_px + 20
    for size in range(38, 27, -2):
        font = ImageFont.truetype(KEY_FONT, size)
        cell_w = [icon_px + gap + int(probe.textlength(text, font=font)) + 50 for _, text in entries]
        if pad + sum(cell_w) <= base.width - pad:
            break
    rows: list[list[int]] = [[]]
    used = pad
    for i, w in enumerate(cell_w):
        if used + w > base.width - pad and rows[-1]:
            rows.append([])
            used = pad
        rows[-1].append(i)
        used += w
    header_h = 64
    height = base.height + header_h + row_h * len(rows) + pad
    out = Image.new("RGB", (base.width, height), "white")
    out.paste(base, (0, 0))
    draw = ImageDraw.Draw(out)
    y = base.height
    draw.text((pad, y + 6), "Key to the icons", font=ImageFont.truetype(KEY_FONT_BOLD, 38), fill="#37474F")
    y += header_h
    for row in rows:
        x = pad
        for i in row:
            icon_file, text = entries[i]
            with Image.open(icon_file) as raw:
                icon = raw.convert("RGBA").resize((icon_px, icon_px))
            out.paste(icon, (x, y), icon)
            draw.text((x + icon_px + gap, y + 8), text, font=font, fill="#263238")
            x += cell_w[i]
        y += row_h
    out.save(png)


def render_step_diagram(b, m: dict, n: int) -> None:
    """Add the picture for module step n (what this step is about to build) if the module has one."""
    diagram = _step_diagram(m)
    if diagram is None or n in diagram.get("skip_steps", ()):
        return
    png = IMG_DIR / f"{m['id']}-step-{n}.png"
    _draw(diagram, n, png, f"{m['id']} step {n} diagram")
    b.para("What this step adds (thick lines and outlines are new):")
    b.doc.paragraphs[-1].paragraph_format.keep_with_next = True
    b.image(png, f"{diagram['title']}, after step {n}", "", width_in=_width_for(png))
    note = (diagram.get("step_notes") or {}).get(n)
    if note:
        b.bullet(note)


def render_concept_diagram(b, m: dict, diagram_id: str) -> None:
    """Draw a diagram that belongs to one concept section (a diagram with a `concept` key) at that spot."""
    for index, diagram in enumerate(m.get("diagrams") or [], start=1):
        if diagram["id"] != diagram_id:
            continue
        png = IMG_DIR / f"{m['id']}-diagram-{index}.png"
        _draw(diagram, None, png, f"{m['id']} diagram {diagram['id']}")
        b.para("What the picture shows:")
        b.prose(diagram["caption"])
        b.image(png, diagram["title"], "", width_in=_width_for(png))
        for line in diagram["reading"]:
            b.lead_bullet(line)


def render_diagrams(b, m: dict) -> None:
    """Add every finished-picture diagram of module `m` to the document builder `b`."""
    diagrams = m.get("diagrams") or []
    if not any(not d.get("concept") for d in diagrams):
        return
    b.h2("How it fits together")
    for index, diagram in enumerate(diagrams, start=1):
        if diagram.get("concept"):
            continue
        b.h3(diagram["title"])
        b.prose(re.sub(r"^This is the lab \(test\) setup[.:]\s+", "Lab (test) setup: ", diagram["caption"]))
        if diagram.get("why_built"):
            b.para("How the lab is set up, and why:")
            b.prose(diagram["why_built"])
        png = IMG_DIR / f"{m['id']}-diagram-{index}.png"
        _draw(diagram, None, png, f"{m['id']} diagram {diagram['id']}")
        b.image(png, diagram["title"], "", width_in=_width_for(png))
        if diagram.get("legend"):
            b.hover_names("Boxes in this picture (in Word, hover over a name to read what it is):", diagram["legend"])
        for line in diagram["reading"]:
            b.lead_bullet(line)
        if diagram.get("setup"):
            b.para("Where each part runs, and why:")
            b.table(["Part", "Where it runs", "Why it is built this way"], [list(r) for r in diagram["setup"]])


def _capital(text: str) -> bool:
    return bool(text) and (text[0].isupper() or text[0].isdigit())


def _texts(d: dict) -> list[tuple[str, str]]:
    out = [("title", d["title"])]
    out += [("zone label", z["label"]) for z in d["zones"]]
    for n in d["nodes"]:
        out.append(("node title", n["title"]))
        if n.get("sub"):
            out.append(("node sub", n["sub"]))
    out += [("edge label", e["label"]) for e in d["edges"] if e.get("label")]
    return out


def _check_structure(d: dict, steps: int, err) -> None:
    did = d["id"]
    zone_ids = {z["id"] for z in d["zones"]}
    node_ids = {n["id"] for n in d["nodes"]}
    if len(node_ids) != len(d["nodes"]):
        err(f"diagram {did}: duplicate node id")
    for n in d["nodes"]:
        if n.get("zone") not in zone_ids:
            err(f"diagram {did}: node {n['id']} is not inside a zone (it would be drawn outside the boundary)")
        if n.get("kind", "neutral") not in KINDS:
            err(f"diagram {did}: node {n['id']} has unknown kind")
    for z in d["zones"]:
        if z.get("parent") and z["parent"] not in zone_ids:
            err(f"diagram {did}: zone {z['id']} has unknown parent")
    for e in d["edges"]:
        if e["a"] not in node_ids or e["b"] not in node_ids:
            err(f"diagram {did}: edge {e['a']}->{e['b']} names an unknown node")
    for kind, text in _texts(d):
        if not _capital(text):
            err(f"diagram {did}: {kind} '{text}' must start with a capital letter")
    if d.get("per_step"):
        notes = d.get("step_notes") or {}
        for part in [*d["zones"], *d["nodes"], *d["edges"]]:
            if part.get("s", 0) > steps:
                err(f"diagram {did}: s={part['s']} but the module has {steps} steps")
        missing = [n for n in range(1, steps + 1) if n not in notes and n not in d.get("skip_steps", ())]
        if missing:
            err(f"diagram {did}: step_notes missing for steps {missing}")
        for text in notes.values():
            if not _capital(text) or not text.rstrip().endswith("."):
                err(f"diagram {did}: step note '{text}' must be a capitalized sentence ending in a period")


def check_diagrams(m: dict, err, warn) -> None:
    """Report problems with module `m`'s diagrams through the err and warn callbacks."""
    diagrams = m.get("diagrams") or []
    if len(diagrams) > MAX_DIAGRAMS:
        err(f"diagrams: {len(diagrams)} given, at most {MAX_DIAGRAMS}")
    seen: set[str] = set()
    banned = [x.lower() for x in sources.banned_names() if x.strip()]
    for d in diagrams:
        missing = [k for k in REQUIRED_KEYS if k not in d]
        if missing:
            err(f"diagram {d.get('id', '?')}: missing {missing}")
            continue
        if d["id"] in seen:
            err(f"diagram {d['id']}: duplicate id")
        seen.add(d["id"])
        text = " ".join([d["title"], d["caption"], *d["reading"], *(t for _, t in _texts(d))])
        if not text.isascii():
            err(f"diagram {d['id']}: non-ASCII text")
            continue
        hit = [x for x in banned if x in text.lower()]
        if hit:
            err(f"diagram {d['id']}: banned words {hit}")
        if not d["reading"]:
            err(f"diagram {d['id']}: 'reading' is empty")
        if len(d["nodes"]) > MAX_NODES:
            err(f"diagram {d['id']}: {len(d['nodes'])} nodes, at most {MAX_NODES}")
        _check_structure(d, len(m.get("steps", [])), err)
        _check_render(d, err, warn)


def _check_render(d: dict, err, warn) -> None:
    if find_dot() is None:
        warn(f"diagram {d['id']}: Graphviz not installed, drawing not checked")
        return
    result = _run_dot(full_source(d), "plain")
    if result.returncode != 0:
        err(f"diagram {d['id']}: Graphviz error: {result.stderr.decode(errors='replace')[:160]}")
    elif result.stderr.strip():
        warn(f"diagram {d['id']}: Graphviz warning: {result.stderr.decode(errors='replace')[:120]}")

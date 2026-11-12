"""Grid diagram engine for the reference cards: one layout, drawn as ASCII and as a PNG.

A card layout is a list of entries on a fixed grid of COLS columns:
  ("frame", element_id)                       open a boundary (titled with the element's name)
  ("end",)                                    close the innermost boundary
  ("row", [cell, ...])                        one row of cells
A cell is ("box", element_id, col, span) or ("arrow", element_id, col, direction),
direction being "down" or "both". Box text is element["text"] if present, else its name.
An arrow shows element["text"] beside its shaft, if present.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path

COLS = 3
CELL_W = 22
GAP = 2
FRAME_PAD = 2
CHAR_W_IN = 0.1
SHAFT_OFF = 4
ARROW_ROOM = CELL_W - SHAFT_OFF - 2
CHAR_H_IN = 0.19


@dataclass(frozen=True)
class Prim:
    kind: str  # "frame", "box" or "arrow"
    x: int
    y: int
    w: int
    h: int
    lines: tuple[str, ...] = ()
    direction: str = "down"
    depth: int = 0


@dataclass
class Geometry:
    width: int
    height: int
    prims: list[Prim] = field(default_factory=list)


def _label(elements: dict[str, dict], element_id: str) -> str:
    element = elements[element_id]
    return element.get("text") or element["name"]


def _max_depth(layout: list[tuple]) -> int:
    depth = best = 0
    for entry in layout:
        if entry[0] == "frame":
            depth += 1
            best = max(best, depth)
        elif entry[0] == "end":
            depth -= 1
    return best


def _col_x(base: int, col: int) -> int:
    return base + col * (CELL_W + GAP)


def _span_w(span: int) -> int:
    return span * CELL_W + (span - 1) * GAP


def _wrap_arrow(label: str) -> list[str]:
    return textwrap.wrap(label, ARROW_ROOM, break_long_words=False)


def _cell_height(cell: tuple, elements: dict[str, dict]) -> int:
    if cell[0] == "box":
        lines = textwrap.wrap(_label(elements, cell[1]), _span_w(cell[3]) - 4)
        return len(lines) + 2
    label = elements[cell[1]].get("text", "")
    return max(3, len(_wrap_arrow(label)) + 1) if label else 3


def _place_cell(cell: tuple, elements: dict[str, dict], base: int, y: int, row_h: int) -> Prim:
    if cell[0] == "box":
        _, element_id, col, span = cell
        width = _span_w(span)
        lines = tuple(textwrap.wrap(_label(elements, element_id), width - 4))
        return Prim("box", _col_x(base, col), y, width, row_h, lines)
    _, element_id, col, direction = cell
    label = elements[element_id].get("text", "")
    lines = tuple(_wrap_arrow(label)) if label else ()
    return Prim("arrow", _col_x(base, col), y, CELL_W, _cell_height(cell, elements), lines, direction)


def build_geometry(layout: list[tuple], elements: dict[str, dict]) -> Geometry:
    depth_max = _max_depth(layout)
    base = FRAME_PAD * depth_max
    width = COLS * CELL_W + (COLS - 1) * GAP + 2 * base
    prims: list[Prim] = []
    open_frames: list[tuple[str, int, int]] = []
    y = 0
    for entry in layout:
        if entry[0] == "frame":
            open_frames.append((entry[1], y, len(open_frames) + 1))
            y += 1
        elif entry[0] == "end":
            element_id, top, depth = open_frames.pop()
            inset = FRAME_PAD * (depth - 1)
            lines = (elements[element_id]["name"],)
            prims.append(Prim("frame", inset, top, width - 2 * inset, y + 1 - top, lines, depth=depth))
            y += 1
        else:
            cells = entry[1]
            row_h = max(_cell_height(c, elements) for c in cells)
            box_h = max([_cell_height(c, elements) for c in cells if c[0] == "box"] or [0])
            for cell in cells:
                height = box_h if cell[0] == "box" else _cell_height(cell, elements)
                prims.append(_place_cell(cell, elements, base, y, height))
            y += row_h
    prims.sort(key=lambda p: (0, p.depth) if p.kind == "frame" else (1, 0))
    return Geometry(width, y, prims)


def _paint_frame(grid: list[list[str]], p: Prim) -> None:
    for x in range(p.x, p.x + p.w):
        grid[p.y][x] = grid[p.y + p.h - 1][x] = "-"
    for y in range(p.y, p.y + p.h):
        grid[y][p.x] = grid[y][p.x + p.w - 1] = "|"
    for y in (p.y, p.y + p.h - 1):
        grid[y][p.x] = grid[y][p.x + p.w - 1] = "+"
    title = f" {p.lines[0]} "
    for i, ch in enumerate(title):
        grid[p.y][p.x + 3 + i] = ch


def _paint_box(grid: list[list[str]], p: Prim) -> None:
    for y in range(p.y, p.y + p.h):
        for x in range(p.x, p.x + p.w):
            grid[y][x] = " "
    _paint_frame(grid, Prim("frame", p.x, p.y, p.w, p.h, ("",)))
    for x in range(p.x + 1, p.x + p.w - 1):
        grid[p.y][x] = "-"
    for i, line in enumerate(p.lines):
        start = p.x + (p.w - len(line)) // 2
        for j, ch in enumerate(line):
            grid[p.y + 1 + i][start + j] = ch


def _paint_arrow(grid: list[list[str]], p: Prim) -> None:
    shaft = p.x + SHAFT_OFF
    for y in range(p.y, p.y + p.h):
        grid[y][shaft] = "|"
    grid[p.y + p.h - 1][shaft] = "v"
    if p.direction == "both":
        grid[p.y][shaft] = "^"
    for i, line in enumerate(p.lines):
        for j, ch in enumerate(line):
            grid[p.y + i][shaft + 2 + j] = ch


def to_ascii(geom: Geometry) -> str:
    grid = [[" "] * geom.width for _ in range(geom.height)]
    painters = {"frame": _paint_frame, "box": _paint_box, "arrow": _paint_arrow}
    for p in geom.prims:
        painters[p.kind](grid, p)
    return "\n".join("".join(row).rstrip() for row in grid)


def to_png(geom: Geometry, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Rectangle

    ink, fills = "#1F3A5F", {1: "#EEF2F7", 2: "#DCE6F1"}
    fig = plt.figure(figsize=(geom.width * CHAR_W_IN, geom.height * CHAR_H_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, geom.width)
    ax.set_ylim(geom.height, 0)
    ax.axis("off")
    font = {"family": "DejaVu Sans Mono", "size": 12, "color": "#111111"}
    for p in geom.prims:
        if p.kind in ("frame", "box"):
            fill = fills.get(p.depth, "#FFFFFF") if p.kind == "frame" else "#FFFFFF"
            ax.add_patch(Rectangle((p.x + 0.5, p.y + 0.5), p.w - 1, p.h - 1, fc=fill, ec=ink, lw=1.4))
        if p.kind == "frame":
            ax.text(p.x + 2.5, p.y + 0.5, f" {p.lines[0]} ", va="center", ha="left", weight="bold",
                    bbox={"fc": fills.get(p.depth, "#FFFFFF"), "ec": "none", "pad": 0.5}, **font)
        elif p.kind == "box":
            for i, line in enumerate(p.lines):
                ax.text(p.x + p.w / 2, p.y + 1.5 + i, line, va="center", ha="center", **font)
        else:
            shaft = p.x + SHAFT_OFF + 0.5
            style = "<|-|>" if p.direction == "both" else "-|>"
            ax.add_patch(FancyArrowPatch((shaft, p.y), (shaft, p.y + p.h), arrowstyle=style,
                                         mutation_scale=14, color=ink, lw=1.4, shrinkA=0, shrinkB=0))
            for i, line in enumerate(p.lines):
                ax.text(shaft + 1.5, p.y + 0.5 + i, line, va="center", ha="left", **font)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)

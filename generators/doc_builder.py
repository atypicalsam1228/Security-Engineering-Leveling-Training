"""Shared document builder for the engineering leveling training modules.

Writes a .docx and a parallel .md from the same calls, and counts callouts so
each generator can print the cross-reference summary the format requires.
"""

from __future__ import annotations

import re
import sys
from xml.sax.saxutils import quoteattr
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.stdout.reconfigure(encoding="utf-8")

CODE_SHADE = "F3F3F3"
OUTPUT_SHADE = "F0F8F0"


def _hover_link(paragraph, text: str, anchor: str, tip: str, size: int, italic: bool) -> None:
    """A link to a bookmark in this document. Word shows `tip` when the reader hovers over it."""
    link = OxmlElement("w:hyperlink")
    link.set(qn("w:anchor"), anchor)
    link.set(qn("w:tooltip"), tip)
    link.set(qn("w:history"), "1")
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    for tag, val in (("w:color", "1F4E79"), ("w:u", "dotted"), ("w:sz", str(size * 2))):
        el = OxmlElement(tag)
        el.set(qn("w:val"), val)
        props.append(el)
    if italic:
        props.append(OxmlElement("w:i"))
    run.append(props)
    label = OxmlElement("w:t")
    label.text = text
    label.set(qn("xml:space"), "preserve")
    run.append(label)
    link.append(run)
    paragraph._p.append(link)


def _add_runs(paragraph, text: str, size: int = 11, italic: bool = False, color: RGBColor | None = None, linker=None) -> None:
    """Add text to a paragraph; segments between backticks become monospace runs (no backticks shown).

    `linker(segment)` may split a plain segment into (text, hover) pieces; a piece with hover=(anchor, tip) becomes a hover link.
    """
    parts = text.split("`") if text.count("`") % 2 == 0 else [text]
    for index, segment in enumerate(parts):
        if not segment:
            continue
        pieces = linker(segment) if linker and index % 2 == 0 else [(segment, None)]
        for piece, hover in pieces:
            if hover:
                _hover_link(paragraph, piece, hover[0], hover[1], size, italic)
                continue
            run = paragraph.add_run(piece)
            run.font.size = Pt(size)
            run.font.italic = italic
            if color is not None:
                run.font.color.rgb = color
            if index % 2 == 1:
                run.font.name = "Consolas"


def _set_cell(cell, text: str, size: int) -> None:
    """Fill a table cell from text, rendering backtick segments as code."""
    cell.text = ""
    _add_runs(cell.paragraphs[0], text, size)


def _md_cell(text: str) -> str:
    """Markdown table cell: one line, with pipes escaped so they do not split the row."""
    return text.replace("\n", " ").replace("|", "\\|")


TEXT_WIDTH_IN = 6.0  # page 8.5 in less 1.25 in margins each side


def _repeat_header(table) -> None:
    """Repeat the first row at the top of each page and never split a row across pages."""
    for index, row in enumerate(table.rows):
        properties = row._tr.get_or_add_trPr()
        properties.append(OxmlElement("w:cantSplit"))
        if index == 0:
            properties.append(OxmlElement("w:tblHeader"))


def _shade(paragraph, color: str) -> None:
    props = paragraph._element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "solid")
    shd.set(qn("w:color"), color)
    shd.set(qn("w:fill"), color)
    # The schema puts shd before tabs, spacing, indentation, justification and run properties.
    later = {qn(f"w:{t}") for t in ("tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange")}
    anchor = next((child for child in props if child.tag in later), None)
    if anchor is None:
        props.append(shd)
    else:
        anchor.addprevious(shd)


class DocBuilder:
    def __init__(self) -> None:
        self.doc = Document()
        self.md_lines: list[str] = []
        self.counts: Counter[str] = Counter()
        self._hover: dict[str, tuple[str, str]] = {}
        self._hover_pattern: re.Pattern | None = None
        self._linked: set[str] = set()
        self._bookmark_id = 0
        self._style_headings()
        zoom = self.doc.settings.element.find(qn("w:zoom"))
        if zoom is not None and zoom.get(qn("w:percent")) is None:
            zoom.set(qn("w:percent"), "100")

    def _style_headings(self) -> None:
        self.doc.styles["Title"].font.name = "Times New Roman"
        self.doc.styles["Title"].font.size = Pt(24)
        self.doc.styles["Title"].font.color.rgb = RGBColor(0, 51, 102)
        for level, size, color in (
            ("Heading 1", 18, RGBColor(0, 51, 102)),
            ("Heading 2", 14, RGBColor(0, 80, 140)),
            ("Heading 3", 12, RGBColor(0, 100, 160)),
        ):
            style = self.doc.styles[level]
            style.font.name = "Times New Roman"
            style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
            for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                style.element.rPr.rFonts.attrib.pop(qn(attr), None)
            style.font.size = Pt(size)
            style.font.color.rgb = color

    def _link(self, segment: str) -> list[tuple[str, tuple[str, str] | None]]:
        """Split a plain text segment so the first use of each registered term becomes a hover link."""
        if not self._hover_pattern:
            return [(segment, None)]
        pieces, pos = [], 0
        for match in self._hover_pattern.finditer(segment):
            key = match.group(1).lower()
            if key in self._linked:
                continue
            self._linked.add(key)
            if match.start() > pos:
                pieces.append((segment[pos:match.start()], None))
            pieces.append((match.group(0), self._hover[key]))
            pos = match.end()
        if pos < len(segment):
            pieces.append((segment[pos:], None))
        return pieces or [(segment, None)]

    def preregister_terms(self, rows: list[tuple[str, str]], aliases: dict[str, str] | None = None) -> None:
        """Register hover terms before the body is written, so a term first used before the table still links.

        `aliases` maps another spelling (such as "policies") to a registered term, so both link to the same entry.
        """
        for term, meaning in rows:
            self._hover[term.lower()] = ("term_" + re.sub(r"[^A-Za-z0-9]", "_", term.lower()), meaning[:250])
        for spelling, term in (aliases or {}).items():
            if term.lower() in self._hover:
                self._hover[spelling.lower()] = self._hover[term.lower()]
        keys = sorted(self._hover, key=len, reverse=True)
        self._hover_pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(k) for k in keys) + r")(?:s|es)?(?![A-Za-z0-9])", re.I)

    def terms_table(self, rows: list[tuple[str, str]], hover: bool = True, side_by_side: bool = False) -> None:
        """The quick-lookup term table. Each term gets a bookmark, and (when hover) later first uses link back to it.

        With `side_by_side` the rows fill two Term/Meaning pairs per line, down the left pair then down the right pair.
        """
        pairs = 2 if side_by_side else 1
        half = -(-len(rows) // pairs)
        table = self.doc.add_table(rows=1, cols=2 * pairs)
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        if side_by_side:
            table.autofit = False
        widths = (Inches(1.1), Inches(1.9)) * pairs
        for index in range(2 * pairs):
            cell = table.rows[0].cells[index]
            cell.text = ("Term", "Plain meaning")[index % 2]
            cell.paragraphs[0].paragraph_format.keep_with_next = True
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.size = Pt(10)
        for line in range(half):
            row = table.add_row()
            for pair in range(pairs):
                position = line + pair * half
                if position >= len(rows):
                    continue
                self._fill_term_cells(row.cells[2 * pair], row.cells[2 * pair + 1], rows[position], hover)
        if side_by_side:
            for row in table.rows:
                for cell, width in zip(row.cells, widths):
                    cell.width = width
        if hover and self._hover:
            keys = sorted(self._hover, key=len, reverse=True)
            self._hover_pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(k) for k in keys) + r")(?:s|es)?(?![A-Za-z0-9])", re.I)
        self.doc.add_paragraph("")
        self._md("| Term | Plain meaning |")
        self._md("| --- | --- |")
        for term, meaning in rows:
            self._md(f"| {_md_cell(term)} | {_md_cell(meaning)} |")
        self._md()

    def _fill_term_cells(self, term_cell, meaning_cell, row: tuple[str, str], hover: bool) -> None:
        """One term and its meaning in two cells; the term cell becomes the bookmark hover links jump to."""
        term, meaning = row
        _set_cell(term_cell, term, 10)
        for run in term_cell.paragraphs[0].runs:
            run.bold = True
        _set_cell(meaning_cell, meaning, 10)
        if hover:
            self._bookmark_id += 1
            name = "term_" + re.sub(r"[^A-Za-z0-9]", "_", term.lower())
            para = term_cell.paragraphs[0]._p
            start = OxmlElement("w:bookmarkStart")
            start.set(qn("w:id"), str(self._bookmark_id))
            start.set(qn("w:name"), name)
            end = OxmlElement("w:bookmarkEnd")
            end.set(qn("w:id"), str(self._bookmark_id))
            para.insert(1 if para.pPr is not None else 0, start)
            para.append(end)
            self._hover[term.lower()] = (name, meaning[:250])

    def _md(self, text: str = "") -> None:
        if text and not text.startswith("- ") and self.md_lines and self.md_lines[-1].startswith("- "):
            self.md_lines.append("")
        self.md_lines.append(text)

    def title(self, text: str) -> None:
        self.doc.add_heading(text, level=0)
        self._md(f"# {text}\n")

    def h1(self, text: str, collapsed: bool = False) -> None:
        """A section heading. collapsed=True starts the section folded in Word and in a Markdown viewer."""
        self._close_details()
        heading = self.doc.add_heading(text, level=1)
        if collapsed:
            heading._p.get_or_add_pPr().append(parse_xml('<w15:collapsed xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"/>'))
            self._md(f"<details>\n<summary><strong>{text}</strong></summary>\n")
            self._details_open = True
        else:
            self._md(f"## {text}\n")

    def _close_details(self) -> None:
        if getattr(self, "_details_open", False):
            self._md("</details>\n")
            self._details_open = False

    def h2(self, text: str, tag: str = "") -> None:
        """A second-level heading. `tag` is a control label shown highlighted after the title."""
        heading = self.doc.add_heading(text, level=2)
        if tag:
            heading.add_run(" (" + tag + ")")
        self._md(f"### {text} ({tag})\n" if tag else f"### {text}\n")

    def control_notes(self, notes: list[tuple[str, str]]) -> None:
        """How a step or test meets each control it addresses: a bold lead line, then one bullet per control."""
        if not notes:
            return
        lead = self.doc.add_paragraph()
        lead.add_run("How this meets the control" + ("s" if len(notes) > 1 else "")).bold = True
        lead.paragraph_format.keep_with_next = True
        self._md(f"**How this meets the control{'s' if len(notes) > 1 else ''}**\n")
        for control, how in notes:
            paragraph = self.doc.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.add_run(control.split(" ")[0] + ": ").bold = True
            _add_runs(paragraph, how, linker=self._link)
            self._md(f"- **{control.split(' ')[0]}:** {how}")
        self._md("")

    def prose(self, text: str) -> None:
        """Facts, not paragraphs: one bullet per sentence (a single sentence stays a plain line)."""
        parts = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Za-z`])", text.strip()) if p]
        if len(parts) < 2:
            self.para(text)
            return
        for part in parts:
            self.bullet(part)
        self._md("")

    def h3(self, text: str) -> None:
        self.doc.add_heading(text, level=3)
        self._md(f"#### {text}\n")

    def para(self, text: str, italic: bool = False) -> None:
        paragraph = self.doc.add_paragraph()
        _add_runs(paragraph, text, italic=italic, linker=self._link)
        if text.rstrip().endswith(":"):
            paragraph.paragraph_format.keep_with_next = True  # a lead-in line stays with what it introduces
        self._md(f"*{text}*\n" if italic else f"{text}\n")

    def bullet(self, text: str) -> None:
        paragraph = self.doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        _add_runs(paragraph, text, linker=self._link)
        self._md(f"- {text}")

    def _new_number_list(self, paragraph) -> None:
        """Point this paragraph at a fresh list so numbering restarts at 1."""
        numbering = self.doc.part.numbering_part.numbering_definitions._numbering
        style_num = self.doc.styles["List Number"].element.pPr.numPr.numId.val
        abstract = next(n for n in numbering.num_lst if n.numId == style_num).abstractNumId.val
        num = numbering.add_num(abstract)
        num.add_lvlOverride(ilvl=0).add_startOverride(1)
        pr = paragraph._p.get_or_add_pPr()
        num_pr = pr.get_or_add_numPr()
        num_pr.get_or_add_numId().val = num.numId
        num_pr.get_or_add_ilvl().val = 0
        self._list_num_id = num.numId

    def numbered(self, text: str) -> None:
        paragraph = self.doc.add_paragraph(style="List Number")
        previous = paragraph._p.getprevious()
        was_numbered = previous is not None and previous.xpath("./w:pPr/w:pStyle[@w:val='ListNumber']")
        if was_numbered and getattr(self, "_list_num_id", None):
            num_pr = paragraph._p.get_or_add_pPr().get_or_add_numPr()
            num_pr.get_or_add_numId().val = self._list_num_id
            num_pr.get_or_add_ilvl().val = 0
        else:
            self._new_number_list(paragraph)
        _add_runs(paragraph, text, linker=self._link)
        self._md(f"1. {text}")

    def _callout(self, key: str, label: str, text: str, italic: bool, color: RGBColor | None, size: int = 11) -> None:
        self.counts[key] += 1
        paragraph = self.doc.add_paragraph()
        tag = paragraph.add_run(f"{label}: ")
        tag.bold = True
        tag.font.size = Pt(size)
        if color is not None:
            tag.font.color.rgb = color
        _add_runs(paragraph, text, size, italic, color, linker=self._link)
        self._md(f"> **{label}:** {text}\n")

    def note(self, text: str) -> None:
        self._callout("note", "NOTE", text, True, None)

    def security(self, text: str) -> None:
        self._callout("security", "SECURITY", text, True, RGBColor(150, 0, 0))

    def tip(self, text: str) -> None:
        self._callout("tip", "TIP", text, True, RGBColor(0, 100, 60))

    def production(self, text: str) -> None:
        self._callout("production", "IN PRODUCTION", text, True, RGBColor(100, 100, 100), 10)

    def incident(self, text: str) -> None:
        self._callout("incident", "REAL-WORLD", text, True, RGBColor(140, 80, 0), 10)

    def action(self, text: str) -> None:
        self._callout("action", "YOUR TURN", text, False, RGBColor(0, 80, 160))

    def objectives(self, rows: list[tuple[str, str]]) -> None:
        """The module overview: one bullet per row, with a bold label."""
        for label, text in rows:
            paragraph = self.doc.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.add_run(f"{label}: ").bold = True
            _add_runs(paragraph, text, linker=self._link)
            self._md(f"- **{label}:** {text}")
        self._md("")

    def lead_bullet(self, text: str) -> None:
        """A bullet whose words before the first colon are bold (a numbered diagram block)."""
        head, sep, rest = text.partition(": ")
        if not sep or len(head) > 40:
            self.bullet(text)
            return
        paragraph = self.doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.add_run(f"{head}: ").bold = True
        _add_runs(paragraph, rest, linker=self._link)
        self._md(f"- **{head}:** {rest}")

    def learning_point(self, text: str) -> None:
        """One bold sentence at the head of a step: what this step teaches."""
        paragraph = self.doc.add_paragraph()
        run = paragraph.add_run(f"Learning point: {text}")
        run.bold = True
        self._md(f"**Learning point: {text}**\n")

    def takeaway(self, text: str) -> None:
        self._callout("takeaway", "TAKEAWAY", text, False, RGBColor(0, 80, 160))

    def checkpoint(self, text: str) -> None:
        self._callout("checkpoint", "CHECKPOINT", text, False, RGBColor(0, 120, 60))

    def code(self, lines: str, lang: str = "bash") -> None:
        for line in lines.split("\n"):
            paragraph = self.doc.add_paragraph()
            run = paragraph.add_run(line)
            run.font.name = "Consolas"
            run.font.size = Pt(10)
            paragraph.paragraph_format.space_after = Pt(0)
            _shade(paragraph, CODE_SHADE)
        self.doc.add_paragraph("")
        self._md(f"```{lang}\n{lines}\n```\n")

    def output(self, lines: str) -> None:
        label = self.doc.add_paragraph()
        run = label.add_run("Expected output:")
        label.paragraph_format.keep_with_next = True
        run.bold = True
        run.font.size = Pt(10)
        for line in lines.split("\n"):
            paragraph = self.doc.add_paragraph()
            run = paragraph.add_run(line)
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0, 100, 0)
            paragraph.paragraph_format.space_after = Pt(0)
            _shade(paragraph, OUTPUT_SHADE)
        self.doc.add_paragraph("")
        self._md(f"**Expected output:**\n\n```\n{lines}\n```\n")

    def legend_bullet(self, name: str, meaning: str) -> None:
        """A bullet "name: meaning" whose name is a bookmark, so a hover link or a box over a picture can point at it."""
        self._bookmark_id += 1
        anchor = "box_" + re.sub(r"[^A-Za-z0-9]", "_", name.lower())
        paragraph = self.doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        start = OxmlElement("w:bookmarkStart")
        start.set(qn("w:id"), str(self._bookmark_id))
        start.set(qn("w:name"), anchor)
        paragraph._p.append(start)
        _add_runs(paragraph, name, linker=None)
        end = OxmlElement("w:bookmarkEnd")
        end.set(qn("w:id"), str(self._bookmark_id))
        paragraph._p.append(end)
        _add_runs(paragraph, ": " + meaning, linker=self._link)
        self._md(f"- {name}: {meaning}")
        if name.lower() not in self._hover:
            self._hover[name.lower()] = (anchor, meaning[:250])
            self._rebuild_hover()

    def _rebuild_hover(self) -> None:
        keys = sorted(self._hover, key=len, reverse=True)
        self._hover_pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(k) for k in keys) + r")(?:s|es)?(?![A-Za-z0-9])", re.I)

    def hover_names(self, intro: str, items: list) -> None:
        """One line "intro name, name, ..." where every name shows its meaning when hovered in Word.

        The Word file shows the meanings only on hover. The .md leaves the line out, because the numbered reading below the picture already says what every box is.
        """
        paragraph = self.doc.add_paragraph()
        _add_runs(paragraph, intro + " ")
        for index, (name, meaning) in enumerate(items):
            if index:
                _add_runs(paragraph, ", ")
            anchor = "box_" + re.sub(r"[^A-Za-z0-9]", "_", name.lower())
            self._bookmark_id += 1
            start = OxmlElement("w:bookmarkStart")
            start.set(qn("w:id"), str(self._bookmark_id))
            start.set(qn("w:name"), anchor)
            paragraph._p.append(start)
            _hover_link(paragraph, name, anchor, meaning[:250], 11, False)
            end = OxmlElement("w:bookmarkEnd")
            end.set(qn("w:id"), str(self._bookmark_id))
            paragraph._p.append(end)
        _add_runs(paragraph, ".")

    def image(self, path: Path, alt: str, ascii_text: str = "", width_in: float = 6.3) -> None:
        """Insert a PNG into the .docx; the .md gets the ASCII diagram (if given) plus an image link."""
        pic = self.doc.add_picture(str(path), width=Inches(min(width_in, TEXT_WIDTH_IN)))
        pic._inline.docPr.set("descr", alt)
        self.doc.add_paragraph("")
        if ascii_text:
            self._md("```text\n" + ascii_text + "\n```\n")
        self._md(f"![{alt}](img/{Path(path).name})\n")

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for index, header in enumerate(headers):
            cell = table.rows[0].cells[index]
            cell.text = header
            cell.paragraphs[0].paragraph_format.keep_with_next = True
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.size = Pt(10)
        for row_data in rows:
            row = table.add_row()
            for index, value in enumerate(row_data):
                _set_cell(row.cells[index], value, 10)
        _repeat_header(table)
        self.doc.add_paragraph("")
        self._md("| " + " | ".join(headers) + " |")
        self._md("| " + " | ".join("---" for _ in headers) + " |")
        for row_data in rows:
            self._md("| " + " | ".join(_md_cell(cell) for cell in row_data) + " |")
        self._md()

    def _link_cell(self, cell, text: str, url: str) -> None:
        part = self.doc.part
        r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
        link = OxmlElement("w:hyperlink")
        link.set(qn("r:id"), r_id)
        run = OxmlElement("w:r")
        props = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0563C1")
        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        size = OxmlElement("w:sz")
        size.set(qn("w:val"), "20")
        for el in (color, underline, size):
            props.append(el)
        run.append(props)
        label = OxmlElement("w:t")
        label.text = text
        run.append(label)
        link.append(run)
        cell.paragraphs[0]._p.append(link)

    def tool_table(self, rows: list[tuple]) -> None:
        """Table of (name, url, what it is, used here[, why this tool]); the name is a live link in the .docx."""
        with_why = bool(rows) and all(len(r) == 5 for r in rows)
        headers = ["Tool (overview link)", "What it is", "Used in this lab"] + (["Why this tool"] if with_why else [])
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for index, header in enumerate(headers):
            cell = table.rows[0].cells[index]
            cell.text = header
            cell.paragraphs[0].paragraph_format.keep_with_next = True
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.size = Pt(10)
        for name, url, what, use, *why in rows:
            row = table.add_row()
            self._link_cell(row.cells[0], name, url)
            for index, value in enumerate((what, use, *why), start=1):
                _set_cell(row.cells[index], value, 9)
        self.doc.add_paragraph("")
        self._md("| " + " | ".join(headers) + " |")
        self._md("| " + " | ".join("---" for _ in headers) + " |")
        for name, url, what, use, *why in rows:
            cells = " | ".join(_md_cell(v) for v in (what, use, *why))
            self._md(f"| [{name}]({url}) | {cells} |")
        self._md()

    def save(self, directory: Path, stem: str) -> tuple[Path, Path]:
        directory.mkdir(parents=True, exist_ok=True)
        docx_path = directory / f"{stem}.docx"
        md_path = directory / f"{stem}.md"
        self.doc.save(docx_path)
        self._close_details()
        md_path.write_text("\n".join(self.md_lines), encoding="utf-8")
        return docx_path, md_path

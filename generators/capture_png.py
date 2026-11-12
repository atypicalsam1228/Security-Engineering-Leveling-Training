"""Render saved live-run captures (live-run/captures/<ID>/<step>.txt) as terminal-style PNGs.

Usage: python capture_png.py <ID> [step ...]     (no step = every capture for the module)
Output: live-run/png/<ID>-shot-<step>.png  (redacted; copy into modules/img/ once checked)
The text is the real command output, redacted and drawn onto an image; it is not a screen grab.
"""
import getpass
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CAPTURES = ROOT / "live-run" / "captures"
OUT = ROOT / "live-run" / "png"

BG, FG, PROMPT, DIM = (24, 26, 31), (220, 223, 228), (120, 200, 140), (130, 136, 146)
FONT_SIZE, PAD, MAX_COLS, MAX_LINES = 15, 16, 110, 60

ANSI = re.compile(r"\[[0-9;?]*[A-Za-z]")  # colour codes in a captured terminal would draw as boxes

REDACTIONS = [
    (re.compile(r"[a-z0-9.-]+\.lab\.[a-z0-9-]+\.[a-z]{2,}"), "<lab-domain>"),
    (re.compile(r"[\w.+-]+@(?!example\.invalid)[\w-]+\.[\w.]+"), "<email>"),
    (re.compile(r"(?i)" + re.escape(getpass.getuser()) + r"[\w.-]*"), "<user>"),
    (re.compile(r"\b\d{12}\b"), "<account-id>"),
    (re.compile(r"(?i)(token|password|secret|authorization)([\"' =:]+)[^\s\"',}]{6,}"), r"\1\2<redacted>"),
    (re.compile(r"\b[A-Za-z0-9+/_-]{40,}\b"), "<redacted>"),
]


def redact(text):
    for pattern, repl in REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def load_font():
    for name in ("consola.ttf", "Consolas.ttf", "cour.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default()


def clip(lines):
    wrapped = [line[:MAX_COLS] + (" ..." if len(line) > MAX_COLS else "") for line in lines]
    if len(wrapped) > MAX_LINES:
        wrapped = wrapped[: MAX_LINES - 1] + [f"... ({len(wrapped) - MAX_LINES + 1} more lines)"]
    return wrapped


def parse(path):
    """Split a capture into (command lines, output lines, timing line)."""
    raw = ANSI.sub("", path.read_text(encoding="utf-8", errors="replace")).expandtabs(8).splitlines()
    sep = raw.index("---") if "---" in raw else 0
    cmd = [l[2:] if l.startswith("$ ") else l for l in raw[1:sep]]
    body = raw[sep + 1:]
    timing = body[-1] if body and body[-1].startswith("[exit=") else ""
    return cmd, [l for l in body if l != timing], timing


def render(path, dest):
    cmd, out, timing = parse(path)
    font = load_font()
    rows = [("$ " + l, PROMPT) for l in clip([redact(l) for l in cmd])]
    rows += [(l, FG) for l in clip([redact(l) for l in out])]
    if timing:
        rows.append((timing, DIM))
    width_px = int(font.getlength("M" * (MAX_COLS + 6))) + 2 * PAD
    height_px = (FONT_SIZE + 5) * len(rows) + 2 * PAD
    img = Image.new("RGB", (width_px, height_px), BG)
    draw = ImageDraw.Draw(img)
    for i, (text, colour) in enumerate(rows):
        draw.text((PAD, PAD + i * (FONT_SIZE + 5)), text, font=font, fill=colour)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    module, steps = argv[0], argv[1:]
    files = sorted((CAPTURES / module).glob("*.txt"))
    for f in files:
        if steps and f.stem not in steps:
            continue
        dest = OUT / f"{module}-shot-{f.stem}.png"
        render(f, dest)
        print(dest.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])

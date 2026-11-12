"""Redact a browser screenshot: python redact_shot.py <original> <out.png> x0,y0,x1,y1 [x0,y0,x1,y1 ...]
Boxes are filled solid. Originals stay outside the project."""
import sys
from PIL import Image, ImageDraw

src, out, *boxes = sys.argv[1:]
img = Image.open(src).convert("RGB")
draw = ImageDraw.Draw(img)
for box in boxes:
    x0, y0, x1, y1 = (int(v) for v in box.split(","))
    draw.rectangle((x0, y0, x1, y1), fill=(60, 60, 66))
img.save(out)

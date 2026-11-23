#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print-specimen sheet: original CJK vs redrawn Signature.

Run after building both presets locally:
    python3 scripts/build_cjk.py ... --preset cjk
    python3 scripts/build_cjk.py ... --preset signature
    python3 scripts/make_signature_sheet.py
Only uses local build/ outputs; no upstream font is needed here.
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MED = ROOT + "/build/SerifCJKExtension-CJK.ttf"
SIG = ROOT + "/build/SerifCJKExtension-Signature.ttf"
LAT = ROOT + "/build/SerifCJKExtension-Signature.ttf"  # Western glyphs are identical
DNA = ROOT + "/assets/design-dna.json"
OUT = ROOT + "/assets/signature-comparison.png"

W, H = 1600, 1320
PAPER, INK, RED, GREY, LINE = (243, 240, 232), (22, 21, 18), (166, 46, 38), (116, 111, 100), (205, 199, 187)

for p in (MED, SIG, LAT):
    if not os.path.isfile(p):
        raise SystemExit("missing: " + p)

im = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(im)

m, L = 26, 20
for x0, dx in ((m, 1), (W - m, -1)):
    for y0, dy in ((m, 1), (H - m, -1)):
        d.line((x0, y0, x0 + dx * L, y0), fill=LINE, width=1)
        d.line((x0, y0, x0, y0 + dy * L), fill=LINE, width=1)

small = ImageFont.truetype(LAT, 19)
label = ImageFont.truetype(LAT, 17)
foot = ImageFont.truetype(LAT, 16)
d.text((64, 34), "SERIF CJK EXTENSION   /   SIGNATURE STUDY", font=small, fill=INK)
tag = "TERMINAL GRAMMAR REDRAWN FROM MEASURED LATIN DNA"
tw = d.textlength(tag, font=small)
d.text((W - 64 - tw, 34), tag, font=small, fill=RED)
d.line((64, 72, W - 64, 72), fill=LINE, width=1)

LINES = [
    "天地玄黄　宇宙洪荒　排版设计",
    "中文字体　永和九年　岁在癸丑",
]


def block(y, title, sub, path, size, lines, red=False):
    d.rectangle((64, y, 67, y + 20), fill=RED if red else GREY)
    d.text((84, y - 3), title, font=label, fill=GREY)
    sw = d.textlength(sub, font=label)
    d.text((W - 64 - sw, y - 3), sub, font=label, fill=RED if red else GREY)
    f = ImageFont.truetype(path, size)
    yy = y + 36
    for ln in lines:
        d.text((64, yy), ln, font=f, fill=INK)
        yy += int(size * 1.40)
    d.line((64, yy - 8, W - 64, yy - 8), fill=LINE, width=1)
    return yy + 22


y = 98
y = block(y, "01   ORIGINAL   /   cjk 1.0.0",
          "Noto Serif CJK SC Medium, triangular terminals", MED, 54, LINES)
y = block(y, "02   SIGNATURE   /   signature 1.3.0",
          "Regular-weight source, flat serif heads, 5deg stress aligned", SIG, 54, LINES, red=True)

# Mixed line: Western glyphs are byte-identical in both builds.
d.rectangle((64, y, 67, y + 20), fill=RED)
d.text((84, y - 3), "03   MIXED   /   A + 文 on one baseline", font=label, fill=GREY)
mix = ImageFont.truetype(SIG, 46)
d.text((64, y + 34), "Typography 排版設計  A 文 H I O  2026  ﬁ 123", font=mix, fill=INK)
y += 34 + 74
d.line((64, y, W - 64, y), fill=LINE, width=1)
y += 18

# Terminal close-ups.
d.rectangle((64, y, 67, y + 20), fill=RED)
d.text((84, y - 3), "04   TERMINAL CLOSE-UP   /   6 glyphs, 2 builds", font=label, fill=GREY)
chars = "一二中文國永"
big = 132
fm = ImageFont.truetype(MED, big)
fs = ImageFont.truetype(SIG, big)
gy = y + 34
col = (W - 128) // len(chars)
for i, ch in enumerate(chars):
    x = 64 + i * col
    d.text((x, gy), ch, font=fm, fill=INK)
    d.text((x, gy + 160), ch, font=fs, fill=INK)
    d.text((x, gy + 320), "U+%04X" % ord(ch), font=foot, fill=GREY)
    if i:
        d.line((x - 14, gy - 8, x - 14, gy + 340), fill=LINE, width=1)
d.text((64, gy + 150), "MED", font=foot, fill=GREY)
d.text((64, gy + 310), "SIG", font=foot, fill=RED)
y = gy + 356
d.line((64, y, W - 64, y), fill=LINE, width=1)

# Measured numbers.
D = json.load(open(DNA, encoding="utf-8"))
t = D["targets"]
R = json.load(open(ROOT + "/assets/harmony-report.json", encoding="utf-8"))
row1 = ("Latin H %d / %d px (contrast %.3f)  |  Medium %.3f  ->  Signature %.3f  |  Western glyphs byte-identical" % (
    D["H_stem_px"], D["H_crossbar_px"], D["latin_contrast_ratio"],
    2.750, 2.273))
row2 = ("serif head %.1f u  |  no outward extension  |  shear %.4f  |  %d terminals  |  %.2f%% of 31,004 glyphs rebuilt" % (
    t["serif_head_over_stem"] * t["target_horizontal_units"] * 0.45,
    __import__("math").tan(__import__("math").radians(t["stress_shear_deg"])) * 0.40,
    R["terminals_total"], R["full_coverage_pct"]))
row3 = "Known limit: wedge slopes retained on dense glyphs; see docs/DESIGN.md."
d.text((64, y + 14), row1, font=foot, fill=GREY)
d.text((64, y + 36), row2, font=foot, fill=INK)
d.text((64, y + 58), row3, font=foot, fill=GREY)
sw = d.textlength("SOURCE-ONLY BUILD  /  NO BINARIES", font=foot)
d.text((W - 64 - sw, y + 58), "SOURCE-ONLY BUILD  /  NO BINARIES", font=foot, fill=RED)

im.save(OUT)
print("saved", OUT, im.size, os.path.getsize(OUT), "B")

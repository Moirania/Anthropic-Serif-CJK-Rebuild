#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optional L3 post-processing: stroke-skeleton-guided terminal harmonisation.

This is NOT a fifth build preset. It takes an already built
build/SerifCJKExtension-CJK.ttf and produces a second, locally generated
font in which selected CJK terminals are gently flattened. Font binaries
are never committed to this repository.

Pipeline (run from the repository root)::

    python3 scripts/l3_pipeline.py fetch
    python3 scripts/l3_pipeline.py build --tag p45 --pull 0.45
    python3 scripts/l3_pipeline.py build --tag p55 --pull 0.55
    python3 scripts/l3_pipeline.py build --tag p65 --pull 0.65
    python3 scripts/l3_pipeline.py build --tag p80 --pull 0.80
    python3 scripts/l3_pipeline.py audit --tag p45
    python3 scripts/l3_pipeline.py audit --tag p55
    python3 scripts/l3_pipeline.py audit --tag p65
    python3 scripts/l3_pipeline.py audit --tag p80
    python3 scripts/l3_pipeline.py merge --tags p80,p65,p55,p45

Third-party data: hanzi-writer-data (Make Me A Hanzi stroke medians).
Its licence is NOT re-asserted here; `fetch` downloads it at run time and
the reader must check the upstream licence before redistributing any index.
The generated data/ directory is git-ignored.

Structural invariants that make malformed glyphs impossible:
  * no point added, removed or re-flagged
  * no x coordinate changes
  * only y coordinates inside a bounded window move
  * every changed glyph is rendered and audited; anomalies roll back
"""
import argparse
import io
import json
import math
import os
import sys
import urllib.request
import zipfile
from array import array
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BUILD = os.path.join(ROOT, "build")
IDX = os.path.join(DATA, "strokes.json")
BASE = os.path.join(BUILD, "SerifCJKExtension-CJK.ttf")
ZIP_URL = "https://codeload.github.com/chanind/hanzi-writer-data/zip/refs/heads/master"

SIZE, BOX, PAD = 128, 220, 30
STRUCT = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=int)
MIN_MEDIAN_LEN = 70


# --------------------------------------------------------------- fetch ----
def cmd_fetch(args):
    os.makedirs(DATA, exist_ok=True)
    cache = os.path.join(DATA, "hanzi-writer-data.zip")
    if not os.path.isfile(cache):
        print("downloading", ZIP_URL)
        req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "l3-pipeline"})
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
        with open(cache, "wb") as fh:
            fh.write(raw)
    z = zipfile.ZipFile(cache)
    idx = {}
    for nm in z.namelist():
        if not nm.endswith(".json"):
            continue
        ch = os.path.basename(nm)[:-5]
        if len(ch) != 1:
            continue
        cp = ord(ch)
        if not (0x3400 <= cp <= 0x9FFF or 0x20000 <= cp <= 0x323AF or
                0xF900 <= cp <= 0xFAFF):
            continue
        try:
            d = json.loads(z.read(nm).decode("utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("medians"), list) and d["medians"]:
            idx[ch] = d["medians"]
    with open(IDX, "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, separators=(",", ":"))
    print("stroke index: %d characters -> %s (%d B)" %
          (len(idx), IDX, os.path.getsize(IDX)))


# --------------------------------------------------------------- geometry --
def classify(m):
    pts = [(float(p[0]), float(p[1])) for p in m]
    if len(pts) < 2:
        return "dot", pts
    x0, y0 = pts[0]
    x1, y1 = pts[-1]
    dx, dy = x1 - x0, y1 - y0
    if math.hypot(dx, dy) < MIN_MEDIAN_LEN:
        return "dot", pts
    if len(pts) >= 3:
        k = len(pts) // 2
        ax, ay = pts[k][0] - x0, pts[k][1] - y0
        bx, by = x1 - pts[k][0], y1 - pts[k][1]
        na, nb = math.hypot(ax, ay), math.hypot(bx, by)
        if na > 25 and nb > 25 and (ax * bx + ay * by) / (na * nb) < 0.55:
            return "fold", pts
    ax, ay = abs(dx), abs(dy)
    if ax > 1e-9 and ay <= 0.30 * ax and dx > 0:
        return "H", pts
    if ay > 1e-9 and ax <= 0.30 * ay and dy < 0:
        return "V", pts
    if dx < 0 and dy < 0:
        return "pie", pts
    if dx > 0 and dy < 0:
        return "na", pts
    return "other", pts


def mapper(all_pts, g):
    hx = [p[0] for p in all_pts]
    hy = [p[1] for p in all_pts]
    hx0, hx1, hy0, hy1 = min(hx), max(hx), min(hy), max(hy)
    sx = (g.xMax - g.xMin) / max(hx1 - hx0, 1.0)
    sy = (g.yMax - g.yMin) / max(hy1 - hy0, 1.0)
    return lambda p: (g.xMin + (p[0] - hx0) * sx,
                      g.yMin + (p[1] - hy0) * sy)


# ----------------------------------------------------------------- build ---
def cmd_build(args):
    if not os.path.isfile(IDX):
        sys.exit("run `l3_pipeline.py fetch` first")
    if not os.path.isfile(BASE):
        sys.exit("run the cjk preset build first: " + BASE)
    idx = json.load(open(IDX, encoding="utf-8"))
    f = TTFont(BASE)
    cm = f.getBestCmap()
    glyf = f["glyf"]
    out = os.path.join(BUILD, "L3-%s.ttf" % args.tag)
    audit = os.path.join(DATA, "L3-%s-build.json" % args.tag)
    chars = sorted(idx)[:args.limit] if args.limit else sorted(idx)
    stats, changed = Counter(), {}
    for ch in chars:
        cp = ord(ch)
        if cp not in cm:
            stats["no_glyph"] += 1
            continue
        cls = [classify(m) for m in idx[ch]]
        H = [pts for kind, pts in cls if kind == "H"]
        if not H:
            stats["no_H_stroke"] += 1
            continue
        name, g = cm[cp], glyf[cm[cp]]
        if g.numberOfContours <= 0:
            stats["composite_or_empty"] += 1
            continue
        mp = mapper([p for _, pts in cls for p in pts], g)
        co = [(float(x), float(y)) for x, y in g.coordinates]
        fl = [int(v) for v in g.flags]
        ends = list(g.endPtsOfContours)
        new = [list(p) for p in co]
        moved = 0
        for pts in H:
            for tip in (pts[-1], pts[0]):
                X, Y = mp(tip)
                right = tip is pts[-1]
                for i, (x, y) in enumerate(co):
                    if right:
                        in_x = (X - args.window_x) <= x <= (X + 60)
                    else:
                        in_x = (X - 60) <= x <= (X + args.window_x)
                    rise = new[i][1] - Y
                    if in_x and args.min_rise < rise < args.window_y:
                        new[i][1] = Y + rise * (1.0 - args.pull)
                        moved += 1
        if moved == 0:
            stats["no_change"] += 1
            continue
        g.coordinates = GlyphCoordinates([(x, y) for x, y in new])
        g.flags = array("B", fl)
        g.endPtsOfContours = ends
        g.recalcBounds(glyf)
        changed[name] = {"char": ch, "cp": cp, "points_moved": moved,
                         "H_strokes": len(H), "strokes": len(cls)}
        stats["changed"] += 1
        stats["points_moved"] += moved
    f.save(out)
    rep = {"tag": args.tag, "index_chars": len(chars),
           "changed_glyphs": len(changed),
           "params": {"PULL": args.pull, "WINDOW_X": args.window_x,
                      "WINDOW_Y": args.window_y, "MIN_RISE": args.min_rise},
           "stats": dict(stats), "changed": changed}
    with open(audit, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print("built %s: %d glyphs, %d points moved -> %s" %
          (args.tag, len(changed), stats["points_moved"], out))


# ----------------------------------------------------------------- audit ---
def render(font, ch):
    im = Image.new("L", (BOX, BOX), 255)
    ImageDraw.Draw(im).text((PAD, PAD), ch, font=font, fill=0)
    return np.array(im) < 128


def metrics(a):
    lab, n = ndimage.label(a, structure=STRUCT)
    sizes = np.bincount(lab.ravel())[1:] if n else np.array([])
    bg, nb = ndimage.label(~a, structure=STRUCT)
    border = set(bg[0, :].tolist() + bg[-1, :].tolist() +
                 bg[:, 0].tolist() + bg[:, -1].tolist())
    holes = nb - len([b for b in border if b != 0])
    ys, xs = np.where(a)
    bbox = ((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            if len(xs) else (0, 0, 0, 0))
    return {"components": int(n), "sizes": [int(s) for s in sizes],
            "holes": int(holes), "bbox": bbox, "ink": int(a.sum())}


def check(b, c):
    r = []
    if c["components"] != b["components"]:
        r.append("component_count")
    if c["holes"] != b["holes"]:
        r.append("hole_count")
    if sum(1 for s in c["sizes"] if s < 10) > sum(1 for s in b["sizes"] if s < 10):
        r.append("hairline")
    if max(abs(x - y) for x, y in zip(b["bbox"], c["bbox"])) > 2:
        r.append("bbox_shift")
    if b["ink"] > 0:
        if max(0, c["ink"] - b["ink"]) / b["ink"] > 0.10:
            r.append("blob")
        if abs(c["ink"] - b["ink"]) / b["ink"] > 0.22:
            r.append("ink_delta")
    return r


def cmd_audit(args):
    cand = os.path.join(BUILD, "L3-%s.ttf" % args.tag)
    bjson = os.path.join(DATA, "L3-%s-build.json" % args.tag)
    clean = os.path.join(BUILD, "L3-%s-clean.ttf" % args.tag)
    report = os.path.join(DATA, "L3-%s-report.json" % args.tag)
    changed = json.load(open(bjson, encoding="utf-8"))["changed"]
    fb, fc = ImageFont.truetype(BASE, SIZE), ImageFont.truetype(cand, SIZE)
    bf, out = TTFont(BASE), TTFont(cand)
    gb, go = bf["glyf"], out["glyf"]
    passed, reasons_count, ink, passed_names = 0, Counter(), [], {}
    for name, info in changed.items():
        ch = info["char"]
        try:
            rs = check(metrics(render(fb, ch)), metrics(render(fc, ch)))
        except Exception as exc:
            rs = ["render_error:" + type(exc).__name__]
        if rs:
            for r in rs:
                reasons_count[r] += 1
            src = gb[name]
            dst = go[name]
            dst.coordinates = GlyphCoordinates(
                [(float(x), float(y)) for x, y in src.coordinates])
            dst.flags = array("B", [int(v) for v in src.flags])
            dst.endPtsOfContours = list(src.endPtsOfContours)
            dst.numberOfContours = src.numberOfContours
            dst.recalcBounds(go)
        else:
            passed += 1
            passed_names[name] = info
            mb = metrics(render(fb, ch))
            if mb["ink"]:
                ink.append(metrics(render(fc, ch))["ink"] / mb["ink"])
    out.save(clean)
    fz = ImageFont.truetype(clean, SIZE)
    residual = 0
    for name, info in changed.items():
        ch = info["char"]
        if check(metrics(render(fb, ch)), metrics(render(fz, ch))):
            residual += 1
    rep = {"tag": args.tag, "candidates": len(changed), "passed": passed,
           "rolled_back": len(changed) - passed, "residual_failures": residual,
           "reasons": dict(reasons_count),
           "ink_ratio_mean": round(float(np.mean(ink)), 4) if ink else None,
           "passed_names": passed_names}
    with open(report, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print("audit %s: passed %d / %d, rolled back %d, residual %d" %
          (args.tag, passed, len(changed), len(changed) - passed, residual))


# ----------------------------------------------------------------- merge ---
def cmd_merge(args):
    tags = [t.strip() for t in args.tags.split(",")]
    picks = {}
    per_tag = {}
    for tag in tags:
        rep = json.load(open(os.path.join(DATA, "L3-%s-report.json" % tag),
                             encoding="utf-8"))
        per_tag[tag] = len(rep["passed_names"])
        for name, info in rep["passed_names"].items():
            if name not in picks:
                picks[name] = (tag, info)
    print("per-tag passed:", per_tag, "| merged:", len(picks))
    base = TTFont(BASE)
    cands = {t: TTFont(os.path.join(BUILD, "L3-%s.ttf" % t)) for t in tags}
    go = base["glyf"]
    for name, (tag, info) in picks.items():
        s = cands[tag]["glyf"][name]
        d = go[name]
        d.coordinates = GlyphCoordinates(
            [(float(x), float(y)) for x, y in s.coordinates])
        d.flags = array("B", [int(v) for v in s.flags])
        d.endPtsOfContours = list(s.endPtsOfContours)
        d.numberOfContours = s.numberOfContours
        d.recalcBounds(go)
    final = os.path.join(BUILD, "SerifCJKExtension-L3.ttf")
    base.save(final)

    fb, ff = ImageFont.truetype(BASE, SIZE), ImageFont.truetype(final, SIZE)
    bad, ink = 0, []
    for name, (tag, info) in picks.items():
        ch = info["char"]
        mb, mf = metrics(render(fb, ch)), metrics(render(ff, ch))
        if check(mb, mf):
            bad += 1
        elif mb["ink"]:
            ink.append(mf["ink"] / mb["ink"])
    bfont, ffont = TTFont(BASE), TTFont(final)
    west_ok = True
    for n in bfont.getGlyphOrder()[:720]:
        if (list(bfont["glyf"][n].getCoordinates(bfont["glyf"])[0]) !=
                list(ffont["glyf"][n].getCoordinates(ffont["glyf"])[0])):
            west_ok = False
            break
    rep = {"index_chars": len(json.load(open(IDX, encoding="utf-8"))),
           "per_tag_passed": per_tag, "merged_glyphs": len(picks),
           "source_distribution": dict(Counter(t for t, _ in picks.values())),
           "re_audit_defects": bad, "western_720_identical": west_ok,
           "ink_ratio_mean": round(float(np.mean(ink)), 4) if ink else None,
           "size_bytes": os.path.getsize(final)}
    rpath = os.path.join(DATA, "L3-final-report.json")
    with open(rpath, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print("saved", final)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    b = sub.add_parser("build")
    b.add_argument("--tag", required=True)
    b.add_argument("--pull", type=float, default=0.55)
    b.add_argument("--window-x", type=float, default=260)
    b.add_argument("--window-y", type=float, default=180)
    b.add_argument("--min-rise", type=float, default=8)
    b.add_argument("--limit", type=int, default=0)
    a = sub.add_parser("audit")
    a.add_argument("--tag", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--tags", default="p80,p65,p55,p45")
    args = ap.parse_args()
    {"fetch": cmd_fetch, "build": cmd_build,
     "audit": cmd_audit, "merge": cmd_merge}[args.cmd](args)


if __name__ == "__main__":
    main()

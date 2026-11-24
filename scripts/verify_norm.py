#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Four-point normative audit for any CJK build.

The acceptance rule came from the maintainer: a build is 规整 only when ALL
four hold --

  1. stroke weight consistency   (笔画粗细是否一致)
  2. counter white uniformity    (字腔留白是否均匀)
  3. shared optical centre line  (重心是否在同一条线上)
  4. uniform central aperture    (中宫大小是否统一)

A post-processing pass is accepted only if none of the four gets worse
than the reference build. Absolute "good looking" numbers are not enough:
we also measure the per-glyph delta, because a small mean shift spread
unevenly across characters is exactly what makes a line of text look off.

Usage (run from the repository root after building both fonts locally)::

    python3 scripts/verify_norm.py \\
      --reference build/SerifCJKExtension-CJK.ttf \\
      --candidate build/SerifCJKExtension-L3.ttf \\
      --out build/norm-report.json

Dependencies: fonttools, numpy, Pillow, scipy.
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from fontTools.ttLib import TTFont

S, BOX, PAD = 400, 700, 100
STRUCT = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=int)

STROKE_CHARS = "二三王土干工正日目田十下上百自且直"
COUNTER_CHARS = "口日目田回品昌由甲申早古占右石"
CENTRE_CHARS = "一二三中口日目田王土干工正大天人山文國永天地"
ALL = sorted(set(STROKE_CHARS + COUNTER_CHARS + CENTRE_CHARS))


def raw_mask(font, ch):
    im = Image.new("L", (BOX, BOX), 255)
    ImageDraw.Draw(im).text((PAD, PAD), ch, font=font, fill=0)
    a = np.array(im) < 128
    ys, xs = np.where(a)
    if not len(xs):
        return None
    return a, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def norm_mask(a, bb):
    x0, y0, x1, y1 = bb
    crop = a[max(0, y0 - 4):y1 + 5, max(0, x0 - 4):x1 + 5]
    im = Image.fromarray((crop * 255).astype("uint8")).resize((256, 256), Image.LANCZOS)
    return np.array(im) > 128


def runs(row):
    out, st = [], None
    for i, v in enumerate(row):
        if v and st is None:
            st = i
        elif not v and st is not None:
            out.append(i - st)
            st = None
    if st is not None:
        out.append(len(row) - st)
    return [w for w in out if w > 2]


def stroke_widths(font, ch):
    r = raw_mask(font, ch)
    if r is None:
        return None
    a, (x0, y0, x1, y1) = r
    h, w = y1 - y0 + 1, x1 - x0 + 1
    hs = []
    for x in range(x0 + int(0.18 * w), x1 - int(0.18 * w), max(1, w // 24)):
        hs += [v for v in runs(a[:, x]) if v < 0.16 * h]
    vs = []
    for y in range(y0 + int(0.18 * h), y1 - int(0.18 * h), max(1, h // 24)):
        vs += [v for v in runs(a[y, :]) if v < 0.16 * w]
    return (float(np.median(hs)) if hs else None,
            float(np.median(vs)) if vs else None)


def counter_white(m):
    bg, n = ndimage.label(~m, structure=STRUCT)
    border = set(bg[0, :].tolist() + bg[-1, :].tolist() +
                 bg[:, 0].tolist() + bg[:, -1].tolist())
    inner = [i for i in range(1, n + 1) if i not in border]
    return sum(int((bg == i).sum()) for i in inner) / float(m.size)


def centre_y(m):
    ys, _ = np.where(m)
    return float(ys.mean()) / m.shape[0] if len(ys) else 0.0


def middle_white(m):
    a, b = int(0.30 * m.shape[0]), int(0.70 * m.shape[0])
    return float((~m[a:b, a:b]).mean())


def cv(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return round(float(np.std(xs) / np.mean(xs)), 4) if len(xs) >= 3 and np.mean(xs) else None


def measure(path, label):
    f = ImageFont.truetype(path, S)
    res = {"label": label, "path": os.path.basename(path),
           "h_thick": {}, "v_thick": {}, "counter": {},
           "centre_y": {}, "middle_white": {}}
    for ch in ALL:
        sw = stroke_widths(f, ch)
        r = raw_mask(f, ch)
        if r is None:
            continue
        m = norm_mask(*r)
        if sw:
            res["h_thick"][ch] = sw[0]
            res["v_thick"][ch] = sw[1]
        res["counter"][ch] = counter_white(m)
        res["centre_y"][ch] = centre_y(m)
        res["middle_white"][ch] = middle_white(m)
    return res


def summarise(res):
    clean = lambda xs: [x for x in xs if x is not None and math.isfinite(x)]
    h = clean([v for k, v in res["h_thick"].items() if k in STROKE_CHARS])
    v = clean([v for k, v in res["v_thick"].items() if k in STROKE_CHARS])
    c = clean([v for k, v in res["counter"].items() if k in COUNTER_CHARS])
    y = clean([v for k, v in res["centre_y"].items() if k in CENTRE_CHARS])
    mw = clean([v for k, v in res["middle_white"].items() if k in CENTRE_CHARS])
    mean = lambda xs: round(float(np.mean(xs)), 4) if xs else None
    return {
        "stroke_h_cv": cv(h), "stroke_v_cv": cv(v),
        "stroke_h_mean": mean(h), "stroke_v_mean": mean(v),
        "counter_cv": cv(c), "counter_mean": mean(c),
        "centre_std": round(float(np.std(y)), 4) if y else None,
        "centre_mean": mean(y),
        "centre_spread": round(float(max(y) - min(y)), 4) if y else None,
        "middle_cv": cv(mw), "middle_mean": mean(mw),
    }


def deltas(base, other, key):
    out = [other[key][ch] - bv for ch, bv in base[key].items()
           if ch in other[key] and bv is not None and other[key][ch] is not None]
    return {"n": len(out),
            "mean": round(float(np.mean(out)), 5) if out else None,
            "std": round(float(np.std(out)), 5) if out else None,
            "max_abs": round(float(max(abs(x) for x in out)), 5) if out else None}


def verdict(a, b, d):
    """True = candidate did not make this dimension worse."""
    checks = {
        "1_stroke_weight": a["stroke_h_cv"] is not None and b["stroke_h_cv"] is not None
                           and b["stroke_h_cv"] <= a["stroke_h_cv"] * 1.02,
        "2_counter_white": a["counter_cv"] is not None and b["counter_cv"] is not None
                           and b["counter_cv"] <= a["counter_cv"] * 1.02,
        "3_centre_line": a["centre_std"] is not None and b["centre_std"] is not None
                         and b["centre_std"] <= a["centre_std"] * 1.02
                         and abs(d["centre_y"]["mean"] or 0) < 0.002,
        "4_central_aperture": a["middle_cv"] is not None and b["middle_cv"] is not None
                              and b["middle_cv"] <= a["middle_cv"] * 1.02,
    }
    return {"checks": checks, "passed": sum(checks.values()),
            "total": 4, "accepted": all(checks.values())}


def inner_contour_evidence(ref, cand):
    try:
        fb, fl = TTFont(ref), TTFont(cand)
        gb, gl, cm = fb["glyf"], fl["glyf"], fb.getBestCmap()
        moved = inner = touched = 0
        for ch in ALL:
            n = cm.get(ord(ch))
            if not n:
                continue
            a, b = gb[n], gl[n]
            if a.numberOfContours <= 0:
                continue
            ca = [(float(x), float(y)) for x, y in a.coordinates]
            cb = [(float(x), float(y)) for x, y in b.coordinates]
            if len(ca) != len(cb):
                continue
            ends, areas, s = list(a.endPtsOfContours), [], 0
            for e in ends:
                seg = ca[s:e + 1]
                areas.append(sum(seg[i][0] * seg[(i + 1) % len(seg)][1] -
                                 seg[(i + 1) % len(seg)][0] * seg[i][1]
                                 for i in range(len(seg))) / 2)
                s = e + 1
            outer = max(range(len(areas)), key=lambda i: abs(areas[i]))
            osign = 1 if areas[outer] >= 0 else -1
            ci, s, hit = 0, 0, False
            for e in ends:
                sign = 1 if areas[ci] >= 0 else -1
                for i in range(s, e + 1):
                    if abs(ca[i][1] - cb[i][1]) > 0.01:
                        moved += 1
                        hit = True
                        if sign != osign:
                            inner += 1
                s, ci = e + 1, ci + 1
            if hit:
                touched += 1
        return {"sample_chars_touched": touched, "moved_points": moved,
                "of_them_inner_contour": inner,
                "inner_pct": round(100.0 * inner / max(moved, 1), 2)}
    except Exception as exc:
        return {"error": type(exc).__name__ + ": " + str(exc)[:100]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", default="build/norm-report.json")
    a = ap.parse_args()
    for p in (a.reference, a.candidate):
        if not os.path.isfile(p):
            raise SystemExit("font not found: " + p)
    ref = measure(a.reference, "reference")
    cand = measure(a.candidate, "candidate")
    sr, sc = summarise(ref), summarise(cand)
    delta = {k: deltas(ref, cand, k)
             for k in ("counter", "centre_y", "middle_white", "h_thick", "v_thick")}
    rep = {"sample_chars": len(ALL),
           "sets": {"stroke": STROKE_CHARS, "counter": COUNTER_CHARS,
                    "centre": CENTRE_CHARS},
           "reference": sr, "candidate": sc,
           "candidate_minus_reference": delta,
           "verdict": verdict(sr, sc, delta),
           "inner_contour_evidence": inner_contour_evidence(a.reference, a.candidate)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print("\nsaved", a.out)


if __name__ == "__main__":
    main()

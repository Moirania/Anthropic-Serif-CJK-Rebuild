#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Measure the Latin base font's design grammar and write assets/design-dna.json.

Everything is measured from FreeType rasterisation at a fixed 1000 px em,
so the numbers are reproducible and independent of the build machine. The
output is the sole parameter source for scripts/harmonize.py: no design
value is hard-coded in the redraw engine.

Run from the repository root::

    python3 scripts/measure_dna.py

Inputs (not shipped):
  * inputs/AnthropicSerifWebText.ttf  (or --latin PATH)
  * a Noto Serif CJK SC Medium OTF    (--cjk PATH)
"""
import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SIZE = 1000


def raster(font, ch, box=(1700, 1500)):
    im = Image.new("L", box, 255)
    ImageDraw.Draw(im).text((220, 220), ch, font=font, fill=0)
    a = np.array(im) < 128
    ys, xs = np.where(a)
    return a, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def runs(row):
    out, st = [], None
    for i, v in enumerate(row):
        if v and st is None:
            st = i
        elif not v and st is not None:
            out.append((st, i - st))
            st = None
    if st is not None:
        out.append((st, len(row) - st))
    return [(s, w) for s, w in out if w > 3]


def widths_at(a, y):
    return [w for _, w in runs(a[y, :])]


def heights_at(a, x):
    return [w for _, w in runs(a[:, x])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latin", default="inputs/AnthropicSerifWebText.ttf")
    ap.add_argument("--cjk", default="/usr/share/fonts/opentype/source-han-serif/"
                                     "SourceHanSerifSC-Medium.otf")
    ap.add_argument("--out", default="assets/design-dna.json")
    a = ap.parse_args()

    for path in (a.latin, a.cjk):
        if not os.path.isfile(path):
            raise SystemExit("input not found: %s" % path)

    WF = ImageFont.truetype(a.latin, SIZE)
    CF = ImageFont.truetype(a.cjk, SIZE)
    D = {"source": os.path.basename(a.latin), "sample_px": SIZE,
         "cjk_baseline": os.path.basename(a.cjk),
         "note": "FreeType raster, all lengths in px at 1000 px em; "
                 "ratios are em-normalised"}

    aH, bH = raster(WF, "H")
    aI, bI = raster(WF, "I")
    aX, bX = raster(WF, "x")
    aO, bO = raster(WF, "O")
    aN, bN = raster(WF, "n")

    cap, xht = bH[3] - bH[1] + 1, bX[3] - bX[1] + 1
    D["cap_height_em"] = round(cap / SIZE, 4)
    D["x_height_em"] = round(xht / SIZE, 4)
    D["xheight_over_cap"] = round(xht / cap, 4)

    # H stem above the crossbar, below the serif.
    hs = sorted(widths_at(aH, int(bH[1] + 0.30 * cap)))
    stem = float(np.mean(hs[:2])) if len(hs) >= 2 else (hs[0] if hs else 0)
    D["H_stem_px"] = round(stem, 2)
    D["H_stems_raw"] = hs[:6]
    cx = (bH[0] + bH[2]) // 2
    vr = heights_at(aH, cx)
    cross = float(min(vr)) if vr else 0
    D["H_crossbar_px"] = round(cross, 2)
    D["latin_contrast_ratio"] = round(stem / max(cross, 1), 3)

    # I bracket profile: flat serif head blending into the stem.
    prof = []
    for frac in (0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.14, 0.18, 0.24, 0.50):
        y = int(bI[1] + frac * (bI[3] - bI[1]))
        prof.append([round(frac, 3), float(max(widths_at(aI, y), default=0))])
    D["I_bracket_profile_frac_px"] = prof
    D["I_serif_head_px"] = prof[0][1]
    D["I_stem_px"] = prof[-1][1]
    D["targets_serif_head_over_stem"] = round(D["I_serif_head_px"] / stem, 3)
    D["serif_side_extension_over_stem"] = round(
        (D["I_serif_head_px"] - stem) / 2 / stem, 3)
    D["bracket_transition_frac"] = next(
        (f for f, w in prof[1:] if w <= stem * 1.08), None)

    # O stress axis.
    ocx, ocy = (bO[0] + bO[2]) / 2, (bO[1] + bO[3]) / 2
    maxr = min(bO[2] - bO[0], bO[3] - bO[1]) / 2 + 50
    th = []
    for deg in range(0, 180, 5):
        r_ = math.radians(deg)
        dx, dy = math.cos(r_), math.sin(r_)
        best = cur = 0
        for r in np.linspace(maxr * 0.60, maxr, 300):
            x, y = int(round(ocx + dx * r)), int(round(ocy + dy * r))
            v = (0 <= y < aO.shape[0] and 0 <= x < aO.shape[1] and bool(aO[y, x]))
            cur = cur + 1 if v else 0
            best = max(best, cur)
        th.append((deg, best))
    th.sort(key=lambda t: t[1])
    D["O_thinnest_axis_deg"] = th[0][0]
    D["O_thickest_axis_deg"] = th[-1][0]
    D["O_contrast_ratio"] = round(th[-1][1] / max(th[0][1], 1), 3)
    D["stress_axis_deg_from_vertical"] = abs(90 - th[0][0])

    ny = (bN[1] + bN[3]) // 2
    nr = widths_at(aN, ny)
    D["n_body_px"] = bN[2] - bN[0] + 1
    D["n_stem_over_body"] = round(float(np.mean(nr[:2])) / D["n_body_px"], 3) if nr else 0

    # CJK: vertical stems on 中, horizontals on 二, terminal wedge on 二.
    aZ, bZ = raster(CF, "中")
    zw = widths_at(aZ, (bZ[1] + bZ[3]) // 2)
    D["CJK_vertical_px"] = round(float(min(zw)) if zw else 0, 2)
    a2, b2 = raster(CF, "二")
    th2 = heights_at(a2, (b2[0] + b2[2]) // 2)
    D["CJK_horizontal_px"] = round(float(min(th2)) if th2 else 0, 2)
    D["CJK_contrast_ratio"] = round(
        D["CJK_vertical_px"] / max(D["CJK_horizontal_px"], 1), 3)
    D["contrast_delta_pct"] = round(
        (D["CJK_contrast_ratio"] / D["latin_contrast_ratio"] - 1) * 100, 1)
    prof2 = []
    span = b2[2] - b2[0]
    for frac in (0.02, 0.08, 0.20, 0.40, 0.60, 0.78, 0.88, 0.94, 0.98):
        x = int(b2[0] + frac * span)
        rs = heights_at(a2, x)
        prof2.append([round(frac, 3), round(float(min(rs)) if rs else 0, 2)])
    D["CJK_terminal_wedge_profile_frac_px"] = prof2
    D["CJK_wedge_end_over_middle"] = round(prof2[-1][1] / max(prof2[3][1], 1), 3)

    px2u = 2000 / SIZE
    tv = D["CJK_vertical_px"] * px2u
    th_ = D["CJK_horizontal_px"] * px2u
    target_h = tv / D["latin_contrast_ratio"]
    D["targets"] = {
        "serif_head_over_stem": D["targets_serif_head_over_stem"],
        "serif_side_extension_over_stem": D["serif_side_extension_over_stem"],
        "bracket_transition_frac_of_cap": D["bracket_transition_frac"],
        "stress_shear_deg": D["stress_axis_deg_from_vertical"],
        "target_contrast_ratio": D["latin_contrast_ratio"],
        "horizontal_over_vertical": round(1 / D["latin_contrast_ratio"], 4),
        "latin_stem_px_at_1000": D["H_stem_px"],
        "latin_crossbar_px_at_1000": D["H_crossbar_px"],
        "cjk_vertical_px_at_1000": D["CJK_vertical_px"],
        "cjk_horizontal_px_at_1000": D["CJK_horizontal_px"],
        "upem": 2000,
        "latin_stem_units": D["H_stem_px"] * px2u,
        "latin_crossbar_units": D["H_crossbar_px"] * px2u,
        "cjk_vertical_units": tv,
        "cjk_horizontal_units": th_,
        "target_horizontal_units": target_h,
        "edge_delta_units": (target_h - th_) / 2,
    }
    D["finding"] = (
        "CJK horizontals are %.1f%% thinner relative to their verticals than the "
        "Latin crossbar is to its stem (contrast %.3f vs %.3f). The second "
        "mismatch is terminal grammar: CJK horizontals end in an upward "
        "triangular wedge (end/middle %.2f), Latin uses a flat bracketed serif "
        "with a head %.2fx the stem blending back within %.0f%% of cap height." % (
            D["contrast_delta_pct"], D["CJK_contrast_ratio"],
            D["latin_contrast_ratio"], D["CJK_wedge_end_over_middle"],
            D["targets_serif_head_over_stem"],
            (D["bracket_transition_frac"] or 0) * 100))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(D, fh, ensure_ascii=False, indent=2)
    print(json.dumps(D, ensure_ascii=False, indent=2))
    print("\nSaved -> %s" % a.out)


if __name__ == "__main__":
    main()

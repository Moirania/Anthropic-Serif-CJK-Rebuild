#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redraw CJK stroke terminals using the Latin font's measured design grammar.

This is NOT a global emboldening pass. The Latin base font is measured by
scripts/measure_dna.py into assets/design-dna.json; every number used here
comes from that file. Three things are applied to CJK outlines only:

  1. Contrast alignment. Near-horizontal contour edges are pushed outward
     along their local outward normal until the horizontal/vertical stroke
     ratio matches the Latin H (crossbar / stem).
  2. Terminal grammar. Sharp triangular stroke ends are replaced with a
     flat bracketed serif: a short horizontal extension, two head points and
     one off-curve control point that pulls the bracket inward.
  3. Stress alignment. A small shear brings the CJK stress axis to the
     angle measured on the Latin O.

Western outlines and LGC outlines are never touched. Parameters are global
and identical for every glyph, which is how consistency across 31,004
characters is guaranteed; assets/harmony-report.json records the resulting
distribution so the claim can be checked rather than asserted.

Usage from build_cjk.py::

    from harmonize import harmonize_font
    report = harmonize_font(base, cjk_names, "assets/design-dna.json")
"""
import json
import math
import os
import sys

from array import array
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates


# ---------------------------------------------------------------------------
# Design parameters derived from assets/design-dna.json
# ---------------------------------------------------------------------------

def load_targets(path):
    with open(path, encoding="utf-8") as fh:
        dna = json.load(fh)

    upem = 2000
    px_to_units = upem / float(dna["sample_px"])          # 1000 px -> 2000 upem

    cjk_v = dna["CJK_vertical_px"] * px_to_units
    cjk_h = dna["CJK_horizontal_px"] * px_to_units
    latin_ratio = float(dna["latin_contrast_ratio"])       # stem / crossbar
    target_h = cjk_v / latin_ratio                         # keep verticals, thicken horizontals

    # Prototyped and deliberately disabled. Pushing every near-horizontal
    # point along its local normal twists long horizontal edges (the two
    # ends get different normals) into self-intersecting slants, and
    # FreeType's scan converter then overflows at >= 800 px. Contrast is
    # aligned by selecting the closest CJK source weight instead; see
    # docs/DESIGN.md for the full experiment log.
    delta = 0.0

    # Serif head. The Latin I head is 2.794x its stem, but transferring that
    # literally to a dense Han square makes an oversized flag. The adaptation
    # factor is explicit and documented in docs/DESIGN.md.
    adaptation = 0.45
    head = target_h * float(dna["targets"]["serif_head_over_stem"]) * adaptation
    # No horizontal extension: a Han square has no room to grow outward, and
    # an extension on an inner contour produces detached hairlines. The
    # serif head is a vertical flat cut at the existing terminal x instead.
    ext = 0.0
    bracket = float(dna["targets"]["bracket_transition_frac_of_cap"])

    shear = math.tan(math.radians(float(dna["targets"]["stress_shear_deg"]))) * 0.40

    return {
        "dna": dna,
        "upem": upem,
        "cjk_vertical_units": round(cjk_v, 2),
        "cjk_horizontal_units": round(cjk_h, 2),
        "target_horizontal_units": round(target_h, 2),
        "edge_delta_units": round(delta, 3),
        "serif_head_units": round(head, 2),
        "serif_extension_units": round(ext, 2),
        "bracket_frac": bracket,
        "shear": round(shear, 6),
        "adaptation": adaptation,
        "horiz_slope": 0.30,       # |dy| <= 0.30 * |dx| counts as horizontal
        # Measured on U+4E00: the right triangular tip turns 59 degrees
        # (cos 0.51) and the left tip has a mostly-horizontal normal
        # (|ny| 0.30). Both must be accepted or the wedge survives.
        "corner_cos": 0.62,
        "min_vertical_normal": 0.30,
        "max_terminals": 6,        # per glyph
        "max_terminals_per_contour": 2,
        "x_extremum_eps": 2.0,
        "max_points": 400,        # above this, keep contrast/stress only
        "hard_max_points": 1400,  # above this, pass the glyph through
    }


# ---------------------------------------------------------------------------
# Small geometry helpers
# ---------------------------------------------------------------------------

def _norm(v):
    x, y = v
    n = math.hypot(x, y)
    return (0.0, 0.0) if n < 1e-9 else (x / n, y / n)


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _signed_area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def _centroid(pts):
    n = float(len(pts))
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)


# ---------------------------------------------------------------------------
# Per-contour transformation
# ---------------------------------------------------------------------------

def _transform_contour(coords, flags, t, is_outer=True):
    """Return (new_coords, new_flags, n_edge, n_terminal, skipped)."""
    n = len(coords)
    if n < 3:
        return coords, flags, 0, 0, "too_few_points"

    pts = [(float(p[0]), float(p[1])) for p in coords]
    fl = [int(f) for f in flags]
    c = _centroid(pts)
    cy = c[1]
    hard = t["hard_max_points"]
    if n > hard:
        return coords, flags, 0, 0, "passthrough_large"

    # Outward normal is fixed by the contour winding, not by a per-point
    # centroid test. A centroid test flips at the two ends of one long
    # horizontal edge and twists it into a self-intersecting slant, which
    # makes FreeType's scan converter overflow at large sizes.
    area = _signed_area(pts)
    winding = -1 if area < 0 else 1

    def outward_normal(p, tangent):
        if winding < 0:                    # clockwise: outside is to the right
            return _norm((tangent[1], -tangent[0]))
        return _norm((-tangent[1], tangent[0]))

    moved = []
    for i in range(n):
        prev = pts[(i - 1) % n]
        nxt = pts[(i + 1) % n]
        tan = _norm((nxt[0] - prev[0], nxt[1] - prev[1]))
        ax, ay = abs(tan[0]), abs(tan[1])
        horizontal = ax > 1e-9 and ay <= t["horiz_slope"] * ax
        w = _smoothstep(1.0 - ay / (t["horiz_slope"] * ax + 1e-9)) if horizontal else 0.0
        nx, ny = outward_normal(pts[i], tan) if w > 0 else (0.0, 0.0)
        d = t["edge_delta_units"] * w
        # Stress shear is applied to every point, not only horizontal edges.
        sx = t["shear"] * (pts[i][1] - cy)
        moved.append((pts[i][0] + nx * d + sx, pts[i][1] + ny * d))

    n_edge = sum(
        1 for i in range(n)
        if abs(_norm((pts[(i + 1) % n][0] - pts[(i - 1) % n][0],
                      pts[(i + 1) % n][1] - pts[(i - 1) % n][1]))[1])
        <= t["horiz_slope"] *
        abs(_norm((pts[(i + 1) % n][0] - pts[(i - 1) % n][0],
                   pts[(i + 1) % n][1] - pts[(i - 1) % n][1]))[0])
    )

    # Terminal rebuild: replace a sharp horizontal-end on-curve point with a
    # flat bracketed head. Topology is preserved (one point becomes three).
    # Terminal rebuild is deliberately narrow. Only sharp x-extremum points
    # on OUTER contours can be horizontal-stroke tips. Inner contours, fold
    # corners and dense glyphs keep the contrast/stress transform but are not
    # rewritten, which prevents the detached hairlines a loose detector makes.
    if n > t["max_points"]:
        return moved, array("B", fl), n_edge, 0, "partial_no_terminals"
    if not is_outer:
        return moved, array("B", fl), n_edge, 0, "inner_contour"

    out_pts, out_fl, terminals, per_contour = [], [], 0, 0
    head_half = t["serif_head_units"] / 2.0
    cos_limit = t["corner_cos"]
    eps = t["x_extremum_eps"]

    for i in range(n):
        p = moved[i]
        prev = moved[(i - 1) % n]
        nxt = moved[(i + 1) % n]
        is_on = bool(fl[i] & 1)
        t1 = _norm((p[0] - prev[0], p[1] - prev[1]))
        t2 = _norm((nxt[0] - p[0], nxt[1] - p[1]))
        cos_t = t1[0] * t2[0] + t1[1] * t2[1]
        sharp = cos_t < cos_limit
        tip = ((p[0] > prev[0] + eps and p[0] > nxt[0] + eps) or
               (p[0] < prev[0] - eps and p[0] < nxt[0] - eps))
        nx, ny = outward_normal(p, t1)
        vertical_cut = abs(ny) >= t["min_vertical_normal"]
        if (is_on and sharp and tip and vertical_cut and
                per_contour < t["max_terminals_per_contour"] and
                terminals < t["max_terminals"]):
            # Strictly vertical flat cut. x is left untouched: expanding
            # along the oblique normal made the lower head point fold back
            # into the following contour points, which FreeType could not
            # subdivide at large sizes (raster overflow). Keeping x fixed
            # also matches the measured Latin serif: the head is 2.79x the
            # stem in the vertical direction, with no outward extension.
            right_tip = p[0] > prev[0] and p[0] > nxt[0]
            sign_x = 1.0 if right_tip else -1.0
            top = (p[0], p[1] + head_half)
            bot = (p[0], p[1] - head_half)
            ctrl = (p[0] - sign_x * head_half * 0.15, p[1])
            out_pts.extend([top, ctrl, bot])
            out_fl.extend([1, 0, 1])
            terminals += 1
            per_contour += 1
        else:
            out_pts.append(p)
            out_fl.append(fl[i])

    skipped = None if terminals else "no_terminal_found"
    return out_pts, array("B", out_fl), n_edge, terminals, skipped


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def harmonize_font(font, glyph_names, dna_path, report_path=None):
    t = load_targets(dna_path)
    glyf = font["glyf"]
    total = len(glyph_names)
    stats = {
        "engine": "harmonize.py",
        "dna": os.path.basename(dna_path),
        "parameters": {k: v for k, v in t.items() if k != "dna"},
        "glyphs_total": total,
        "glyphs_full": 0,
        "glyphs_partial": 0,
        "glyphs_passthrough": 0,
        "glyphs_no_terminal": 0,
        "terminals_total": 0,
        "edge_points_total": 0,
        "points_before": 0,
        "points_after": 0,
        "reasons": {},
        "failures": [],
    }

    for idx, name in enumerate(glyph_names):
        g = glyf[name]
        if g.numberOfContours == 0:
            stats["glyphs_passthrough"] += 1
            continue
        try:
            coords = g.coordinates
            flags = g.flags
            ends = list(g.endPtsOfContours)
            before = len(coords)
            stats["points_before"] += before

            # TrueType outer and inner contours wind in opposite directions.
            # The largest contour defines the outer winding for this glyph.
            areas = []
            for ci, end in enumerate(ends):
                s = 0 if ci == 0 else ends[ci - 1] + 1
                areas.append(_signed_area(
                    [(float(p[0]), float(p[1])) for p in coords[s:end + 1]]))
            largest = max(range(len(areas)), key=lambda i: abs(areas[i]))
            outer_sign = 1 if areas[largest] >= 0 else -1

            new_coords, new_flags, new_ends = [], [], []
            off, edge_n, term_n, reasons = 0, 0, 0, []
            for ci, end in enumerate(ends):
                start = 0 if ci == 0 else ends[ci - 1] + 1
                cc = list(coords[start:end + 1])
                cf = list(flags[start:end + 1])
                sign = 1 if areas[ci] >= 0 else -1
                oc, of, en, tn, skip = _transform_contour(cc, cf, t, sign == outer_sign)
                new_coords.extend([(float(x), float(y)) for x, y in oc])
                new_flags.extend([int(f) for f in of])
                new_ends.append(off + len(oc) - 1)
                off += len(oc)
                edge_n += en
                term_n += tn
                if skip:
                    reasons.append(skip)

            # Consistency invariant: flags and coordinates must stay aligned.
            if len(new_coords) != len(new_flags):
                raise ValueError("coord/flag length mismatch")

            g.coordinates = GlyphCoordinates(new_coords)
            g.flags = array("B", new_flags)
            g.endPtsOfContours = new_ends
            g.numberOfContours = len(new_ends)
            g.recalcBounds(glyf)

            after = len(new_coords)
            stats["points_after"] += after
            stats["edge_points_total"] += edge_n
            stats["terminals_total"] += term_n

            hard = any(r == "passthrough_large" for r in reasons)
            partial = any(r == "partial_no_terminals" for r in reasons)
            if hard:
                stats["glyphs_passthrough"] += 1
            elif partial:
                stats["glyphs_partial"] += 1
            elif term_n == 0:
                stats["glyphs_no_terminal"] += 1
            else:
                stats["glyphs_full"] += 1
            for r in reasons:
                stats["reasons"][r] = stats["reasons"].get(r, 0) + 1
        except Exception as exc:
            stats["failures"].append([name, type(exc).__name__, str(exc)[:120]])
            stats["glyphs_passthrough"] += 1
            if len(stats["failures"]) >= 50:
                stats["failures"].append(["...", "truncated", ""])
                break

        if (idx + 1) % 5000 == 0:
            print("  harmonized %d / %d" % (idx + 1, total), file=sys.stderr)

    stats["terminals_per_glyph"] = round(
        stats["terminals_total"] / max(total, 1), 3)
    stats["point_growth_pct"] = round(
        (stats["points_after"] / max(stats["points_before"], 1) - 1) * 100, 2)
    stats["full_coverage_pct"] = round(
        stats["glyphs_full"] / max(total, 1) * 100, 2)

    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(stats, fh, ensure_ascii=False, indent=2)

    print("harmonize: %d glyphs | full %d | partial %d | passthrough %d | "
          "terminals %d | +%.1f%% points" % (
              total, stats["glyphs_full"], stats["glyphs_partial"],
              stats["glyphs_passthrough"], stats["terminals_total"],
              stats["point_growth_pct"]))
    return stats


if __name__ == "__main__":
    import argparse
    from fontTools.ttLib import TTFont

    ap = argparse.ArgumentParser()
    ap.add_argument("font")
    ap.add_argument("--dna", default="assets/design-dna.json")
    ap.add_argument("--report", default="assets/harmony-report.json")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    f = TTFont(a.font)
    cm = f.getBestCmap()
    names = sorted({cm[c] for c in cm if 0x2E80 <= c <= 0x9FFF or
                    0x20000 <= c <= 0x323AF or 0xF900 <= c <= 0xFAFF or
                    0xFE30 <= c <= 0xFE4F or 0xFF00 <= c <= 0xFFEF})
    if a.limit:
        names = names[:a.limit]
    harmonize_font(f, names, a.dna, a.report)
    print(json.dumps({k: v for k, v in load_targets(a.dna).items() if k != "dna"},
                     ensure_ascii=False, indent=2))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify a locally built font without needing any reference file."""
import argparse
import os
import sys

from fontTools.ttLib import TTFont

EXPECTED = {
    "cjk":          (31724, 31595),
    "cjk-bold":     (31724, 31595),
    "multilingual": (33897, 33768),
    "full":         (47092, 46963),
    "signature":    (31724, 31595),
}

SAMPLES = {
    "Latin":   [0x0041, 0xFB01, 0x00E9],
    "CJK":     [0x4E00, 0x4E2D, 0x9FA5, 0x2000B, 0x3002, 0xFF0C],
    "LGC":     [0x0180, 0x03B1, 0x1F00, 0x0416, 0xA640, 0x20AC],
    "Kana":    [0x3042, 0x30A2, 0x31F0, 0x3190],
    "Hangul":  [0xAC00, 0xD7A3, 0x1100, 0x3131, 0xA960, 0xD7B0],
    "Symbols": [0x320E, 0x337F, 0x2460, 0x2160, 0x2500, 0x1F200],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("font", help="TTF or WOFF2 produced by build_cjk.py")
    ap.add_argument("--preset", choices=sorted(EXPECTED), default=None,
                    help="also check exact glyph / code point counts")
    args = ap.parse_args()

    f = TTFont(args.font)
    cm = f.getBestCmap()
    glyphs = f["maxp"].numGlyphs
    codes = len(cm)

    print("file          : %s (%.2f MB)" % (
        args.font, os.path.getsize(args.font) / 1048576))
    print("family        : %s" % f["name"].getDebugName(1))
    print("subfamily     : %s" % f["name"].getDebugName(2))
    print("version       : %s" % f["name"].getDebugName(5))
    print("upem          : %d" % f["head"].unitsPerEm)
    h = f["hhea"]
    print("hhea          : %d / %d / %d" % (h.ascent, h.descent, h.lineGap))
    print("glyphs        : %d" % glyphs)
    print("code points   : %d" % codes)
    print("non-BMP       : %d" % sum(1 for c in cm if c > 0xFFFF))
    print("GSUB / GPOS   : %d / %d" % (
        len(f["GSUB"].table.FeatureList.FeatureRecord),
        len(f["GPOS"].table.FeatureList.FeatureRecord)))
    print("cmap subtables: %s" % [
        (t.platformID, t.platEncID, t.format, len(t.cmap))
        for t in f["cmap"].tables])
    print("unique names  : %s" % (
        len(set(f.getGlyphOrder())) == len(f.getGlyphOrder())))
    print("full-width CJK: %s" % all(
        f["hmtx"][cm[cp]][0] == f["head"].unitsPerEm
        for cp in (0x4E00, 0x4E2D, 0x6587) if cp in cm))

    failures = []
    if args.preset:
        want_g, want_c = EXPECTED[args.preset]
        if (glyphs, codes) != (want_g, want_c):
            failures.append("expected %d glyphs / %d codes, got %d / %d" % (
                want_g, want_c, glyphs, codes))

    print("\ncharacter samples")
    for group, cps in SAMPLES.items():
        present = sum(1 for cp in cps if cp in cm)
        print("  %-10s %d/%d  %s" % (
            group, present, len(cps),
            " ".join("U+%05X" % cp for cp in cps[:3])))

    # Every preset must at least cover Latin and CJK.
    for cp in SAMPLES["Latin"] + SAMPLES["CJK"]:
        if cp not in cm:
            failures.append("missing mandatory U+%05X" % cp)
    if "Anthropic" in (f["name"].getDebugName(1) or ""):
        print("\nNOTE: internal family still contains the upstream brand name.")

    print()
    if failures:
        for line in failures:
            print("FAIL:", line)
        sys.exit(1)
    print("OK: structure and mandatory characters verified.")


if __name__ == "__main__":
    main()

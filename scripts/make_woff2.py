#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert a locally built TTF to WOFF2. Never commit the output."""
import argparse
import os
import time

from fontTools.ttLib import TTFont


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ttf", help="input TTF produced by build_cjk.py")
    ap.add_argument("-o", "--out", default=None,
                    help="output WOFF2 (default: same stem, .woff2)")
    args = ap.parse_args()

    dst = args.out or os.path.splitext(args.ttf)[0] + ".woff2"
    outdir = os.path.dirname(os.path.abspath(dst))
    os.makedirs(outdir, exist_ok=True)

    t0 = time.time()
    f = TTFont(args.ttf)
    f.flavor = "woff2"
    f.save(dst)
    check = TTFont(dst)
    print("input  %s  %.2f MB" % (args.ttf, os.path.getsize(args.ttf) / 1048576))
    print("output %s  %.2f MB  %.1fs" % (
        dst, os.path.getsize(dst) / 1048576, time.time() - t0))
    print("glyphs %d | codes %d | flavor %s" % (
        check["maxp"].numGlyphs, len(check.getBestCmap()), check.flavor))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild a multilingual serif font from source, locally.

This repository ships NO font binaries. You supply a legally obtained copy
of the upstream Latin font, plus the two SIL OFL source families, and this
script produces the composite on your own machine. See docs/COMPLIANCE.md
for why the binaries are deliberately absent.

The Latin font is the base: every original glyph id, advance, metric and
OpenType layout lookup is preserved. New glyphs are always APPENDED, never
inserted, so existing GSUB/GPOS lookups keep pointing at the right glyphs.

Outline sources:

  * CJK, kana, Hangul, CJK symbols: Noto Serif CJK SC (Source Han Serif),
    CFF cubic outlines. Converted with cu2qu to TrueType quadratics and
    scaled from 1000 to 2000 UPM.
  * Latin Extended / Greek / Cyrillic: Noto Serif variable font instanced
    at wght=500, glyf outlines decomposed and scaled to 2000 UPM.

Four presets reproduce the four coverage levels. One command each:

    python3 scripts/build_cjk.py \
        --latin /path/to/your/AnthropicSerifWebText.ttf \
        --source-dir /path/to/noto-fonts \
        --preset cjk

    # other presets: cjk-bold, multilingual, full

By default the output is written to build/ (gitignored) and the internal
family name is changed to "Serif CJK Extension", so the result carries no
upstream brand name. Pass --keep-upstream-name to reproduce the original
naming exactly, or --family-name "Your Name" to choose another.

The --source-dir directory must contain NotoSerifCJK-Medium.ttc (and
Bold.ttc for the cjk-bold preset) and, for the multilingual / full presets,
a Noto Serif variable font. Override individual paths with --cjk-ttc and
--lgc-font. See docs/BUILD.md for the exact layout.

Requires: fontTools; brotli only for scripts/make_woff2.py.
Both outline sources are under the SIL Open Font License 1.1; see OFL.txt
and FONTLOG.txt. The upstream Latin font is proprietary and is NOT
relicensed by this script.
"""
import argparse
import os
import sys
import time

from fontTools.ttLib import TTCollection, TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.varLib.instancer import instantiateVariableFont


# ------------------------------------------------------------------ ranges
# Chinese-related ranges. Kana, Hangul, Greek and Cyrillic are excluded here
# because they are either out of scope or supplied by the dedicated LGC font.
CJK_RANGES = (
    (0x2E80, 0x2FDF),    # CJK radicals supplement, Kangxi radicals
    (0x2FF0, 0x2FFF),    # ideographic description characters
    (0x3000, 0x303F),    # CJK symbols and punctuation
    (0x3100, 0x312F),    # bopomofo
    (0x31A0, 0x31BF),    # bopomofo extended
    (0x31C0, 0x31EF),    # CJK strokes
    (0x3400, 0x4DBF),    # extension A
    (0x4E00, 0x9FFF),    # unified ideographs, basic block
    (0xF900, 0xFAFF),    # compatibility ideographs
    (0xFE10, 0xFE1F),    # vertical forms
    (0xFE30, 0xFE4F),    # CJK compatibility forms
    (0xFF00, 0xFFEF),    # halfwidth and fullwidth forms
    (0x20000, 0x2EBEF),  # extensions B through F
    (0x2F800, 0x2FA1F),  # compatibility ideographs supplement
    (0x30000, 0x323AF),  # extensions G through I
)

# Latin Extended, Greek, Cyrillic and the shared marks needed to typeset them.
# (name, start, end, group)
LGC_RANGES = (
    ("Latin-1 Supplement",              0x0080, 0x00FF, "latin"),
    ("Latin Extended-A",               0x0100, 0x017F, "latin"),
    ("Latin Extended-B",               0x0180, 0x024F, "latin"),
    ("IPA Extensions",                 0x0250, 0x02AF, "latin"),
    ("Phonetic Extensions",            0x1D00, 0x1D7F, "latin"),
    ("Phonetic Extensions Supplement", 0x1D80, 0x1DBF, "latin"),
    ("Latin Extended Additional",      0x1E00, 0x1EFF, "latin"),
    ("Latin Extended-C",               0x2C60, 0x2C7F, "latin"),
    ("Latin Extended-D",               0xA720, 0xA7FF, "latin"),
    ("Latin Extended-E",               0xAB30, 0xAB6F, "latin"),
    ("Latin Extended-F",               0x10780, 0x107BF, "latin"),
    ("Latin Extended-G",               0x1DF00, 0x1DFFF, "latin"),
    ("Greek and Coptic",               0x0370, 0x03FF, "greek"),
    ("Greek Extended",                 0x1F00, 0x1FFF, "greek"),
    ("Cyrillic",                       0x0400, 0x04FF, "cyrillic"),
    ("Cyrillic Supplement",            0x0500, 0x052F, "cyrillic"),
    ("Cyrillic Extended-A",            0x2DE0, 0x2DFF, "cyrillic"),
    ("Cyrillic Extended-B",            0xA640, 0xA69F, "cyrillic"),
    ("Cyrillic Extended-C",            0x1C80, 0x1C8F, "cyrillic"),
    ("Combining Diacritical Marks",    0x0300, 0x036F, "support"),
    ("Spacing Modifier Letters",       0x02B0, 0x02FF, "support"),
    ("General Punctuation",            0x2000, 0x206F, "support"),
    ("Superscripts and Subscripts",    0x2070, 0x209F, "support"),
    ("Currency Symbols",               0x20A0, 0x20CF, "support"),
    ("Letterlike Symbols",             0x2100, 0x214F, "support"),
    ("Number Forms",                   0x2150, 0x218F, "support"),
)

DEBUG_SAMPLE = (
    0x4E00, 0x4E2D, 0x6587, 0x5B57, 0x6392, 0x7248, 0x8BBE, 0x8BA1,
    0x4E16, 0x754C, 0x4F60, 0x597D, 0x3002, 0xFF0C, 0x3001, 0xFF1A,
    0x0100, 0x03B1, 0x0416, 0x1F00,
    0x3042, 0x3044, 0x30A2, 0x30AB, 0xAC00, 0xD55C, 0xAE00, 0x1100,
)


def in_ranges(cp, ranges):
    return any(lo <= cp <= hi for lo, hi in ranges)


def set_name(font, name_id, value):
    """Replace every record of a name ID with a single bilingual value."""
    table = font["name"]
    for rec in list(table.names):
        if rec.nameID == name_id:
            table.names.remove(rec)
    table.setName(value, name_id, 3, 1, 0x409)
    table.setName(value, name_id, 1, 0, 0)


def rename_family(font, family):
    sub = font["name"].getDebugName(2) or "Regular"
    ps = family.replace(" ", "") + "-" + sub.replace(" ", "")
    for nid, value in ((1, family), (4, family + " " + sub),
                       (6, ps), (16, family), (17, sub)):
        set_name(font, nid, value)


def add_cjk_glyphs(base, used, glyf, hmtx, cjk, scale, max_err, todo, prefix=""):
    """CFF cubic charstrings -> TrueType quadratic glyphs."""
    cmap = cjk.getBestCmap()
    charstrings = cjk["CFF "].cff.topDictIndex[0].CharStrings
    new_names, new_cps, failed = [], {}, []
    for i, cp in enumerate(todo):
        src_name = cmap[cp]
        pen = TTGlyphPen(None)
        cu = Cu2QuPen(TransformPen(pen, (scale, 0, 0, scale, 0, 0)),
                      max_err=max_err, reverse_direction=True)
        try:
            charstrings[src_name].draw(cu)
            glyph = pen.glyph()
            glyph.recalcBounds(None)
        except Exception as exc:
            failed.append((hex(cp), type(exc).__name__, str(exc)[:80]))
            continue
        name = ("uni%04X" % cp) if cp <= 0xFFFF else ("u%X" % cp)
        if name in used:
            name = "x%X" % cp
        used.add(name)
        glyf.glyphs[name] = glyph
        advance = int(round(cjk["hmtx"][src_name][0] * scale))
        lsb = glyph.xMin if glyph.numberOfContours > 0 else 0
        hmtx.metrics[name] = (advance, lsb)
        new_names.append(name)
        new_cps[cp] = name
        if (i + 1) % 5000 == 0:
            print("  CJK converted %d / %d" % (i + 1, len(todo)))
    return new_names, new_cps, failed


def add_lgc_glyphs(base, used, glyf, hmtx, lgc, scale, todo):
    """Decompose composite glyf outlines and scale them to the base UPM."""
    cmap = lgc.getBestCmap()
    glyph_set = lgc.getGlyphSet()
    new_names, new_cps, failed = [], {}, []
    dedup = {}  # source glyph name -> generated name, for shared cmap entries
    for i, cp in enumerate(todo):
        src_name = cmap[cp]
        if src_name in dedup:
            new_cps[cp] = dedup[src_name]
            continue
        pen = TTGlyphPen(None)
        transform = TransformPen(pen, (scale, 0, 0, scale, 0, 0))
        decompose = DecomposingRecordingPen(glyph_set)
        try:
            glyph_set[src_name].draw(decompose)
            decompose.replay(transform)
            glyph = pen.glyph()
            glyph.recalcBounds(None)
        except Exception as exc:
            failed.append((hex(cp), type(exc).__name__, str(exc)[:80]))
            continue
        # A fixed prefix keeps these names from colliding with CJK uniXXXX.
        name = "lgc%X" % cp
        if name in used:
            name = "x%X" % cp
        used.add(name)
        dedup[src_name] = name
        glyf.glyphs[name] = glyph
        advance = int(round(lgc["hmtx"][src_name][0] * scale))
        lsb = glyph.xMin if glyph.numberOfContours > 0 else 0
        hmtx.metrics[name] = (advance, lsb)
        new_names.append(name)
        new_cps[cp] = name
        if (i + 1) % 1000 == 0:
            print("  LGC converted %d / %d" % (i + 1, len(todo)))
    return new_names, new_cps, failed


PRESETS = {
    "cjk": dict(weight="Medium", lgc=False, full=False,
                suffix="CJK", version="Version 1.000"),
    "cjk-bold": dict(weight="Bold", lgc=False, full=False,
                     suffix="CJK-Bold", version="Version 1.000 CJK Bold"),
    "multilingual": dict(weight="Medium", lgc=True, full=False,
                         suffix="Multilingual", version="Version 1.100"),
    "full": dict(weight="Medium", lgc=True, full=True,
                 suffix="Full", version="Version 1.200"),
    "signature": dict(weight="Regular", lgc=False, full=False, harmonize=True,
                      suffix="Signature", version="Version 1.300 Signature"),
}

DEFAULT_FAMILY = "Serif CJK Extension"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--latin", required=True,
                    help="your own legally obtained copy of the upstream Latin TTF")
    ap.add_argument("--preset", choices=sorted(PRESETS), default=None,
                    help="coverage/weight preset; sets most other options")
    ap.add_argument("--source-dir", default=None,
                    help="directory holding the Noto Serif CJK TTCs and the "
                         "Noto Serif variable font")
    ap.add_argument("--cjk-ttc", default=None, help="Noto Serif CJK TTC or OTF")
    ap.add_argument("--cjk-face", type=int, default=2,
                    help="TTC face index, 2 = Simplified Chinese (default)")
    ap.add_argument("--lgc-font", default=None,
                    help="Noto Serif variable font for Latin/Greek/Cyrillic")
    ap.add_argument("--lgc-weight", type=float, default=500,
                    help="instance wght of the LGC source (default 500)")
    ap.add_argument("--out", default=None, help="output TTF path")
    ap.add_argument("--max-err", type=float, default=0.5,
                    help="cu2qu max error in source units (default 0.5)")
    ap.add_argument("--family-name", default=None,
                    help="replace internal family names (default: %s)" % DEFAULT_FAMILY)
    ap.add_argument("--keep-upstream-name", action="store_true",
                    help="keep the upstream family name instead of renaming")
    ap.add_argument("--version-string", default=None,
                    help="override the nameID 5 version string")
    ap.add_argument("--no-cjk", action="store_true", help="skip the CJK source")
    ap.add_argument("--no-lgc", action="store_true", help="skip the LGC source")
    ap.add_argument("--full", action="store_true",
                    help="add every remaining CJK source code point: kana, "
                         "Hangul syllables/jamo and CJK symbols")
    ap.add_argument("--harmonize", action="store_true",
                    help="redraw CJK stroke terminals with the Latin design grammar")
    ap.add_argument("--dna", default="assets/design-dna.json",
                    help="measured design DNA (see scripts/measure_dna.py)")
    ap.add_argument("--harmony-report", default="assets/harmony-report.json",
                    help="where to write the consistency report")
    ap.add_argument("--limit", type=int, default=0,
                    help="convert only a small sample, for debugging")
    args = ap.parse_args()

    # ------------------------------------------------------------- presets
    if args.preset:
        p = PRESETS[args.preset]
        args.full = p["full"]
        args.no_lgc = not p["lgc"]
        if p.get("harmonize"):
            args.harmonize = True
        if args.version_string is None:
            args.version_string = p["version"]
        if args.out is None:
            args.out = os.path.join("build", "SerifCJKExtension-%s.ttf" % p["suffix"])
        if args.cjk_ttc is None:
            if not args.source_dir:
                sys.exit("--preset needs --source-dir or --cjk-ttc")
            args.cjk_ttc = os.path.join(
                args.source_dir, "NotoSerifCJK-%s.ttc" % p["weight"])
        if p["lgc"] and args.lgc_font is None:
            if not args.source_dir:
                sys.exit("this preset needs --source-dir or --lgc-font")
            for candidate in ("NotoSerif[wdth,wght].ttf",
                              "NotoSerif-VF.ttf", "NotoSerif[wght].ttf"):
                path = os.path.join(args.source_dir, candidate)
                if os.path.isfile(path):
                    args.lgc_font = path
                    break
            if args.lgc_font is None:
                sys.exit("Noto Serif variable font not found in --source-dir; "
                         "pass --lgc-font explicitly")
    if args.out is None:
        sys.exit("provide --out or use --preset")
    if args.family_name is None and not args.keep_upstream_name:
        args.family_name = DEFAULT_FAMILY
    outdir = os.path.dirname(os.path.abspath(args.out))
    if outdir and not os.path.isdir(outdir):
        os.makedirs(outdir, exist_ok=True)

    for path in (args.latin, args.cjk_ttc, args.lgc_font):
        if path and not os.path.isfile(path):
            sys.exit("input file not found: %s" % path)
    if (args.no_cjk or args.cjk_ttc is None) and (args.no_lgc or args.lgc_font is None):
        sys.exit("nothing to do: provide --cjk-ttc and/or --lgc-font")

    t0 = time.time()
    base = TTFont(args.latin)
    upem = base["head"].unitsPerEm
    orig_order = list(base.getGlyphOrder())
    orig_cps = set(cp for t in base["cmap"].tables for cp in t.cmap.keys())
    print("Latin base: %s | upem %d | glyphs %d | code points %d" %
          (base["name"].getDebugName(1) or "(unnamed)", upem,
           len(orig_order), len(orig_cps)))

    glyf = base["glyf"]
    hmtx = base["hmtx"]
    for name in orig_order:
        _ = glyf[name]  # force decoding of lazy glyph data
    used = set(orig_order)
    all_new, all_cps = [], {}
    cjk_names = []

    # ---------------------------------------------------------------- CJK
    if not args.no_cjk and args.cjk_ttc:
        if args.cjk_ttc.lower().endswith(".ttc"):
            cjk = TTCollection(args.cjk_ttc, lazy=False).fonts[args.cjk_face]
        else:
            cjk = TTFont(args.cjk_ttc)
        scale = upem / cjk["head"].unitsPerEm
        print("CJK source: %s | upem %d | scale %.3f" %
              (cjk["name"].getDebugName(1) or "(unnamed)",
               cjk["head"].unitsPerEm, scale))
        cjk_cmap = cjk.getBestCmap()
        if args.full:
            # Complete build: take everything the CJK source has, except
            # code points the LGC source can actually supply. Excluding only
            # the LGC source's real cmap (not its nominal ranges) matters:
            # the LGC font lacks characters such as U+2160 ROMAN NUMERAL ONE,
            # which must then come from the CJK source to avoid a gap.
            lgc_available = set()
            if args.lgc_font and not args.no_lgc:
                probe = TTFont(args.lgc_font, lazy=True)
                lgc_available = set(probe.getBestCmap())
                probe.close()
            cjk_todo = sorted(cp for cp in cjk_cmap
                              if cp not in orig_cps and cp not in lgc_available)
            print("CJK source: complete mode (kana, Hangul, CJK symbols)")
        else:
            cjk_todo = sorted(cp for cp in cjk_cmap
                              if in_ranges(cp, CJK_RANGES) and cp not in orig_cps)
        if args.limit:
            cjk_todo = [cp for cp in DEBUG_SAMPLE
                        if cp in cjk_cmap and cp not in orig_cps]
        print("CJK code points to add: %d" % len(cjk_todo))
        names, mapping, failed = add_cjk_glyphs(
            base, used, glyf, hmtx, cjk, scale, args.max_err, cjk_todo)
        print("CJK converted %d, failed %d %s" % (len(names), len(failed), failed[:5]))
        cjk_names = list(names)
        all_new += names
        all_cps.update(mapping)

    # ------------------------------------------------------- LGC (Lat/Grk/Cyr)
    lgc = None
    if not args.no_lgc and args.lgc_font:
        vf = TTFont(args.lgc_font, lazy=False)
        if "fvar" in vf:
            loc = {"wght": args.lgc_weight}
            for axis in vf["fvar"].axes:
                if axis.axisTag == "wdth":
                    loc["wdth"] = axis.defaultValue
            lgc = instantiateVariableFont(vf, loc, inplace=False, optimize=True)
            print("LGC source: %s | instanced %s" %
                  (vf["name"].getDebugName(1) or "(unnamed)", loc))
        else:
            lgc = vf
            print("LGC source: %s (static)" % (vf["name"].getDebugName(1) or "(unnamed)"))
        scale = upem / lgc["head"].unitsPerEm
        lgc_cmap = lgc.getBestCmap()
        lgc_todo = sorted(cp for cp in lgc_cmap
                          if in_ranges(cp, [(a, b) for _, a, b, _ in LGC_RANGES])
                          and cp not in orig_cps and cp not in all_cps)
        if args.limit:
            lgc_todo = [cp for cp in DEBUG_SAMPLE
                        if cp in lgc_cmap and cp not in orig_cps][:4]
        print("LGC code points to add: %d" % len(lgc_todo))
        names, mapping, failed = add_lgc_glyphs(
            base, used, glyf, hmtx, lgc, scale, lgc_todo)
        print("LGC converted %d, failed %d %s" % (len(names), len(failed), failed[:5]))
        all_new += names
        all_cps.update(mapping)

    if not all_new:
        sys.exit("no glyphs produced")
    print("total new glyphs: %d" % len(all_new))

    # ---------------------------------------------------------- signature
    if args.harmonize:
        if not cjk_names:
            sys.exit("--harmonize needs the CJK source")
        if not os.path.isfile(args.dna):
            sys.exit("design DNA not found: %s (run scripts/measure_dna.py first)" % args.dna)
        try:
            from harmonize import harmonize_font
        except ImportError:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from harmonize import harmonize_font
        print("signature mode: redrawing CJK terminals from %s" % args.dna)
        harmonize_font(base, cjk_names, args.dna, args.harmony_report)
        print("Western outlines untouched: %d glyphs" % len(orig_order))

    # Append only: all original glyph ids stay valid, so GSUB/GPOS survive.
    base.setGlyphOrder(orig_order + all_new)
    total = len(orig_order) + len(all_new)
    base["maxp"].numGlyphs = total
    base["hhea"].numberOfHMetrics = total

    # BMP characters go into the existing format 4 subtables.
    for sub in base["cmap"].tables:
        if sub.format in (4, 6) and sub.platformID in (0, 3):
            for cp, name in all_cps.items():
                if cp <= 0xFFFF:
                    sub.cmap[cp] = name

    # Format 12 carries every code point, including non-BMP CJK extensions
    # and the Latin Extended-F/G planes.
    full = {}
    for sub in base["cmap"].tables:
        if sub.platformID in (0, 3) and not (sub.platformID == 3 and sub.platEncID == 10):
            full.update(sub.cmap)
    full.update(all_cps)
    sub12 = CmapSubtable.newSubtable(12)
    sub12.platformID, sub12.platEncID = 3, 10
    sub12.format, sub12.language = 12, 0
    sub12.cmap = dict(sorted(full.items()))
    base["cmap"].tables.append(sub12)

    os2 = base["OS/2"]
    os2.usFirstCharIndex = min(full)
    os2.usLastCharIndex = 0xFFFF
    for i in range(1, 5):
        setattr(os2, "usUnicodeRange%d" % i, 0xFFFFFFFF)

    xmin = ymin = 10 ** 9
    xmax = ymax = -10 ** 9
    for name in base.getGlyphOrder():
        g = glyf[name]
        if g.numberOfContours > 0:
            xmin, ymin = min(xmin, g.xMin), min(ymin, g.yMin)
            xmax, ymax = max(xmax, g.xMax), max(ymax, g.yMax)
    head = base["head"]
    head.xMin, head.yMin, head.xMax, head.yMax = xmin, ymin, xmax, ymax
    base["maxp"].recalc(base)
    try:
        base["hhea"].recalc(base)
    except Exception as exc:
        print("hhea recalc skipped:", exc)

    # ------------------------------------------------------------ attribution
    copyright_cjk = ""
    if not args.no_cjk and args.cjk_ttc:
        copyright_cjk = str(cjk["name"].getDebugName(0) or "")
    copyright_lgc = ""
    if lgc is not None:
        copyright_lgc = str(lgc["name"].getDebugName(0) or "")
    notice = "CJK glyph outlines: " + copyright_cjk
    if copyright_lgc:
        notice += " Latin Extended, Greek and Cyrillic outlines: " + copyright_lgc
    notice += (" Both licensed under the SIL Open Font License, Version 1.1. "
               "This font is a modified composite; Reserved Font Names "
               "'Noto' and 'Source Han' are not used. Upstream Latin outlines "
               "are proprietary and are not relicensed.")
    set_name(base, 0, notice)
    if args.version_string:
        version_string = args.version_string
    elif args.full:
        version_string = "Version 1.200 Full"
    elif lgc is not None:
        version_string = "Version 1.100 CJK-LGC"
    else:
        version_string = "Version 1.000 CJK"
    set_name(base, 5, version_string)
    print("version string:", version_string)
    license_desc = "SIL Open Font License, Version 1.1"
    if lgc is not None:
        license_desc = str(lgc["name"].getDebugName(13) or license_desc)
    set_name(base, 13, license_desc)
    set_name(base, 14, "https://openfontlicense.org/")

    if args.family_name:
        rename_family(base, args.family_name)
        print("internal family renamed to: %s" % args.family_name)

    print("saving ... total glyphs %d, code points %d" % (total, len(full)))
    base.save(args.out)
    print("done: %s | %.2f MB | %.1fs" %
          (args.out, os.path.getsize(args.out) / 1048576, time.time() - t0))


if __name__ == "__main__":
    main()

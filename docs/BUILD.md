# Building from source

Everything needed to reproduce the font is in this repository except the
font inputs themselves. See [COMPLIANCE.md](COMPLIANCE.md) for why those
are not shipped.

## Prerequisites

| Requirement | Version used | Notes |
| --- | --- | --- |
| Python | 3.10 | 3.8 or newer should work |
| fontTools | 4.65.0 | `ttLib`, `Cu2QuPen`, `varLib.instancer`, `DecomposingRecordingPen` |
| brotli | 1.2.1 | Only for `scripts/make_woff2.py` |
| Noto Serif CJK | 2.004 | TTC, seven weights, SC face index 2 |
| Noto Serif | 2025.04 | Variable font `NotoSerif[wdth,wght].ttf` |
| Upstream Latin font | Regular | Your own legally obtained copy |

```bash
python3 -m pip install fonttools brotli
```

On Debian or Ubuntu: `apt install python3-fonttools fonts-noto-cjk fonts-noto`.
The variable font is also available from
[notofonts/latin-greek-cyrillic](https://github.com/notofonts/latin-greek-cyrillic).

## Material layout

Put your upstream copy somewhere private. A typical local layout:

```
inputs/
└── AnthropicSerifWebText.ttf        your copy, never committed
/usr/share/fonts/opentype/noto/
├── NotoSerifCJK-Medium.ttc
├── NotoSerifCJK-Bold.ttc
├── NotoSerifCJK-SemiBold.ttc
└── ...
/path/to/noto/
└── NotoSerif[wdth,wght].ttf
```

`inputs/` and `build/` are excluded by `.gitignore`. If the Noto files are
spread across directories, skip `--source-dir` and pass `--cjk-ttc` and
`--lgc-font` as absolute paths.

## Four presets

```bash
# 1.0.0 equivalent: Chinese only, Medium
python3 scripts/build_cjk.py \
  --latin inputs/AnthropicSerifWebText.ttf \
  --source-dir /usr/share/fonts/opentype/noto \
  --preset cjk

# Chinese only, heavier Chinese outlines
python3 scripts/build_cjk.py \
  --latin inputs/AnthropicSerifWebText.ttf \
  --source-dir /usr/share/fonts/opentype/noto \
  --preset cjk-bold

# Add Latin Extended, Greek, Cyrillic
python3 scripts/build_cjk.py \
  --latin inputs/AnthropicSerifWebText.ttf \
  --source-dir /usr/share/fonts/opentype/noto \
  --lgc-font "/path/to/NotoSerif[wdth,wght].ttf" \
  --preset multilingual

# Add kana, Hangul and the rest of the CJK source
python3 scripts/build_cjk.py \
  --latin inputs/AnthropicSerifWebText.ttf \
  --source-dir /usr/share/fonts/opentype/noto \
  --lgc-font "/path/to/NotoSerif[wdth,wght].ttf" \
  --preset full
```

Each preset sets the CJK weight, whether the LGC source is used, whether
`--full` is enabled, the version string, and the output path under
`build/`. Outputs are independent; no preset overwrites another.

Expected build time on a modest machine: about 45 seconds for `cjk`, about
50 seconds for `full`. WOFF2 compression of the `full` build takes roughly
another 90 seconds.

## Full parameter list

| Option | Default | Meaning |
| --- | --- | --- |
| `--latin` | required | Your upstream Latin TTF |
| `--preset` | none | `cjk`, `cjk-bold`, `multilingual`, `full` |
| `--source-dir` | none | Directory with Noto Serif CJK TTCs and the variable font |
| `--cjk-ttc` | from preset/source-dir | Noto Serif CJK TTC or single-face OTF |
| `--cjk-face` | 2 | Face index in the TTC; 2 is Simplified Chinese |
| `--lgc-font` | from preset/source-dir | Noto Serif variable font |
| `--lgc-weight` | 500 | `wght` instance; `wdth` stays at its default |
| `--out` | `build/SerifCJKExtension-<preset>.ttf` | Output TTF path |
| `--max-err` | 0.5 | cu2qu maximum error in source units |
| `--family-name` | `Serif CJK Extension` | Replace internal family and PostScript names |
| `--keep-upstream-name` | off | Do not rename (see [COMPLIANCE.md](COMPLIANCE.md)) |
| `--version-string` | from preset | Override `name` ID 5 |
| `--no-cjk` | off | Skip the CJK source |
| `--no-lgc` | preset decides | Skip the LGC source |
| `--full` | preset decides | Take every remaining CJK source code point |
| `--limit` | 0 | Convert a small sample, for debugging |

To smoke-test without a full build:

```bash
python3 scripts/build_cjk.py \
  --latin inputs/AnthropicSerifWebText.ttf \
  --cjk-ttc /usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc \
  --preset cjk --limit 24 --out /tmp/smoke.ttf
```

## Choosing the Chinese weight

The CJK weight is decided by which TTC you pass. All seven weight TTCs of
Noto Serif CJK SC have identical cmap coverage (44,746 code points), so
switching weight never changes which characters you get.

Measured by rendering `H` and `中` at the same pixel size (FreeType
normalises by unitsPerEm, so 1000 UPM CJK and 2000 UPM Latin are directly
comparable):

| CJK source | `usWeightClass` | `中` stem | vs. Western `H` (61.4 px) | Sample ink |
| --- | --- | --- | --- | --- |
| Regular | 400 | 47.5 px | -22.7% | 17,931 px |
| Medium (default) | 500 | 54.5 px | -11.1% | 21,178 px |
| SemiBold | 600 | 60.7 px | -1.0% | 23,744 px |
| **Bold (`cjk-bold`)** | **700** | **70.7 px** | **+15.1%** | **28,082 px** |
| Heavy | 900 | 82.3 px | +34.1% | 33,346 px |

Medium is the default because it stays close to the Latin without
darkening dense Chinese text. **SemiBold is the near-exact optical match.**
Bold is deliberately heavier and is what `cjk-bold` uses, because its
purpose is to fix Chinese that reads as thin and pale. To get the tighter
match, run the `cjk` preset with `--cjk-ttc .../NotoSerifCJK-SemiBold.ttc`.

`cjk-bold` keeps `OS/2.usWeightClass = 400` and `name` ID 2 = `Regular`.
The Western outlines are Regular, so this is a Regular font with heavier
Chinese, not a synthetic bold face. Do not install it alongside `cjk`;
the two have identical family and subfamily names.

## What the script does

1. **Baseline.** Load the Latin font, record glyph order, cmap and vertical
   metrics. It reads `unitsPerEm == 2000` and never alters `hhea`, `OS/2`
   typographic metrics or cap/x heights.
2. **CJK selection.** By default keep Chinese-related ranges. With `--full`
   (the `full` preset), keep every remaining code point of the CJK source,
   which adds kana, Hangul, enclosed CJK, squared compatibility forms, box
   drawing and other symbols. The exclusion set is the LGC source's
   **actual** cmap, not its nominal ranges: U+2160 ROMAN NUMERAL ONE is in
   the CJK source but absent from Noto Serif, so it must not be excluded.
3. **CJK conversion.** CFF cubic charstrings become TrueType quadratics via
   `Cu2QuPen` (`max_err=0.5`, `reverse_direction=True`) while a
   `TransformPen` scales coordinates by 2 to reach 2000 UPM.
4. **LGC instance.** `instantiateVariableFont` pins `wght=500` and default
   `wdth`; the static instance's `hmtx` advances already include `HVAR`
   deltas.
5. **LGC conversion.** `DecomposingRecordingPen` expands composite glyphs
   into plain contours, coordinates are scaled by 2, and `TTGlyphPen`
   rebuilds the glyph. Expanding removes dependencies on source glyph
   names, so CJK `uniXXXX` and LGC `lgcXXXX` names never collide.
6. **Metrics.** Chinese and kana advances become full-width 2000 units;
   Hangul syllables use 1932. LGC advances come from the instanced source
   and are scaled by 2. Original Latin advances and bearings are untouched.
7. **Append only.** New glyphs are appended after the original 720. This is
   the critical detail: every existing glyph id stays valid, so all GSUB
   and GPOS lookups keep working without being rewritten.
8. **cmap.** BMP characters are added to the existing format 4 subtables;
   a new (3,10) format 12 subtable carries the complete mapping for
   non-BMP CJK Extensions B-I, Latin Extended-F/G and the U+1F100 /
   U+1F200 enclosed supplements. The Macintosh (1,0,6) subtable is left
   untouched.
9. **Metadata and naming.** `maxp`, `hhea`, `head` bounding box, `OS/2`
   Unicode ranges and `name` are updated. Adobe, Noto Project and
   maintainer copyright lines plus the OFL reference go into IDs 0, 5, 13
   and 14. The family is renamed to `Serif CJK Extension` unless
   `--keep-upstream-name` is passed.

## Verification

```bash
python3 scripts/make_woff2.py build/SerifCJKExtension-CJK.ttf
python3 scripts/verify.py build/SerifCJKExtension-CJK.ttf --preset cjk
```

`verify.py` prints family, version, UPM, vertical metrics, glyph and code
point counts, cmap subtables, GSUB/GPOS counts, full-width CJK advances,
and sample coverage for Latin, CJK, LGC, kana, Hangul and symbols. Built-in
expectations:

| Preset | Glyphs | Code points | Non-BMP | Highest |
| --- | --- | --- | --- | --- |
| `cjk`, `cjk-bold` | 31,724 | 31,595 | 2,306 | U+3106C |
| `multilingual` | 33,897 | 33,768 | 2,394 | U+3106C |
| `full` | 47,092 | 46,963 | 2,619 | U+3106C |

All four retain 19 GSUB features, 2 GPOS features and four cmap subtables
including format 12. Render
`A 文 あ 한 α Ж Typography 排版設計 かな 한글 Ελληνικά Кириллица ﬁ 123`
with the `full` build and confirm that `fi` still forms a ligature and no
tofu boxes appear.

To confirm the two CJK-only presets differ only in outlines:

```python
from fontTools.ttLib import TTFont
a = TTFont("build/SerifCJKExtension-CJK.ttf")
b = TTFont("build/SerifCJKExtension-CJK-Bold.ttf")
print("cmap identical:", a.getBestCmap() == b.getBestCmap())
west = a.getGlyphOrder()[:720]
print("western identical:", all(a["glyf"][g] == b["glyf"][g] for g in west))
print("Chinese differs:",
      a["glyf"][a.getBestCmap()[0x4E00]] != b["glyf"][b.getBestCmap()[0x4E00]])
```

## Renaming

The default family is `Serif CJK Extension`. Choose another with
`--family-name`, or reproduce the original names with
`--keep-upstream-name`. The script rewrites `name` IDs 1, 4, 6, 16 and 17
and derives the PostScript name from the family plus subfamily. Renaming
does not change outlines or the licence status of the Western glyphs.

## Known trade-offs

- CFF to TrueType conversion drops native CFF hinting; decomposing LGC
  composites drops their hinting instructions. Very small screen sizes may
  look slightly softer.
- Chinese, kana, Hangul and CJK symbols retain Source Han Serif stroke
  detail; Latin Extended, Greek and Cyrillic retain Noto Serif detail.
  They share a design language and `wght=500`, but are not redrawn stroke
  by stroke to imitate the upstream Latin letterforms.
- Original GSUB/GPOS lookups cover Latin only. Other scripts get correct
  glyphs and advances but not Latin kerning pairs, kana positioning,
  vertical layout, or Hangul Jamo composition. Hangul syllables are
  supplied precomposed.
- The `full` build is about 23.6 MB as TTF and 8.4 MB as WOFF2. Subset
  for the web; see [USAGE.md](USAGE.md).
- `cjk-bold` is heavier only in Chinese. Applying CSS `font-weight: 700`
  on top of it would synthetically embolden the Latin and is not
  recommended.

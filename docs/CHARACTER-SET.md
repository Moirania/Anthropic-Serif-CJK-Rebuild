# Character set coverage

This document lists exactly which Unicode ranges the build adds to the
upstream Latin font. Counts are taken from the two source fonts, minus code
points the Latin base already covered.

## Totals by preset

| Preset | Added | Glyphs | Code points | Non-BMP |
| --- | --- | --- | --- | --- |
| `cjk` | 31,004 | 31,724 | 31,595 | 2,306 |
| `cjk-bold` | 31,004 | 31,724 | 31,595 | 2,306 |
| `multilingual` | 33,177 | 33,897 | 33,768 | 2,394 |
| `full` | 46,372 | 47,092 | 46,963 | 2,619 |

`cjk` and `cjk-bold` have **byte-identical cmap dictionaries**; only the
outline instances differ. See [BUILD.md](BUILD.md) for the weight table.

The upstream font contributes 628 code points, of which 591 live in its
Unicode BMP subtables and 37 exist only in its Macintosh (1,0,6) subtable.
All four original cmap subtables are preserved untouched, and a fifth
(3,10) format 12 subtable carries the complete mapping.

## By group

| Group | Added | Source |
| --- | --- | --- |
| CJK Unified Ideographs, basic block | 20,971 | Noto Serif CJK SC |
| CJK Extension A | 6,582 | Noto Serif CJK SC |
| CJK Extensions B-I plus compatibility supplement | 2,306 | Noto Serif CJK SC |
| CJK compatibility ideographs (BMP) | 366 | Noto Serif CJK SC |
| CJK punctuation, radicals, bopomofo, strokes, forms | 779 | Noto Serif CJK SC |
| Hangul Syllables | 11,172 | Noto Serif CJK SC |
| Hangul Jamo, Compat Jamo, Ext-A, Ext-B | 451 | Noto Serif CJK SC |
| Hiragana, Katakana, Katakana Phonetic Ext, Kanbun | 221 | Noto Serif CJK SC |
| Enclosed CJK, squared compatibility, enclosed ideographs | 735 | Noto Serif CJK SC |
| Enclosed alphanumerics, Roman numerals, box drawing | 312 | Noto Serif CJK SC |
| Arrows, math, geometric, misc symbols, dingbats, small forms | 304 | Noto Serif CJK SC |
| Latin Extended (IPA, phonetic, Ext-A to G) | 1,018 | Noto Serif wght=500 |
| Greek (including Greek Extended) | 354 | Noto Serif wght=500 |
| Cyrillic (including Ext-A/B/C) | 441 | Noto Serif wght=500 |
| Shared marks, punctuation, currency, number forms | 360 | Noto Serif wght=500 |

`cjk` and `cjk-bold` take only the first five rows. `multilingual` adds
the last four rows. `full` adds every row.

## CJK ranges (all presets)

| Unicode range | Block | Added |
| --- | --- | --- |
| U+2E80-U+2FDF | CJK Radicals Supplement, Kangxi Radicals | 329 |
| U+2FF0-U+2FFF | Ideographic Description Characters | 12 |
| U+3000-U+303F | CJK Symbols and Punctuation | 64 |
| U+3100-U+312F | Bopomofo | 43 |
| U+31A0-U+31BF | Bopomofo Extended | 28 |
| U+31C0-U+31EF | CJK Strokes | 36 |
| U+4E00-U+9FFF | CJK Unified Ideographs | 20,971 |
| U+3400-U+4DBF | CJK Extension A | 6,582 |
| U+20000-U+2EBEF, U+30000-U+3134F | Extensions B-I | 2,248 |
| U+2F800-U+2FA1F | Compatibility Supplement | 55 |
| U+F900-U+FAFF | Compatibility Ideographs | 366 |
| U+FE30-U+FE4F | CJK Compatibility Forms | 26 |
| U+FF00-U+FFEF | Halfwidth and Fullwidth Forms | 224 |
| U+3000-U+303F (Japanese punctuation) | included above | - |

Halfwidth Katakana (U+FF61-U+FF9F, 63 code points) is already covered by
the Halfwidth and Fullwidth Forms row, so Japanese text does not need a
separate preset for its basic kana rendering.

## Latin Extended, Greek and Cyrillic (`multilingual`, `full`)

| Unicode range | Block | Added |
| --- | --- | --- |
| U+0100-U+024F | Latin Extended-A/B | 208 |
| U+0250-U+02AF | IPA Extensions | 96 |
| U+1D00-U+1D7F, U+1D80-U+1DBF | Phonetic Extensions | 105 |
| U+2C60-U+2C7F, U+A720-U+A7FF | Latin Extended-C/D | 120 |
| U+AB30-U+AB6F | Latin Extended-E | 49 |
| U+10780-U+107BF | Latin Extended-F | 57 |
| U+1DF00-U+1DFFF | Latin Extended-G | 31 |
| U+0370-U+03FF | Greek and Coptic | 121 |
| U+1F00-U+1FFF | Greek Extended (polytonic) | 233 |
| U+0400-U+04FF | Cyrillic | 256 |
| U+0500-U+052F | Cyrillic Supplement | 48 |
| U+2DE0-U+2DFF, U+A640-U+A69F | Cyrillic Ext-A/B | 128 |
| U+1C80-U+1C8F | Cyrillic Ext-C | 9 |

The upstream font already has complete Latin-1 Supplement and Latin
Extended-A, so those ranges needed almost no additions. Greek Extended
supplies breathings, accents and iota subscript for classical texts.

## Kana ranges (`full` only)

| Unicode range | Block | Added |
| --- | --- | --- |
| U+3040-U+309F | Hiragana | 93 |
| U+30A0-U+30FF | Katakana | 96 |
| U+31F0-U+31FF | Katakana Phonetic Extensions | 16 |
| U+3190-U+319F | Kanbun | 16 |

## Hangul ranges (`full` only)

| Unicode range | Block | Added |
| --- | --- | --- |
| U+AC00-U+D7A3 | Hangul Syllables | 11,172 |
| U+1100-U+11FF | Hangul Jamo | 256 |
| U+3130-U+318F | Hangul Compatibility Jamo | 94 |
| U+A960-U+A97F | Hangul Jamo Extended-A | 29 |
| U+D7B0-U+D7FF | Hangul Jamo Extended-B | 72 |

Syllables are precomposed glyphs. Conjoining Jamo sequences are present as
individual characters but are not recombined by any OpenType lookup; use
precomposed text or a shaping engine.

## CJK symbol ranges (`full` only)

| Unicode range | Block | Added |
| --- | --- | --- |
| U+3200-U+32FF | Enclosed CJK Letters and Months | 255 |
| U+3300-U+33FF | CJK Compatibility (squared units) | 255 |
| U+1F100-U+1F1FF | Enclosed Alphanumeric Supplement | 167 |
| U+1F200-U+1F2FF | Enclosed Ideographic Supplement | 58 |
| U+2460-U+24FF | Enclosed Alphanumerics | 160 |
| U+2500-U+257F | Box Drawing | 128 |
| U+2150-U+218F | Roman numerals (Number Forms) | 24 |
| U+2190-U+21FF | Arrows | 17 |
| U+2200-U+22FF | Mathematical Operators | 66 |
| U+2300-U+23FF | Miscellaneous Technical | 25 |
| U+25A0-U+25FF | Geometric Shapes and block elements | 37 |
| U+2600-U+26FF | Miscellaneous Symbols | 50 |
| U+2700-U+27BF | Dingbats | 38 |
| U+FE50-U+FE6F | Small Form Variants | 26 |
| U+20DD-U+20DE | Combining enclosing circle / square | 2 |

Another 43 scattered single code points include U+2423 OPEN BOX and the
U+2580-U+259F block elements.

## Deliberately not included

- **Colour emoji and pictographs.** The U+1F200-U+1F2FF block contributes
  monochrome enclosed CJK ideographs, not emoji. Use a dedicated emoji font.
- **Private Use Area** code points.
- **Composition and vertical layout features.** No Jamo composition, no
  `vert` / `vrt2` for vertical kana, no `ljmo` / `vjmo` / `tjmo`.
- **Other scripts** such as Arabic, Devanagari, Thai and Hebrew, and kana
  extensions beyond U+31FF that this Source Han Serif version lacks.
- **Anything the two source fonts do not contain.** The build is a merger,
  not a pan-Unicode synthesiser.

## Verifying coverage yourself

```bash
python3 scripts/verify.py build/SerifCJKExtension-Full.ttf --preset full
```

Or directly:

```python
from fontTools.ttLib import TTFont
cm = TTFont("build/SerifCJKExtension-Full.ttf").getBestCmap()
for cp in (0x4E00, 0x2000B, 0x3042, 0x30A2, 0xAC00, 0xD7A3, 0x1100,
           0x320E, 0x337F, 0x2160, 0x1F200, 0x03B1, 0x0416, 0xFB01):
    print("U+%05X" % cp, cm.get(cp, "MISSING"))
```

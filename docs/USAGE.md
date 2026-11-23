# Using the font you built

This repository does not contain font files. Once you have run
`scripts/build_cjk.py`, the outputs in `build/` are ordinary TTF and WOFF2
fonts and can be used like any other. See [BUILD.md](BUILD.md) for the build
steps and [COMPLIANCE.md](COMPLIANCE.md) before sharing the result.

## Outputs

| Preset | TTF | WOFF2 | Glyphs |
| --- | --- | --- | --- |
| `cjk` | ~15.3 MB | ~6.9 MB | 31,724 |
| `cjk-bold` | ~15.3 MB | ~7.2 MB | 31,724 |
| `multilingual` | ~15.6 MB | ~7.0 MB | 33,897 |
| `full` | ~23.6 MB | ~8.4 MB | 47,092 |
| `signature` | ~17.0 MB | ~7.5 MB | 31,724 |

Default naming: `SerifCJKExtension-CJK.ttf`,
`SerifCJKExtension-CJK-Bold.ttf`,
`SerifCJKExtension-Multilingual.ttf`, `SerifCJKExtension-Full.ttf`,
`SerifCJKExtension-Signature.ttf`.
The internal family name is `Serif CJK Extension` unless you passed
`--keep-upstream-name` or a custom `--family-name`.

## Desktop installation

- **Windows**: double click the TTF and choose Install, or copy it into
  `%WINDIR%\Fonts`.
- **macOS**: open the TTF with Font Book and click Install Font.
- **Linux**: copy to `~/.local/share/fonts/`, then run `fc-cache -fv`.

All five presets share the same family name and the same `Regular`
subfamily, so install **only one**. In particular `cjk` and `cjk-bold` are
indistinguishable to the font cache. Verify with:

```bash
fc-match "Serif CJK Extension"
```

If you kept the upstream name, use that name instead and remove the
original font first.

## Web embedding

```css
@font-face {
  font-family: "Serif CJK Extension";
  src: url("/fonts/SerifCJKExtension-Full.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

article {
  font-family: "Serif CJK Extension", Georgia, "Times New Roman", serif;
  font-feature-settings: "kern" 1, "liga" 1;
  line-height: 1.65;
}
```

Because CJK, kana, Hangul, Greek and Cyrillic live in one file, no fallback
stack is needed for those scripts. Keep a fallback for colour emoji,
Private Use Area characters and scripts outside the project's scope.

## Multilingual example

```html
<p lang="zh">《庄子》曰：「天地与我并生，而万物与我为一。」</p>
<p lang="ja">吾輩は猫である。名前はまだ無い。　カタカナと漢字の混植。</p>
<p lang="ko">모든 사람은 태어날 때부터 자유롭고 존엄하며 평등하다.</p>
<p lang="el">Ἀπὸ τὴν ἀρχὴ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν.</p>
<p lang="ru">В начале было Слово, и Слово было у Бога.</p>
<p lang="la">Ā ā Ă ă Æ æ Ø ø Ł ł Ș Ț ẞ — ﬁde et amōre.</p>
<p>A 文 あ 한 α Ж　㍿ ㌔ ㈎ ㉠ ①　Typography 排版設計 かな 한글 ﬁ 123</p>
```

Use the `full` preset for the Japanese, Korean and CJK-symbol lines.
Polytonic Greek, Cyrillic Ext-A/B/C, all 11,172 precomposed Hangul
syllables and both kana syllabaries render without tofu boxes. Hangul Jamo
sequences are not recombined by OpenType lookups, so use precomposed
syllables or a shaping engine.

## OpenType features

The original GSUB and GPOS lookups survive intact because new glyphs are
appended rather than inserted. The Western font provides 19 GSUB and 2 GPOS
features, including standard ligatures, discretionary ligatures, small
caps, old-style and tabular numerals, fractions, ordinals and case-sensitive
forms.

```css
.numbers { font-feature-settings: "tnum" 1, "onum" 1; }
.heading { font-feature-settings: "dlig" 1, "case" 1; }
```

These features were authored for the upstream Latin glyphs. Greek,
Cyrillic, kana and Hangul get correct glyphs and advances but are not
included in Latin kerning pairs or language-specific substitutions. There
are no `vert`, `vrt2`, `ljmo`, `vjmo` or `tjmo` lookups.

## Subsetting for production

The `full` WOFF2 is about 8.4 MB. Use `pyftsubset` to keep only the
characters a page needs:

```bash
pyftsubset build/SerifCJKExtension-Full.ttf \
  --text-file=content.txt \
  --output-file=subset.woff2 \
  --flavor=woff2 \
  --layout-features='*' \
  --no-hinting
```

Notes:

- `--text-file` should contain every character that can appear on the
  page, including kana, Hangul syllables, Greek accents and Cyrillic.
- `--layout-features='*'` keeps ligature and kerning tables.
- Split by `unicode-range` for dynamic content: one Latin subset plus
  separate CJK, kana, Hangul, Greek and Cyrillic chunks. Hangul alone is
  11,172 glyphs, so a page without Korean should never load that chunk.
- Do not drop the format 12 cmap subtable if your content uses CJK
  Extensions B-I, Latin Extended-F/G or the U+1F100 / U+1F200 supplements.

```bash
printf '%s' 'A 文 あ 한 α Ж Typography 排版設計 かな 한글 2026' > content.txt
pyftsubset build/SerifCJKExtension-Full.ttf \
  --text-file=content.txt --flavor=woff2 \
  --output-file=article.woff2 --layout-features='*'
```

## Rendering notes

- 2000 UPM, ascender 1985, descender -515. Tight line heights can clip CJK
  tops, Hangul and polytonic Greek accents; 1.6 or greater is comfortable.
- Chinese and kana are full width (2000 units); Hangul syllables use 1932;
  Latin, Greek and Cyrillic keep proportional advances.
- CFF hinting is lost during conversion and LGC composites are decomposed,
  so very small text on low-density screens may look slightly softer.
- Vertical typesetting is not implemented. Vertical forms are covered as
  characters, not as full vertical layout.
- The global `head` bounding box is wider than the vertical metrics because
  some combining marks extend beyond the em box. `hhea` is unchanged, so
  line height stays stable.

## PDF and document embedding

The TTF can be embedded in PDF, EPUB and office documents. Embedding rules
for the upstream proprietary Latin outlines still apply; read
[COMPLIANCE.md](COMPLIANCE.md) before distributing files that contain it.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Build exits with "input file not found" | Wrong `--latin`, `--cjk-ttc` or `--lgc-font` | Check absolute paths and TTC face index |
| Chinese, kana or Hangul shows boxes | A smaller preset is installed | Build and install `full`, clear the font cache |
| Chinese looks thin and pale | `cjk` Medium is lighter than the Western stems | Use `cjk-bold`; do not stack `font-weight: 700` |
| Chinese serifs clash with the Latin | Source Han triangular terminals | Use `signature`; read its documented limits in [DESIGN.md](DESIGN.md) |
| Two presets installed, unpredictable results | Identical family and subfamily names | Remove one and clear the font cache |
| Hangul Jamo typed separately do not form a syllable | No Jamo composition lookups | Use precomposed U+AC00-U+D7A3 or a shaping engine |
| `fi` no longer joins | Subset dropped layout features | Rebuild with `--layout-features='*'` |
| Very large page weight | Full WOFF2 served | Generate a subset as shown above |
| WOFF2 conversion fails with "No module named brotli" | Missing dependency | `python3 -m pip install brotli` |

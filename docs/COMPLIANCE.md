# Compliance and licensing

This repository deliberately contains **no font binaries**. Read this
document before building, using or redistributing anything produced by the
scripts here.

## 1. Why the binaries are absent

The base font, Anthropic Serif Web Text Regular, is a proprietary brand
typeface. Anthropic, PBC does not publish a public font licence for it, and
third-party references describe it as a non-licensed brand font. It is
**not** a SIL OFL font.

A composite font necessarily contains every Western outline from that base.
Publishing such a file in a public repository, attaching it to a Release,
or mirroring it elsewhere is a redistribution of proprietary outlines whose
permission status is unclear. This repository therefore follows the
conservative publication path:

| Shipped here | Not shipped here |
| --- | --- |
| Build script and parameters | The upstream Latin TTF |
| Documentation and verification data | Generated TTF / WOFF2 / OTF files |
| OFL text, copyright notices, FONTLOG | TTC / OTF outline sources |
| Specimen images | Credentials or local paths |

The `inputs/`, `build/` and `dist/` directories and all common font
extensions are excluded by [../.gitignore](../.gitignore). GitHub Releases
for this repository contain source material only.

You supply the upstream font yourself, on your own machine, and the script
reads it locally. No upload occurs and no binary leaves your machine unless
you choose to publish it.

## 2. What you must supply

| Input | Status | Condition |
| --- | --- | --- |
| Anthropic Serif Web Text Regular | Proprietary | A copy you have legally obtained; you are responsible for your right to use it |
| Noto Serif CJK SC (any weight TTC) | SIL OFL 1.1 | Keep copyright and licence text with any distributed derivative |
| Noto Serif (Latin-Greek-Cyrillic VF) | SIL OFL 1.1 | Same |

The two Noto families are the only outline sources added by the build.
No third outline source is introduced, including for kana and Hangul: those
characters come from the same Noto Serif CJK SC family, whose five regional
faces share identical cmap coverage. The `cjk-bold` preset is not a new
source either; it points the same family at its Bold TTC.

## 3. SIL OFL 1.1 obligations for the added outlines

Noto Serif CJK SC is copyright (c) 2014-2022 Adobe and other contributors.
Noto Serif is Copyright 2022 The Noto Project Authors. Both are licensed
under [SIL OFL 1.1](../OFL.txt). If you distribute a font built here, the
OFL portion requires you to:

1. Include the copyright notice and the full OFL text with the font. The
   build script writes both into `name` IDs 0, 13 and 14; still ship
   `OFL.txt` and `FONTLOG.txt` alongside the binary.
2. License the modified OFL-derived outlines under the same OFL 1.1. You
   may not sell the font file by itself.
3. Not use the original authors' names to endorse your derivative without
   permission.
4. Respect Reserved Font Names. **Noto** and **Source Han** are not used in
   the output. This repository renames the family to `Serif CJK Extension`
   by default, which also removes the upstream brand name from the internal
   `name` table.
5. Record changes. [../FONTLOG.txt](../FONTLOG.txt) follows the OFL FAQ
   convention for modified fonts.

## 4. The upstream brand name and trademark

`--family-name` defaults to `Serif CJK Extension`, rewriting `name` IDs 1,
4, 6, 16 and 17. This avoids presenting a derivative as an official
Anthropic product and reduces trademark risk. It does **not** change the
fact that the Western outlines themselves are proprietary; renaming is a
naming measure, not a licence.

Pass `--keep-upstream-name` only if you have a specific reason to reproduce
the original `name` table and have confirmed you may do so.

The repository name contains "Anthropic Serif" purely to describe the
object being rebuilt. It does not imply affiliation, sponsorship or
endorsement by Anthropic, Adobe or Google.

## 5. Before you redistribute a built font

Use this checklist:

- [ ] I have a legal right to use and, if applicable, redistribute the
      upstream Latin outlines.
- [ ] `OFL.txt` and `FONTLOG.txt` travel with the binary.
- [ ] Copyright lines in `name` ID 0 name Adobe and The Noto Project
      Authors for their respective outlines.
- [ ] No Reserved Font Name appears in the internal family or PostScript
      names.
- [ ] The font is not sold by itself and is not presented as endorsed by
      the original designers.
- [ ] I am not committing the binary, the upstream font, or credentials to
      any public repository.
- [ ] For commercial or client work, I have obtained whatever additional
      permission the upstream rights holder requires.

## 6. Simplest fully compliant configuration

If in doubt, use the output only locally or inside your own organisation,
do not publish the binary, and share this repository instead: readers can
reproduce the method with their own legally obtained inputs. That is the
configuration this repository is designed for.

## 7. Disclaimer

This document is a technical description of the licensing layers involved,
not legal advice. Only the rights holders can grant permission for the
proprietary outlines. No maintainer of this repository can give that
permission on their behalf.

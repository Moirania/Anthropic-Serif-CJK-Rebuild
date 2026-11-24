# Compliance and licensing

Read this document before building, using or redistributing anything here.
**Scope changed on 2026-11-24**: this repository now ships exactly one font
binary, `fonts/SerifCJKExtension-Standard.ttf`. All other built fonts remain
local-only.

## 1. Why there is exactly one binary, and the risk it carries

The base font, Anthropic Serif Web Text Regular, is a proprietary brand
typeface. Anthropic, PBC does not publish a public font licence for it, and
third-party references describe it as a non-licensed brand font. It is
**not** a SIL OFL font.

Every composite font produced by these scripts contains all 720 Western
outlines from that base. At the maintainer's explicit request, one such
composite -- the `cjk` preset production build -- is now committed as
`fonts/SerifCJKExtension-Standard.ttf` and listed in
[../SOURCE-MANIFEST.txt](../SOURCE-MANIFEST.txt).

| Shipped here | Not shipped here |
| --- | --- |
| Build script and parameters | The upstream Latin TTF |
| One `cjk` preset TTF under `fonts/` | `cjk-bold`, `multilingual`, `full` outputs |
| 13 specimen images and 2 reports | Generated WOFF2 / OTF files |
| OFL text, copyright notices, FONTLOG | TTC / OTF outline sources |
| Verification scripts and audit data | Credentials or local paths |

**This is a redistribution of proprietary outlines whose permission status
is unclear.** Renaming the family to `Serif CJK Extension` is a naming
measure, not a licence. This repository grants no permission and reaches no
legal conclusion on behalf of Anthropic, PBC. Before downloading, mirroring
or using that file -- especially in commercial or client work -- verify your
own right to do so with the rights holder. The fact that one copy is present
here does not give that right to anyone else.

If you want to avoid the binary entirely, ignore `fonts/` and build locally
from your own legally obtained inputs. No script reads that directory.

`inputs/`, `build/`, `dist/` and all common font extensions remain excluded
by [../.gitignore](../.gitignore), with a single explicit exception for the
one production TTF.

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
      upstream Latin outlines. The one binary shipped here does not grant
      that right to anyone else.
- [ ] `OFL.txt` and `FONTLOG.txt` travel with the binary.
- [ ] Copyright lines in `name` ID 0 name Adobe and The Noto Project
      Authors for their respective outlines.
- [ ] No Reserved Font Name appears in the internal family or PostScript
      names.
- [ ] The font is not sold by itself and is not presented as endorsed by
      the original designers.
- [ ] I am not committing the upstream font, a second font binary, or
      credentials to any public repository.
- [ ] For commercial or client work, I have obtained whatever additional
      permission the upstream rights holder requires.

## 6. Simplest fully compliant configuration

If in doubt, use every output only locally or inside your own organisation,
do not republish the binary, and share the source-only parts of this
repository instead: readers can reproduce the method with their own legally
obtained inputs. Treat `fonts/SerifCJKExtension-Standard.ttf` as an
exception made at the maintainer's request, not as a licence grant.

## 7. Disclaimer

This document is a technical description of the licensing layers involved,
not legal advice. Only the rights holders can grant permission for the
proprietary outlines. No maintainer of this repository can give that
permission on their behalf.

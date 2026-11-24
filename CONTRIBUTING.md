# Contributing

Thanks for taking the time to improve this project.

## The one rule

**Never commit a font binary, an upstream font file, or a credential.**

This repository exists specifically because it ships no font software.
`.gitignore` excludes every common font extension plus `inputs/`,
`build/` and `dist/`. If a pull request adds a `.ttf`, `.otf`, `.woff2`,
`.ttc` or the upstream Latin font, it cannot be merged. Do not attach
binaries to issues either; describe the problem with code points and
screenshots instead.

## Before you start

Read [docs/COMPLIANCE.md](docs/COMPLIANCE.md). Any change that introduces a
new outline source must name the source, its weight or instance, and its
licence. Without that information a pull request cannot be merged.

## Good first contributions

- Report a missing character with its Unicode code point, preset,
  rendering engine and a screenshot.
- Fix a broken relative link, a typo, or an unclear sentence in `docs/`.
- Improve `scripts/build_cjk.py`: better error messages, faster outline
  conversion, extra presets, or smarter source discovery.
- Extend `scripts/verify.py` with more coverage checks or clearer output.
- Add a reading sample or specimen sheet for a language not shown yet
  (polytonic Greek, Old Church Slavonic, Vietnamese, IPA transcription,
  classical kana orthography, older Hangul orthography). Keep the
  print-specimen style: hard rules, crop marks, left alignment, no
  rounded corners, no glass, no gradient buttons.
- Add a subsetting recipe to [docs/USAGE.md](docs/USAGE.md).
- Improve the L3 stroke gate or audit rules; read [docs/L3.md](docs/L3.md)
  first and state which glyphs you proofed.
- Propose a new preset, with its source font, licence and expected counts.

## Pull request process

1. Fork the repository and create a branch from `main`.
2. Keep the change focused. Document any change to the generated font's
   structure in [FONTLOG.txt](FONTLOG.txt).
3. If you changed the build script, run the smoke test and at least one
   full preset locally:

   ```bash
   python3 scripts/build_cjk.py \
     --latin inputs/AnthropicSerifWebText.ttf \
     --source-dir /path/to/noto-fonts \
     --preset cjk
   python3 scripts/verify.py build/SerifCJKExtension-CJK.ttf --preset cjk
   ```

4. Confirm that README, `docs/` and `SOURCE-MANIFEST.txt` still describe
   the real output: preset counts, file sizes, command examples.
5. Regenerate `SOURCE-MANIFEST.txt` if you added, removed or edited any
   tracked file.
6. Confirm there is no emoji, no token, no absolute local path and no
   font binary in the diff.
7. Open a pull request describing what changed and how you verified it.

## Reporting problems

Use the GitHub issue tracker and include:

- which preset produced the font (`cjk`, `cjk-bold`, `multilingual`,
  `full`), and whether you used `--family-name` or
  `--keep-upstream-name`;
- the exact command, with private paths redacted;
- operating system, Python version, fontTools version, and application,
  browser or rendering engine version;
- the exact text or Unicode code points involved;
- what you expected and what you saw;
- a screenshot when the problem is visual.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

# fa-subset — Font Awesome Subsetter

[![License: BSD-2-Clause](https://img.shields.io/badge/License-BSD--2--Clause-blue.svg)](./LICENSE)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20FreeBSD%20%7C%20macOS-lightgrey)
[![Issues](https://img.shields.io/github/issues/Sheridan-Internet/fa-subset.svg)](https://github.com/Sheridan-Internet/fa-subset/issues)
[![Last commit](https://img.shields.io/github/last-commit/Sheridan-Internet/fa-subset.svg)](https://github.com/Sheridan-Internet/fa-subset/commits/main)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)
![Powered by fonttools](https://img.shields.io/badge/powered%20by-fonttools-FF5A1F)

Shrink Font Awesome **webfonts** to only the icons you actually use — safely, automatically, and fast.

- **FA6 & FA5** compatible (solid, regular, light, thin, **duotone**, brands, sharp variants, FA5 aliases)
- Works with **minified CSS** and **chained selectors** (e.g. `.fa-duotone.fa-house:after`)
- Handles **duotone’s dual codepoints** (`"\f015\f015"`)
- Ignores **non-icons** (sizes like `fa-2x`, utilities like `fa-fw`, animations, etc.)
- **Multi-pack** subsetting (one subset per family)
- **Dry-run** report with per-file & per-icon breakdown (+ JSON)
- Sensible defaults; **strict checks** available

> **Not affiliated with Font Awesome / Fonticons, Inc.**  
> Bring your own licensed FA CSS/fonts and comply with your Font Awesome license (Free or Pro).  
> This tool never ships FA assets; it subsets the files **you** provide.

---

## Why

Browsers download the **entire font file** once any glyph is needed. If your site uses 100 icons but your FA font ships thousands, you pay for everything.

This tool builds tiny, per-style fonts that contain **only** the glyphs you actually use. Real numbers from production:

- Fonts: **803 KB → 14.5 KB** (**98.2% reduction**)
- Total FA payload (CSS + fonts): **~1.29 MB → ~0.50 MB** (**~61% reduction**)

Faster first paint, happier Lighthouse, less bandwidth — especially for mobile users.

---

## Requirements

- Python **3.9+**
- [`fonttools`](https://github.com/fonttools/fonttools) (for `pyftsubset`)

```bash
pip install fonttools
```

- Your own Font Awesome CSS & font files (Free or Pro).  
  **Do not** commit these assets to the repo if they’re licensed.

---

## Quick Start

1. Clone this repository or add the script to your project (`bin/fa-subset.py`).
2. Run a **dry run** to preview what will be sub‑set:

```bash
python3 bin/fa-subset.py \
  --src ./src ./templates ./module \
  --ext .phtml .php .twig .html \
  --pack solid:css=./public/css/fontawesome.min.css,font=./public/webfonts/fa-solid-900.ttf \
  --pack duotone:css=./public/css/duotone.min.css,font=./public/webfonts/fa-duotone-900.ttf \
  --pack brands:css=./public/css/brands.min.css,font=./public/webfonts/fa-brands-400.ttf \
  --out ./public/css/fa-custom \
  --default-pack solid \
  --strict-styles \
  --dry-run --report-json ./public/css/fa-custom/report.json
```

3. Build the subsets (remove `--dry-run`):

```bash
python3 bin/fa-subset.py \
  --src ./src ./templates ./module \
  --ext .phtml .php .twig .html \
  --pack solid:css=./public/css/fontawesome.min.css,font=./public/webfonts/fa-solid-900.ttf \
  --pack duotone:css=./public/css/duotone.min.css,font=./public/webfonts/fa-duotone-900.ttf \
  --pack brands:css=./public/css/brands.min.css,font=./public/webfonts/fa-brands-400.ttf \
  --out ./public/css/fa-custom \
  --default-pack solid \
  --strict-styles
```

4. Include the emitted CSS alongside your app:

```html
<link rel="stylesheet" href="/css/fa-custom/solid/fontawesome.solid.subset.min.css">
<link rel="stylesheet" href="/css/fa-custom/duotone/fontawesome.duotone.subset.min.css">
<!-- add brands/sharp subsets if you used them -->
```

> **Tip:** The CSS you reference for each `--pack` **must include icon rules**. For FA6, that’s typically `all(.min).css` or the per‑style files like `duotone(.min).css`, `solid(.min).css`, etc. If a file lacks icon rules, the script will warn you.

---

## CLI Usage

```
usage: fa-subset.py --src DIR [DIR ...] --pack name:css=PATH,font=PATH [--pack ...] --out DIR [options]
```

### Required
- `--src DIR [DIR…]` — Directories to scan (recursive).
- `--pack name:css=PATH,font=PATH` — Repeat per FA **pack** (e.g., `solid`, `duotone`, `brands`, `sharp-*`).
- `--out DIR` — Output directory (subfolders per pack).

### Useful options
- `--ext .twig .phtml .php .html` — Restrict scanning to these extensions (default: all non‑binary).
- `--dry-run` — Don’t write fonts/CSS; print a human report (plus optional JSON).
- `--report-json PATH` — Write a machine‑readable report (icons per pack, per‑file mapping, conflicts).
- `--default-pack {solid,regular,light,thin,duotone,brands,sharp-*,none}` — Style to assume if a line has no style class (default: `solid`).
- `--strict-styles` — Error out if a line mixes multiple styles (e.g., `fa-duotone` + `fa-solid`).

### Exit codes
- `0` ok
- `1` `pyftsubset` missing
- `2` no `fa-*` usage found in sources
- `4` style conflicts with `--strict-styles`

---

## What gets produced

For each `--pack NAME` you provided:

```
/out/
  NAME/
    fontawesome.NAME.subset.woff2
    fontawesome.NAME.subset.css
```

- The **subset WOFF2** contains only glyphs you actually used for that pack.
- The **subset CSS** keeps required base rules/variables and the icon rules for used icons.

---

## How it works (high level)

1. **Scan** source for `fa-*` tokens and detect the **style** on each line (`fa-solid`, `fa-duotone`, `fa-brands`, sharp variants, or FA5 aliases like `fas`, `fad`).
2. **Parse** your FA CSS to map **icon → codepoints**. Works on minified CSS and chained selectors (`.fa-duotone.fa-house:after`). Handles duotone’s **two layers**.
3. **Subset** each pack’s font via `pyftsubset` to just those codepoints; emit WOFF2.
4. **Trim CSS** to keep essential base + used icon rules.

---

## Choosing the right CSS file

The CSS you pass per pack needs the **icon rules** (e.g., `.fa-house:before { content:"\f015" }`).

- **Usually works:** `all(.min).css` for all styles, or per‑style files `solid(.min).css`, `duotone(.min).css`, `brands(.min).css`, etc.
- **May not work:** a core `fontawesome(.min).css` that only defines variables/base without per‑icon mappings (you’ll see a warning and zero mappings).

You can point multiple packs at the same combined CSS (e.g., `all.min.css`), or at their own per‑style CSS — both are fine.

---

## JSON report (schema)

When `--report-json PATH` is provided, the file contains:

```json
{
  "packs": {
    "solid": {
      "icons_found": ["user", "house", "..."],
      "icons_missing_in_css": [],
      "codepoints": ["U+F007", "U+F015"],
      "icons_to_files": {"user": ["templates/nav.phtml"], "house": ["..."]}
    },
    "duotone": { "...": "..." }
  },
  "conflicts": [
    {"file": "templates/nav.phtml", "line": 42, "icon": "screwdriver-wrench", "styles": ["duotone", "solid"]}
  ],
  "missing_pack_refs": [
    {"file": "...", "line": 1, "icon": "...", "wanted_pack": "sharp-duotone"}
  ],
  "file_to_icons": {
    "templates/nav.phtml": [ {"pack": "solid", "icon": "user"} ]
  }
}
```

Use it in CI to fail builds on conflicts or unexpected style usage.

---

## Best practices

- **Cache aggressively:** serve subset CSS/WOFF2 with long `Cache-Control` and Brotli (or gzip) compression.
- **Cache busting:** include a hash in filenames (or append `?v=hash`).
- **One style per icon:** don’t mix `fa-duotone` and `fa-solid` on the same element.
- **CORS:** fonts are cross‑origin fetches — ensure your CDN/site sends permissive CORS headers if needed.

---

## Troubleshooting

**“No icon rules found in CSS”**  
Use `all(.min).css` or the per‑style CSS with icon selectors. The tool warns if the file you passed is only a variables/base sheet.

**Duotone icons not rendering**  
Verify the duotone pack is provided (`--pack duotone:css=...,font=fa-duotone-900.ttf`) and your markup uses `fa-duotone` (not mixed with `fa-solid`).

**Mixed styles warning**  
Fix markup to one style per icon. Or run without `--strict-styles` if you want a soft warning.

**Subset WOFF2 is empty/tiny**  
No icons matched that pack. Check your `--ext` filters and style classes.

**Fonts load but icons show tofu (squares)**  
Check that the subset CSS is included **after** your theme overrides, and that the `@font-face src` URLs are reachable (Network tab). Verify CORS.

---

## Performance results (real-world example)

**Fonts**

- **Original**: Solid **345 KB** (`fa-solid-900.woff2`), Duotone **458 KB** (`fa-duotone-900.woff2`) — **Total 803 KB**
- **Optimized**: Solid **2.5 KB** (`fontawesome.solid.subset.woff2`), Duotone **12 KB** (`fontawesome.duotone.subset.woff2`) — **Total 14.5 KB**

**Reductions**

- Solid: **345 KB → 2.5 KB** (**−99.3%**)
- Duotone: **458 KB → 12 KB** (**−97.4%**)
- Overall fonts: **803 KB → 14.5 KB** (**−98.2%**)

**Icons included**

- Solid pack: **20** icons
- Duotone pack: **99** icons
- Brands pack: **0** icons (not used)

> CSS size remains roughly the same in conservative mode (keeps base rules/variables); the **huge win is the fonts**. You can enable an aggressive trimming mode if you want to shrink CSS further.

## Optional: aggressive CSS trimming (advanced)

By default, the subset CSS keeps all base rules/variables to be maximally safe. If you need smaller CSS, you can modify the writer to keep only:

- `@font-face` for the subset font
- Base **style** classes you actually use (e.g., `.fa-solid`, `.fa-duotone`)
- **Modifiers** you actually use (`fa-2x`, `fa-fw`, animations, etc.)
- The **icon rules** for used icons

This can reduce a ~490 KB minified sheet to tens of KB, but increases maintenance risk. Consider making it opt‑in behind a flag.

---

## Project policy & licensing

- **No Font Awesome assets are shipped.** You must supply your own FA CSS/fonts and comply with your Font Awesome licence. Not affiliated with Fonticons, Inc.
- Licensed under **BSD-2-Clause**. © 2025 Sheridan Internet Limited.  
  See [`LICENSE`](./LICENSE) for the full text.

## Authors
- **Sam Sheridan** — original author & maintainer

## Maintainers
- **Sheridan Internet**

---

## Contributing

Issues and PRs welcome! Please:
- Include reproduction steps and a minimal sample if reporting CSS parsing issues.
- Add/adjust fixtures in `examples/` and tests in `tests/` for parser changes.
- Keep dependencies minimal (only `fonttools`).

---

## Minimal repo skeleton

```
fa-subset/
├─ bin/fa-subset.py                  # the main script (CLI)
├─ bin/fa-minify.sh                 # optional CSS minifier
├─ examples/
│  ├─ sample.html                   # tiny demo page (no FA assets)
│  └─ sample.css                    # synthetic test CSS you wrote yourself
├─ tests/
│  └─ test_parser.py                # unit tests against sample.css/html
├─ .gitignore
├─ LICENSE                          # BSD-2-Clause
├─ README.md
└─ pyproject.toml                   # optional: package as a CLI
```

**.gitignore** (protect yourself):

```
*.woff
*.woff2
*.ttf
*.otf
*.eot
public/webfonts/
public/css/*fontawesome*.css
public/css/*duotone*.css
public/css/*solid*.css
```

---

## Using with Composer (Mezzio/Laminas)

Add handy scripts to your `composer.json` so anyone on the team can analyze/optimize with a single command.

> **Prereqs:** `python3` and `pyftsubset` (from `fonttools`) must be on `PATH`.

### Example `composer.json` snippet

```json
{
  "scripts": {
    "fa-analyze": "python3 bin/fa-subset.py --src ./src ./templates --ext .phtml .php .html .twig --pack solid:css=./public/css/fontawesome.min.css,font=./public/webfonts/fa-solid-900.ttf --pack duotone:css=./public/css/duotone.min.css,font=./public/webfonts/fa-duotone-900.ttf --out ./public/css/fa-custom --default-pack solid --dry-run --report-json ./public/css/fa-custom/fa-report.json",
    "fa-optimize": [
      "python3 bin/fa-subset.py --src ./src ./templates --ext .phtml .php .html .twig --pack solid:css=./public/css/fontawesome.min.css,font=./public/webfonts/fa-solid-900.ttf --pack duotone:css=./public/css/duotone.min.css,font=./public/webfonts/fa-duotone-900.ttf --out ./public/css/fa-custom --default-pack solid",
      "@fa-minify"
    ],
    "fa-minify": "sh bin/fa-minify.sh",
    "fa-check": "python3 bin/fa-subset.py --src ./src ./templates --ext .phtml .php .html .twig --pack solid:css=./public/css/fontawesome.min.css,font=./public/webfonts/fa-solid-900.ttf --pack duotone:css=./public/css/duotone.min.css,font=./public/webfonts/fa-duotone-900.ttf --out ./public/css/fa-custom --default-pack solid --strict-styles --dry-run --report-json ./public/css/fa-custom/fa-report.json"
  }
}
```

### Run it

```bash
composer fa-analyze   # dry-run report + JSON
composer fa-optimize  # write subset fonts + CSS, then minify CSS
composer fa-check     # strict CI-style analysis (fails on conflicts)
```

> If you don’t use Brands (or other packs), omit those `--pack` lines to skip generating unused subsets.

---

## CI (optional)

`.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -U pip fonttools pytest
      - run: pytest -q
```

## Minifying the subset CSS (optional)

This repo includes a small helper: `bin/fa-minify.sh`.  
It cleans the subset CSS and rewrites `@font-face` URLs to the local subset `.woff2`.

**What it does**
- Flattens/minifies whitespace (safe “micro-minify”).
- Rewrites `url(../webfonts/...)` (quoted or unquoted) → `url(fontawesome.<pack>.subset.woff2)`.
- Removes legacy `.ttf` fallbacks (and their `format('truetype')`) from `@font-face`.
- Auto-detects **Linux/FreeBSD/macOS** `sed` features (prefers `gsed` if available).

**When to run**
Run it after `fa-subset.py` has generated:

```
public/css/fa-custom/<pack>/fontawesome.<pack>.subset.css
public/css/fa-custom/<pack>/fontawesome.<pack>.subset.woff2
```

**Composer scripts**

```json
{
  "scripts": {
    "fa-optimize": [
      "python3 bin/fa-subset.py --src ./src ./templates --ext .phtml .php .html .twig --pack solid:css=./public/css/fontawesome.min.css,font=./public/webfonts/fa-solid-900.ttf --pack duotone:css=./public/css/duotone.min.css,font=./public/webfonts/fa-duotone-900.ttf --out ./public/css/fa-custom --default-pack solid",
      "@fa-minify"
    ],
    "fa-minify": "sh bin/fa-minify.sh"
  }
}
```

### Manual usage

```bash
chmod +x bin/fa-minify.sh
sh bin/fa-minify.sh
```

### Output
For each pack (e.g., solid, duotone) you’ll get: 

`public/css/fa-custom/<pack>/fontawesome.<pack>.subset.min.css`

Reference the .min.css in your HTML (it points at the subset .woff2).

Tip: keep the original FA CSS/fonts out of production if you don’t need them; the subset CSS is self-contained.

### Troubleshooting

- Icons show blank/squares → ensure you’re including the new fontawesome.<pack>.subset.min.css (not the original sheet), and the .woff2 is being served (check DevTools → Network).
- Browser still requests original FA fonts → your CSS wasn’t rewritten; re-run fa-minify and verify the url(...) now points to fontawesome.<pack>.subset.woff2.
- CORS errors on fonts → serve the .woff2 from the same origin as the page or add the correct Access-Control-Allow-Origin header.

---

## Acknowledgments

- The awesome `fonttools` project for robust font subsetting.
- Font Awesome for their icon ecosystem (again: this project isn't affiliated).

---

**Happy subsetting!** 🎯

---

Made by [Sheridan Internet Limited](https://sheridaninternet.com)


#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2025 Sheridan Internet Limited
"""
Font Awesome subsetting for FA6 (multi-pack) + FA5 compatibility.

Features:
- Finds fa-* icon uses in source files (twig, phtml, html, php, etc.)
- Detects FA6 style classes on the same line (fa-solid, fa-duotone, fa-brands, ...)
- Properly handles duotone icons (fa-duotone is a style, not an icon name)
- Assigns each icon to the correct PACK (font) based on style classes
- Parses each pack's CSS to resolve icon -> codepoint(s) (supports ::before/::after)
- Subsets each pack's font separately and emits one trimmed CSS per pack
- Keeps FA6 base rules and CSS variables needed for styles/duotone

Usage example (Solid + Brands + Duotone):
  python strip-fa.py \
    --src ./templates ./module ./src \
    --ext .twig .phtml .php .html \
    --pack solid:css=./public/css/solid.min.css,font=./public/webfonts/fa-solid-900.ttf \
    --pack brands:css=./public/css/brands.min.css,font=./public/webfonts/fa-brands-400.ttf \
    --pack duotone:css=./public/css/duotone.min.css,font=./public/webfonts/fa-duotone-900.ttf \
    --out ./public/css/fa-subset \
    --default-pack solid \
    --dry-run --report-json ./public/css/fa-subset/report.json

Quality-of-life options:
  --default-pack solid   # Assigns unstyled icons (fa fa-house) to solid pack
  --strict-styles        # Fails if multiple styles on same line (catches errors)

Output structure:
  ./public/css/fa-subset/
    solid/fontawesome.solid.subset.woff2 + .css
    duotone/fontawesome.duotone.subset.woff2 + .css
    brands/fontawesome.brands.subset.woff2 + .css

Requires: pip install fonttools brotli
"""
import argparse, re, sys, subprocess, shutil, json
from pathlib import Path
from collections import defaultdict

# ---- Regexes
# Icon names: fa-<name> and FA5 short prefixes (fas-, far-, fal-, fab-, fad-)
ICON_NAME_RX = re.compile(r'\bfa(?:s|r|l|b|d|-)?-([a-z0-9-]+)\b', re.I)

# FA6 style classes (long names) + FA5 short names
STYLE_RX = re.compile(
    r'\b(?:'
    r'fa-(?:solid|regular|light|thin|duotone|brands|sharp-solid|sharp-regular|sharp-light|sharp-thin|sharp-duotone)'
    r'|fas|far|fal|fat|fab|fad'
    r')\b', re.I
)

# Match CSS selectors with content rules for FA5/6 (handles compound selectors and duotone double-codepoints) and CSS variable for FA7
CSS_SELECTOR_CONTENT_RX = re.compile(
    r'(?P<selector>[^{}]+?)\s*(?::\s*(?:before|after)\s*\{[^}]*?content|\{[^}]*?--fa)\s*:\s*["\']\\(?P<hex>[0-9a-fA-F]{3,6})(?:\\[0-9a-fA-F]{3,6})?["\']',
    re.I
)


# Keep essential blocks: FA5 short style classes, FA6 long style classes, @font-face, and CSS variables.
BASE_RULE_KEEPERS = (
    re.compile(r'\.fa(?:s|r|l|b|d)?[^-]'),  # FA5 base
    re.compile(r'\.fa-(?:solid|regular|light|thin|duotone|brands|sharp-solid|sharp-regular|sharp-light|sharp-thin|sharp-duotone)[^-]'),
    re.compile(r'@font-face', re.I),
    re.compile(r'--fa-'),  # FA6 CSS variables
)

# ---- Helpers
SKIP_BIN_SUFFIXES = {
    '.png','.jpg','.jpeg','.gif','.webp','.svg','.ico',
    '.woff','.woff2','.ttf','.otf','.eot',
    '.pdf','.zip','.gz','.br'
}

# Map style tokens to "pack" keys
STYLE_TO_PACK = {
    # FA6 long names
    'fa-solid':'solid','fa-regular':'regular','fa-light':'light','fa-thin':'thin',
    'fa-duotone':'duotone','fa-brands':'brands',
    'fa-sharp-solid':'sharp-solid','fa-sharp-regular':'sharp-regular',
    'fa-sharp-light':'sharp-light','fa-sharp-thin':'sharp-thin','fa-sharp-duotone':'sharp-duotone',
    # FA5 short aliases
    'fas':'solid','far':'regular','fal':'light','fat':'thin','fad':'duotone','fab':'brands'
}

# Set of style class names (used for filtering in CSS parsing)
STYLE_CLASS_SET = {
    # FA6 long
    'fa-solid','fa-regular','fa-light','fa-thin','fa-duotone','fa-brands',
    'fa-sharp-solid','fa-sharp-regular','fa-sharp-light','fa-sharp-thin','fa-sharp-duotone',
    # FA5 short
    'fas','far','fal','fat','fad','fab',
}

# FA "non-icon" tokens to ignore (sizes, rotations, flips, animations, utilities)
MODIFIER_TOKENS = {
    # sizes (FA6)
    'fa-2xs','fa-xs','fa-sm','fa-lg','fa-xl','fa-2xl',
    # legacy sizes
    'fa-fw','fa-li','fa-border','fa-inverse','fa-stack','fa-stack-1x','fa-stack-2x',
    # rotations & flips
    'fa-rotate-90','fa-rotate-180','fa-rotate-270',
    'fa-flip','fa-flip-horizontal','fa-flip-vertical','fa-flip-both',
    # animations
    'fa-spin','fa-pulse','fa-spin-pulse','fa-beat','fa-bounce','fa-fade','fa-beat-fade','fa-shake',
    # layout
    'fa-pull-left','fa-pull-right','fa-fixed-width',
    # style aliases we never want to count as icons (extra safety)
    'fa-solid','fa-regular','fa-light','fa-thin','fa-duotone','fa-brands',
    'fas','far','fal','fat','fad','fab'
}

# Also accept Nx numeric sizes like fa-3x, fa-10x
MODIFIER_NUMERIC_RX = re.compile(r'^fa-(?:[1-9]|10)x$', re.I)

def is_non_icon_token(token):
    """Check if token is a modifier/style, not an actual icon.

    Args:
        token: Full FA token including 'fa-' prefix (e.g., 'fa-2x', 'fa-solid', 'fa-house')

    Returns:
        True if token is a modifier, size, style, or utility class
        False if token is an actual icon name
    """
    t = token.lower()
    return t in MODIFIER_TOKENS or bool(MODIFIER_NUMERIC_RX.match(t)) or t in STYLE_CLASS_SET

def parse_packs(raw_packs):
    """Parse command-line pack specifications into structured format.

    Each --pack is like:
      solid:css=path,font=path

    Args:
        raw_packs: List of pack specifications from command line

    Returns:
        dict: pack_key -> {'css':Path,'font':Path}

    Exits:
        System exit with code 1 if pack format is invalid
    """
    packs = {}
    for spec in raw_packs:
        try:
            name, rest = spec.split(':', 1)
            parts = dict(x.split('=',1) for x in rest.split(','))
            css = Path(parts['css']); font = Path(parts['font'])
            packs[name] = {'css': css, 'font': font}
        except Exception:
            print(f"Invalid --pack format: {spec}", file=sys.stderr); sys.exit(1)
    return packs

def collect_usage(src_dirs, exts, default_pack='solid'):
    """Scan source files to collect Font Awesome icon usage.

    Scans files line-by-line. For each line:
      - Collects icon names (e.g., 'house' from 'fa-house')
      - Collects style tokens (e.g., 'fa-solid', 'fa-duotone')
      - Assigns icons to detected pack(s). If none detected, uses default_pack

    Args:
        src_dirs: List of directories to scan recursively
        exts: List of file extensions to include (e.g., ['.html', '.php'])
              If empty, scans all non-binary files
        default_pack: Pack to assign unstyled icons to ('solid', 'duotone', etc.)
                     Use 'none' to mark unstyled icons as 'unknown'

    Returns:
        tuple containing:
          - pack_to_icon_files: dict[pack -> dict[icon -> set[file]]]
          - file_to_icons: dict[file -> set[(pack, icon)]]
          - conflicts: list of (file, line_no, icon, styles_detected)
    """
    extset = set(e.lower() for e in exts) if exts else None
    pack_to_icon_files = defaultdict(lambda: defaultdict(set))
    file_to_icons = defaultdict(set)
    conflicts = []

    for root in src_dirs:
        for p in Path(root).rglob('*'):
            if not p.is_file(): continue
            suf = p.suffix.lower()
            if suf in SKIP_BIN_SUFFIXES: continue
            if extset is not None and suf not in extset: continue

            try:
                lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
            except Exception:
                continue

            for idx, line in enumerate(lines, start=1):
                # Find all fa-<something> tokens on the line
                tokens = [f'fa-{m.group(1).lower()}' for m in ICON_NAME_RX.finditer(line)]
                # Keep only real icons (not styles/modifiers)
                # Note: is_non_icon_token expects full token with 'fa-' prefix
                icons = [t[3:] for t in tokens if not is_non_icon_token(t)]
                if not icons: continue
                styles = [m.group(0).lower() for m in STYLE_RX.finditer(line)]
                packs_here = {STYLE_TO_PACK[s] for s in styles if s in STYLE_TO_PACK}
                if len(packs_here) == 0:
                    # Use default pack if specified, otherwise 'unknown'
                    if default_pack != 'none':
                        packs_here = {default_pack}
                    else:
                        packs_here = {'unknown'}
                if len(packs_here) > 1:
                    for ic in icons:
                        conflicts.append((p, idx, ic, sorted(packs_here)))
                for ic in icons:
                    for pack in packs_here:
                        pack_to_icon_files[pack][ic].add(p)
                        file_to_icons[p].add((pack, ic))
    return pack_to_icon_files, file_to_icons, conflicts

def build_mapping(css_path):
    """Parse CSS file to extract icon name to codepoint mappings.

    Handles minified CSS, compound selectors (e.g., '.fa-duotone.fa-house'),
    and duotone's double codepoints.

    Args:
        css_path: Path to Font Awesome CSS file

    Returns:
        tuple: (mapping dict[icon_name -> set[codepoints]], raw CSS string)
    """
    css = css_path.read_text(encoding='utf-8', errors='ignore')
    mapping = defaultdict(set)

    for m in CSS_SELECTOR_CONTENT_RX.finditer(css):
        selector = m.group('selector')
        cp = int(m.group('hex'), 16)

        # A rule can have multiple selectors separated by commas
        for sel in selector.split(','):
            # Find all .fa-xxx tokens in the selector (chained classes allowed)
            classes = re.findall(r'\.fa-([a-z0-9-]+)', sel, flags=re.I)
            if not classes:
                continue
            # Take the last candidate that is NOT a style class or modifier
            # This handles compound selectors like '.fa-duotone.fa-house'
            for name in reversed(classes):
                token = f'fa-{name}'.lower()
                if not is_non_icon_token(token):
                    mapping[name.lower()].add(cp)
                    break
    return mapping, css

def write_subset_css(full_css, used_icons, out_css_path):
    """Write subset CSS containing only used icons and required base rules.

    Preserves:
      - @font-face declarations
      - FA base classes and utilities
      - CSS variables (--fa-*)
      - Rules for actually used icons

    Args:
        full_css: Complete CSS content
        used_icons: Set of icon names that are actually used
        out_css_path: Path to write subset CSS
    """
    out_lines = []
    block_rx = re.compile(r'[^{}]+{[^{}]*}')
    for m in block_rx.finditer(full_css):
        block = m.group(0)
        keep = False
        if any(rx.search(block) for rx in BASE_RULE_KEEPERS):
            keep = True
        # Check if this block contains any of our used icon names
        # Extract icon names from the selector part (before the brace)
        selector_part = block.split('{')[0] if '{' in block else block
        classes = re.findall(r'\.fa-([a-z0-9-]+)', selector_part, flags=re.I)
        for name in classes:
            token = f'fa-{name}'.lower()
            if token not in STYLE_CLASS_SET and name.lower() in used_icons:
                keep = True
                break
        if keep:
            out_lines.append(block)
    out_css_path.write_text('\n'.join(out_lines), encoding='utf-8')

def subset_font(font_path, codepoints, out_path_woff2):
    """Create subset font containing only specified codepoints.

    Uses pyftsubset to extract only the glyphs needed, creating
    a much smaller WOFF2 font file.

    Args:
        font_path: Path to source font file (TTF/OTF)
        codepoints: Set of Unicode codepoints to include
        out_path_woff2: Path to write subset WOFF2 font

    Exits:
        System exit with code 1 if pyftsubset is not installed
    """
    if not shutil.which('pyftsubset'):
        print("ERROR: 'pyftsubset' not found. Install: pip install fonttools", file=sys.stderr)
        sys.exit(1)
    if not codepoints:
        return
    unicodes_arg = ",".join(f"U+{cp:04X}" for cp in sorted(codepoints))
    cmd = [
        'pyftsubset', str(font_path),
        f'--unicodes={unicodes_arg}',
        '--flavor=woff2',
        '--layout-features=*',
        '--name-IDs=',
        '--no-hinting',
        f'--output-file={out_path_woff2}'
    ]
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', nargs='+', required=True)
    ap.add_argument('--ext', nargs='*', default=[], help='e.g. .html .twig .phtml .php')
    ap.add_argument('--pack', action='append', required=True,
                    help='name:css=PATH,font=PATH  (repeat per FA pack)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report-json')
    ap.add_argument('--default-pack',
                    choices=list(set(STYLE_TO_PACK.values())) + ['none'],
                    default='solid',
                    help='Pack to use when no style is present (default: solid)')
    ap.add_argument('--strict-styles', action='store_true',
                    help='Error if multiple styles are present on the same line')
    args = ap.parse_args()

    packs = parse_packs(args.pack)
    out_dir = Path(args.out)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    # Scan usage
    pack_to_icon_files, file_to_icons, conflicts = collect_usage(args.src, args.ext, args.default_pack)

    # Check for strict mode
    if args.strict_styles and conflicts:
        print("\n❌ ERROR: Style conflicts detected (--strict-styles enabled):", file=sys.stderr)
        for f, ln, ic, styles in conflicts[:10]:
            print(f"  {f}:{ln} icon={ic} styles={','.join(styles)}", file=sys.stderr)
        if len(conflicts) > 10:
            print(f"  ... and {len(conflicts)-10} more conflicts", file=sys.stderr)
        sys.exit(4)

    # Build mappings per pack
    pack_map = {}
    pack_css = {}
    for name, conf in packs.items():
        mapping, css = build_mapping(conf['css'])
        if not mapping:
            print(f"⚠️  [{name}] No icon rules found in {conf['css']}. "
                  f"Use all.min.css or the style CSS (e.g., solid.min.css, duotone.min.css).",
                  file=sys.stderr)
        pack_map[name] = mapping
        pack_css[name] = css

    # Prepare report + codepoints
    report = {
        'packs': {},
        'conflicts': [
            {'file': str(f), 'line': ln, 'icon': ic, 'styles': st}
            for (f, ln, ic, st) in conflicts
        ],
        'file_to_icons': {str(f): sorted([{'pack':p,'icon':i} for (p,i) in s], key=lambda x:(x['pack'],x['icon']))
                          for f, s in file_to_icons.items()},
    }

    for name in packs.keys():
        used_icons = set(pack_to_icon_files.get(name, {}))
        mapping = pack_map.get(name, {})
        missing = sorted([ic for ic in used_icons if ic not in mapping])
        cps = set()
        for ic in used_icons:
            if ic in mapping:
                cps.update(mapping[ic])

        report['packs'][name] = {
            'icons_found': sorted(used_icons),
            'icons_missing_in_css': missing,
            'codepoints': [f"U+{cp:04X}" for cp in sorted(cps)],
            'icons_to_files': {
                ic: sorted(str(p) for p in pack_to_icon_files[name][ic])
                for ic in sorted(pack_to_icon_files.get(name, {}))
            }
        }

    # Print human-readable summary
    print("=== Font Awesome Subset Report ===")
    for name in packs.keys():
        p = report['packs'][name]
        print(f"\n[{name}] icons found: {len(p['icons_found'])}, resolved: {len(p['codepoints'])}")
        if p['icons_missing_in_css']:
            print("  ⚠ Missing in CSS mapping:", ", ".join(p['icons_missing_in_css']))
    if conflicts:
        print("\nConflicts (multiple styles on one line):")
        for c in conflicts[:20]:
            print(f"  {c[0]}:{c[1]} icon={c[2]} styles={','.join(c[3])}")
        if len(conflicts) > 20:
            print(f"  ... and {len(conflicts)-20} more")

    # Handle dry-run mode - report only, don't write files
    if args.dry_run:
        if args.report_json:
            Path(args.report_json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.report_json).write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(f"\nWrote JSON report → {args.report_json}")
        print("\nNothing written (dry run).")
        return

    # Write subsets per pack
    for name, conf in packs.items():
        used_icons = set(report['packs'][name]['icons_found'])
        mapping = pack_map[name]
        cps = set()
        for ic in used_icons:
            if ic in mapping:
                cps.update(mapping[ic])

        pack_out = out_dir / name
        pack_out.mkdir(parents=True, exist_ok=True)
        out_woff2 = pack_out / f'fontawesome.{name}.subset.woff2'
        out_css = pack_out / f'fontawesome.{name}.subset.css'

        subset_font(conf['font'], cps, out_woff2)
        write_subset_css(pack_css[name], used_icons, out_css)

        print(f"\n[{name}] subset complete:")
        print(f"  CSS : {out_css}")
        print(f"  Font: {out_woff2}")

    print("\nDone.")

if __name__ == '__main__':
    main()


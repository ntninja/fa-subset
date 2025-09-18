#!/usr/bin/env sh
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2025 Sheridan Internet Limited
#
# fa-minify.sh - Minify Font Awesome subset CSS and fix font URLs
#
# This script:
#  1. Minifies the subset CSS files (removes unnecessary whitespace)
#  2. Rewrites font URLs to point to local subset .woff2 files
#  3. Removes legacy .ttf font fallbacks that aren't needed for modern browsers
#
# Run after fa-subset.py has generated the subset CSS/WOFF2 files.
#
set -eu

# Detect available sed implementation
# Prefer gsed (GNU sed) if available, as it has more consistent behaviour
# across platforms. Falls back to system sed if gsed isn't installed.
if command -v gsed >/dev/null 2>&1; then
  SED="gsed"
else
  SED="sed"
fi

# Detect support for -E (extended regex) flag
# The -E flag enables extended regular expressions, making patterns cleaner.
# Supported by: FreeBSD sed, macOS sed, and modern GNU sed (v4.2+)
# If not available, we fall back to POSIX-compliant basic regex.
if "$SED" -E 's/a/a/' </dev/null >/dev/null 2>&1; then
  HAVE_E=1
else
  HAVE_E=0
fi

# Process each pack's subset CSS (solid, duotone, brands, etc.)
for dir in public/css/fa-custom/*/; do
  [ -d "$dir" ] || continue
  dir=${dir%/}  # Strip trailing slash to avoid // in paths
  name=$(basename "$dir")  # Extract pack name (solid, duotone, etc.)
  css="$dir/fontawesome.$name.subset.css"
  out="$dir/fontawesome.$name.subset.min.css"
  [ -f "$css" ] || continue  # Skip if source CSS doesn't exist

  if [ "$HAVE_E" -eq 1 ]; then
    # Extended regex path (cleaner, more efficient)
    tr -d '\n' < "$css" \
    | "$SED" 's/  */ /g; s/: /:/g; s/; /;/g; s/ {/{/g; s/} /}/g' \
    | "$SED" -E "s|url\(([\"'])?\.\./webfonts/[^)]*\)|url(fontawesome.$name.subset.woff2)|g" \
    | "$SED" -E 's|,?[[:space:]]*url\([^)]+\.ttf[^)]*\)[[:space:]]*(format\([^)]+\))?||g' \
    > "$out"
  else
    # POSIX-compliant fallback (no -E flag): requires multiple passes
    # Less efficient but maximally compatible with older/minimal systems
    tr -d '\n' < "$css" \
    | "$SED" 's/  */ /g; s/: /:/g; s/; /;/g; s/ {/{/g; s/} /}/g' \
    | "$SED" 's|url("../webfonts/|url(../webfonts/|g; s|url('"'"'../webfonts/|url(../webfonts/|g' \
    | "$SED" "s|url(../webfonts/[^)]*)|url(fontawesome.$name.subset.woff2)|g" \
    | "$SED" 's|, *url([^)]*\.ttf[^)]*) *format([^)]*)||g' \
    | "$SED" 's|url([^)]*\.ttf[^)]*) *format([^)]*)||g' \
    | "$SED" 's|, *url([^)]*\.ttf[^)]*)||g' \
    | "$SED" 's|url([^)]*\.ttf[^)]*)||g' \
    | "$SED" 's/ ,/,/g; s/,,/,/g' \
    > "$out"
  fi
done

# Report completion
echo "Minified CSS files created in subdirectories"

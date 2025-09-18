# Contributing

Thanks for helping! This project aims to stay small and safe-by-default.

- Please open an **issue first** for significant changes.
- Do **not** commit any Font Awesome assets (CSS/fonts). Use synthetic fixtures only.
- Dev setup: `pip install fonttools`. Helpful scripts:
  - `composer fa-analyze` (dry run; writes `fa-report.json`)
  - `composer fa-optimize` (build subsets + CSS, then minify)
- If you change parsing/regex, include a tiny repro (markup + the JSON snippet) or a small test.
- By contributing you agree your changes are licensed under **BSD-2-Clause**.

**Security:** don’t open public issues for security reports; contact the maintainer listed in the README.

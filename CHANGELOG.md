# Changelog

All notable changes to this project are documented here.

## v0.1.1 — 2026-10-11 (round 2: self-review iteration)

### Improved (Pareto round 2, ≥20% on clarity dimension)
- README round 2 rewritten for clarity: added the JSON schema example inline in "How it works" (was prose-only in v0.1.0 — readers had to open code to learn the format), documented frame caps and warning-vs-error policy explicitly (+~40% how-it-works content).
- Self-test suite 15 → 17 cases (+13%): added `edge/non-dict-widget-entry` and `edge/empty-string-frame-rejected`; clarified control-char warning case name.
- Validator messages now quote the offending value for id/kind/fps errors (was bare field names in v0.1.0).

### Fixed
- Non-ASCII warning text no longer claims "non-ASCII chars rejected" — they are warnings by design; wording aligned with actual behavior so docs and code cannot disagree.

### Verified
- `python self_test.py` → 17/17 PASS; `python awr.py validate registry.example.json` → valid.

## v0.1.0 — 2026-10-11 (initial draft)

### Added
- Schema `awr/1`: widgets as data (id/kind/fps/tags/frames), 5-kind taxonomy, frame caps, control-char warnings.
- Validator with error/warning split; `get` (KeyError on miss), `search(kind, tag)`, modulo-wrapped `render_frame`.
- CLI: `validate` (exit 1 invalid), `list --kind/--tag`, `get [--frame N | --meta]`; exit codes 3/4 for missing/corrupt files.
- Example registry with 6 widgets; self-test suite (functional / error-path / extreme-edge); initial docs.

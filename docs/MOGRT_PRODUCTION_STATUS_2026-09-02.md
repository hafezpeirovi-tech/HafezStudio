# Hafez Studio MOGRT production status — 2026-09-02

## Scope

This pass converts the curated user-owned After Effects elements into real
Premiere Motion Graphics Templates. It does not use rendered PNG cards and it
does not modify the original After Effects or Premiere projects.

## Source and rollback

- Original AEP (read-only): `D:\AE proj\Hermes Studio Elements.aep`
- Curated working AEP: `motion-pack/source/Hermes Studio Elements - Hafez Curated.aep`
- Rollback backup: `backups/premiere-mogrt-text-fix-20260902-153757`
- Overlay-fix backup: `backups/mogrt-overlay-fix-20260902-170000`

## Production output

- Fourteen catalogued `.mogrt` files live in `motion-pack/dist`.
- The same templates are installed under Adobe's local Motion Graphics
  Templates directory in the `Hafez Studio` collection.
- The Windows package carries the exact same files under
  `release/win-unpacked/resources/motion-pack/dist`.
- The Premiere-only QA project is
  `proof/premiere-mogrt-qa/Hafez-MOGRT-QA.prproj`; the user's original Premiere
  project is not changed.

## Editable control contract

Each relevant text slot exposes Source Text, font family, font style, font
size, text color, line spacing and tracking. Templates also expose background
and glass colors, accent colors, background toggle, glass opacity, glow
intensity/radius, layout position and layout scale. Complex After Effects
shading, displacement, shadows, easing and authored motion remain baked by
After Effects as intended.

## Visual contract

- Palette tokens mirror the production Director UI: near-black glass,
  `#55FF72` primary green, `#2FD65B` secondary green, pale-green highlight and
  `#F5F7F5` text.
- Vendor full-frame demo plates, grids and colorizing carrier layers are
  disabled for transparent overlays; glass geometry, panel lighting, shadow,
  displacement and authored glow remain.
- Grain assets/effects are forbidden.
- The rule engine selects a maximum of four motion families per video and uses
  multi-frame subject union bounds for safe placement.

## Text grounding

Graphic copy is copied from source-faithful transcript spans. Numeric and Latin
tokens are locked. Unsupported paraphrases and incomplete claims are rejected;
an unresolved incomplete sentence becomes an editable `…` placeholder instead
of invented copy.

## Verification

- `scripts/validate_editorial_mogrts.py` validates catalog parity, editable
  control coverage, ABAR High FaNum fonts and grain absence.
- Active test suite: `tests/test_studio.py`.
- Premiere QA verifies an imported MOGRT renders on video and that its editable
  controls are visible in the Properties panel.

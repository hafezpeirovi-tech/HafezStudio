# Hafez Studio — Codex handoff (2026-09-01)

## Current checkpoint

The YouTube Director UI second pass is complete. The Director now uses the
approved premium dark/glass visual language with controlled top/left edge
highlights, localized neon-green emphasis, corrected spacing, and the approved
three-group hierarchy. The Adaptive slider bug is fixed and verified.

## Completed work

- Reversible pre-change backup:
  `backups/ui-second-pass-20260831-155933`
- `adaptiveValue` is the single source of truth for percentage text, thumb
  position, green fill, preview intensity, and persisted configuration.
- Valid saved values are preserved. Legacy valid `glowIntensity` values are
  migrated. Missing or invalid values fall back to `82`.
- Track click, pointer drag, and Arrow keys update the slider live.
- Geometry tests at `0`, `24`, `50`, `82`, and `100` report `0 px` difference
  between the fill endpoint and thumb center.
- All 36 Python/product contract tests pass.
- Source JavaScript syntax checks pass.
- Exact visual proofs were generated at 1672×941 and 1920×1080.
- Windows `win-unpacked` build completed and its executable passed a live
  five-second responding-process smoke test.
- The packaged `app.asar` was inspected and contains the updated UI and slider
  implementation.

## Primary changed files

- `app/index.html`
- `app/renderer.js`
- `app/styles.css`
- `electron/main.js`
- `tests/test_studio.py`
- `proof/capture-ui.js`
- `proof/test-adaptive-slider.js`
- `proof/build-visual-comparison.py`

## Proof and reports

- `proof/hafez-studio-final-1672x941.png`
- `proof/hafez-studio-1920x1080.png`
- `proof/hafez-studio-overlay-50.png` (content-aligned comparison)
- `proof/hafez-studio-overlay-50-1672x941.png` (raw exact-size comparison)
- `proof/hafez-studio-side-by-side.png`
- `proof/adaptive-slider-test.json`
- `proof/ui-capture-state-1672x941.json`
- `proof/ui-capture-state-1920x1080.json`

## Verified distributable

- Full offline portable folder: `release/win-unpacked`
- Launch executable: `release/win-unpacked/Hafez Studio.exe`
- Verification hashes: `release/Hafez-Studio-0.2.0-SHA256.txt`
- Transfer instructions: `release/Hafez-Studio-0.2.0-PORTABLE.txt`

Copy the complete `win-unpacked` directory. The executable alone is not a full
distribution because the ASR model, engine, FFmpeg, Adobe plugins, fonts, and
motion pack live under `resources`.

## NSIS installer status

The single-file NSIS installer cannot be completed with the full offline
payload. `runtime/models/whisper-fa-ct2/model.bin` is about 2.94 GB; the complete
portable payload is about 4.1 GB, and 32-bit `makensis` fails while memory-mapping
the roughly 3 GB compressed application archive. Failed/partial installer files
were removed from the main release listing and preserved under
`release/failed-nsis-over-4gb` so they cannot be mistaken for valid installers.

Recommended next packaging architecture:

1. Keep the verified full offline Portable build for personal use.
2. Build a smaller Core Installer containing the desktop app, engine, FFmpeg,
   Adobe integrations, fonts, and motion pack.
3. Ship the Persian Whisper model as a separately versioned Offline Model Pack.
4. Add a model importer/validator that installs an adjacent model pack or lets
   the buyer select an existing model directory.
5. Keep automatic personal downloads in Personal Mode only; the sellable mode
   must use buyer-owned/imported assets and models.

## New-task continuation prompt

Use this exact prompt in a new Codex task opened on the same project:

> Continue Hafez Studio from `docs/CODEX_HANDOFF_2026-09-01.md`. Read that file
> first and do not redo the completed Director UI or Adaptive slider work.
> Verify the existing portable release and propose the smallest production-grade
> Core Installer + Offline Whisper Model Pack architecture. Preserve the full
> personal offline build. Before changing Python, database, trading workflows,
> or Hermes security-sensitive code, follow AGENTS.md and obtain the required
> explicit approval. Start with a read-only packaging audit and an implementation
> plan; after approval, implement and test the split installer/model importer.


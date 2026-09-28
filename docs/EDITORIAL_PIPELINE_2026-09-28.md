# Editorial Glass — automatic compilation checkpoint

Status: **full existing review assembled automatically and saved in native Premiere; installed desktop release pending visual QA**. This supersedes the single-cue limitation in `EDITORIAL_SOURCE_BINDING_2026-09-28.md`, not its historical results.

## Implemented

- Moved the tested source-bound compiler into the engine, including its AE script and editable-font helper. The old script remains a compatible entry point.
- Added an explicit compiled-MOGRT contract: exact job folder, authoring source hashes, camera media hashes, reviewed cue text/timing, successful AE receipt, portrait/template integrity and exposed controls are independently checked.
- The optional `--editorial-glass` pipeline compiles every eligible reviewed semantic title; retains independently selected vendor families; applies one smoked-sage palette; preserves the original cut, dialogue, subtitles and duration. No additional pause is inserted by this compiler.
- `glass-editorial --manifest` upgrades an existing Glass review into a new folder/manifest. It never overwrites the original or dispatches Premiere itself.
- Desktop source routes Glass jobs to this compiler before the existing guarded native Finisher. Other styles and Upscale are unchanged.
- Consecutive AE jobs can close only the exact clean compiler-owned project. Dirty/unrelated projects are refused. A hash-bound local ownership ledger supports later jobs.
- Fixed an actual SFX validation failure: Premiere's `file://localhost/C%3A/...` and pathlib's `file:///C:/...` identify the same local file. Validation now normalizes that identity while still rejecting wrong media, remote URLs, timing/filter changes and URL queries/fragments.

## Usable Premiere artifact

Relative to this project root:

`proof/automatic-semantic-glass-20260923-05/frozen-package/editorial/Hafez-FX-Editorial-Review.prproj`

Sequence: `Hafez Glass — Automatic Timeline Review`.

The same production Finisher, not manual clip placement, created and saved this separate full-length review:

- **7 native editable MOGRT instances**: five compiled Editorial cards plus the two retained intro layers.
- Five compiled cards have **20 exposed controls each**, including six text fields with font/size editing, line spacing, colors and media replacement.
- Native readback confirms enabled V4 cards, ABAR High FaNum ExtraBold at 102 for title lines, line spacing 132, and HAFEZ-FX branding.
- Existing **142 subtitle cues, 26 camera shots, 11 punch-ins and 6 SFX cues** are retained. These counts do not imply editorial or listening approval.
- No PNG title clips; no final movie export; no music was added.

Approximate positions for review:

| Start (seconds) | Editable heading |
| --- | --- |
| 7.374 | بهترین استراتژی |
| 220.787 | احتمالات |
| 292.626 | دیتا |
| 393.593 | تکنولوژی |
| 431.364 | ریاضی و احتمالات |

Evidence in that folder: `engine-validation.json`, `native-dispatch.json`, `native-receipt.json`, `inspect-request.json`, `inspect-receipt.json`, and `compiled/<cue>/` recipes, native AE receipts, editable MOGRTs and source projects. Do not redispatch the saved native mutation. Use read-only inspection if needed.

## Verification and release state

- 13 Editorial Python tests and 74 Glass Python tests passed.
- Desktop IPC, native broker, CEP panel and bridge JavaScript suites passed.
- Candidate executable built successfully at `engine/editorial-candidate-20260928-02/dist/hermes-engine/hermes-engine.exe`; CLI exposes `--editorial-glass`.
- That frozen executable also passed `glass-validate --qa` against the actual full compiled plan (six graphics, seven MOGRT layers), with the workspace root selected explicitly.
- Shell candidate at `build/editorial-shell-20260928-01/app.asar` was derived from the actual installed shell, changing only the new Glass routing flag. It preserves current UI/Upscale code.
- **Neither candidate has replaced the installed application.** The existing desktop shortcut still targets `release-upscale-candidate-20260928-01/win-unpacked/Hafez Studio.exe`.
- Native insertion and read-only control inspection succeeded. Visual QA of this five-card batch is **pending**: Windows capture returned black frames and activation failed twice with `GetCursorPos failed: Access is denied (0x80070005)`. UI input was stopped and the user was asked to check the unlocked desktop. No Windows security setting was changed.
- The previously verified single-cue preview remains available under `proof/editorial-source-bound-20260928-03/`; it is not a preview of the whole new batch.

## Next safe steps

1. After desktop access is available, visually review the first and late cards, two-line layout, subtitle overlap and entrance/exit timing in the saved new project. Save only this review project; do not export the final film.
2. Validate a fresh job through the packaged candidate and installed-root dependencies. Copy the required local v3 AEP/v4 MOGRT prerequisites with hashes; these licensed/local assets are not redistributed in Git.
3. Back up and update **the same shortcut-targeted installation**, not another app copy. Preserve runtime/model/Upscale resources. Until then, do not announce that the installed editing button uses Editorial.
4. Add separately tested numbered-problem/list/comparison/chart/CTA modules. Five title cards are one usable module, not all promised editorial roles or a final publication-ready edit. Text/ASR review remains necessary.

Known limitations retained: approximately six-second card duration only; primary-camera portrait binding, not automatic subject-aware reframing of arbitrary footage; AE and original template dependencies required locally; full source hashing is deliberately strict and may be expensive. This turn did not retrain/re-run transcription or approve all title choices.

Preservation: `backups/editorial-pipeline-20260928-01/` contains pre-change source files. Empty failed encoding attempt is retained as `editorial-failed-encoding-01/`. Original projects and unrelated dirty module work are untouched. No Trading/Hermes service/database/credential/Upscale changes. Source commit remains local; remote push needs the unresolved explicit permission before retrying.

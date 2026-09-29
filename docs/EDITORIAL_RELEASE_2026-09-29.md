# Editorial Glass staged release — 2026-09-29

Status: **activated in the existing desktop-shortcut installation**. This is a usable title-card increment, not a complete/publication-approved editing system.

## Evidence

- Reopened `proof/automatic-semantic-glass-20260923-05/frozen-package/editorial/Hafez-FX-Editorial-Review.prproj` in Premiere. Native MOGRTs survive reopen; no relink prompt. Visually inspected the first card at 00:00:09:15 and the two-line late card at 00:07:13:15. Current-media portrait, sage gradient, HAFEZ-FX, title/subtitle separation were present. This was not a full playback or listening approval.
- The apparently calligraphic title shape matches the original module `layout-v3.png`. Existing AE diagnostics explicitly report ABAR High FaNum with `fontObject.isSubstitute=false`; font-file PostScript metadata and the Windows installed-family enumeration match. No font installation or substitution was performed this turn. The Latin brand is also bound to ABAR by the current compiler.
- Reopening produced a **Poppins-SemiBold missing-font warning**, associated with the retained vendor-template dependency. Dismissed only; eliminating that warning remains unverified. Do not advertise a warning-free font preflight.
- Ran the packaged staged executable from the actual installed resources against a new, path/hash-rebound copy of the complete reviewed assembly. It compiled all five cards in AE and independently validated seven planned MOGRT layers, 142 captions, 26 camera shots, 11 punch-ins, six SFX cues, zero PNG-title assets. No final movie export. Fresh run: `proof/editorial-release-smoke-20260929-01/smoke.edit.editorial.json`.
- This fresh release smoke test **did not dispatch another Premiere project**. Native insertion is evidenced by the existing saved review and its prior seven-instance receipt; this turn verified reopening and actual render frames.
- 13 Editorial Python unittest tests, 74 Glass Python unittest tests, and desktop/bridge/finisher/panel JavaScript suites passed. `pytest` was not installed; the repository uses unittest and no dependency was installed for it.

## Installed target and rollback

The existing desktop shortcut still targets:

`release-upscale-candidate-20260928-01/win-unpacked/Hafez Studio.exe`

Activated candidate engine 02 and the shell that adds `--editorial-glass` only to Glass jobs. Added the verified local v3 AEP/v4 MOGRT authoring prerequisites. **No second shortcut or application copy** was created. UI/Upscale code and runtime/model assets were preserved.

Backup: `backups/editorial-release-20260929-01/` contains the previous shell, unpacked assets and engine, plus `activation.json`. The previous active engine directory is retained as `active-engine-before-switch`. Nothing was deleted. Rollback requires Hafez jobs/app to be closed and restoration from this backup; do not mix engine generations.

`scripts/verify_editorial_release.cjs` passed: installed shell hash, actual routing flag, unchanged UI/Upscale files, and all **1,892 candidate engine files** match.

## Handoff

Follow `EDITORIAL_QUICKSTART_FA.md`: open the Premiere Finisher panel, save existing projects, choose **Motion Design → Glass · Native Review**, then run Director with the next two cameras. Other style profiles do not enable Editorial. The engine refuses unrelated dirty AE projects rather than closing them.

Remaining: source transcript/copy review; full playback/listening; subject-aware reframing beyond the primary-camera insert; numbered-list/comparison/chart/CTA families; removal of the retained Poppins warning. This increment does not make every library family automatic or guarantee a publication-ready edit. Upscale remains independent and was not worked on.

Source remains on `codex/editorial-source-binding`. Remote push remains deferred because the earlier security-review rejection was not explicitly resolved. Unrelated dirty module assets were preserved and not committed in this increment.

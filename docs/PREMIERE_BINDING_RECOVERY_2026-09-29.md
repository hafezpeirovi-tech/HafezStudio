# Premiere multi-project recovery — 2026-09-29

## Incident

The C3026/C2996 latest job compiled six Editorial cards but native handoff
returned `XML IMPORT FAILED: Active project does not match the explicitly
requested QA project`. It placed zero MOGRTs and did not save the review.
The ready XML, SRT, plan and compiled templates were preserved.

## Correction

The isolated Glass finisher now finds the newly created project in
`app.projects` by exact normalized path and retains its native `documentID`.
XML import, MOGRT application, caption creation and save use that project
object instead of re-reading the focus-dependent `app.project`. At stage
boundaries and each graphic, the bound document must still exist with the
same ID and unique path. Missing, closed, replaced or ambiguous projects fail
closed. Manual/unbound requests still require the active project to match.
No existing project is closed, saved or overwritten; no movie is exported.

Adobe's PProPanel sample uses `app.projects`, project paths and `documentID`:
https://github.com/Adobe-CEP/Samples/blob/master/PProPanel/jsx/PPRO/Premiere.jsx

## Deployment and rollback

Updated only `jsx/hafez.jsx` and `jsx/glass-review.jsx` in installed CEP and
the same desktop application's `resources/premiere-cep-plugin`.
SHA-256 matches were checked. Backup:
`backups/premiere-target-binding-20260929-01` (source and deployed copies).
Engine, UI, Upscale and runtime queue implementation were not changed.

## Real result

Recovery folder: `proof/editorial-recovery-20260929-01`.
Project: `ME-YOUTUBE-10-Motion-Review.prproj`.
Original failed dispatch is retained, not resent. `prepare_native_recovery.cjs`
validated original artifact and MOGRT hashes and created a new destination.
No transcription, AI selection or AE compilation rerun was required.

Native receipt request `7ee7c6cf-35ec-48c6-91b3-5e324ab3a21f` confirms:

- 8/8 editable MOGRT layers, 0 failures/disabled items/safety failures.
- Two intro layers and six Editorial cards; text controls read back with ABAR.
- Captions created, source camera/dialogue tracks unchanged, 7 SFX synced.
- Separate review saved; `publication_ready=false`.
- Independent exact-project inspection confirmed all 8 MOGRTs.

Tests passed: `glass_project_binding_test.cjs`, `glass_finisher_test.cjs`,
`glass_bridge_test.cjs`, `glass_panel_test.cjs`, `glass_desktop_test.cjs`.
New regression covers actual XML importer with another project focused,
full bound lifecycle, closed/replaced/duplicate targets and owner isolation.

## Remaining review

This is a recovered editable review, not a claim of publication quality.
The old vendor intro reports a missing Poppins-SemiBold dependency even though
exposed text controls read back as ABAR. No font was installed in this repair.
Automatic wording and visual composition still require the owner's review.
This repair does not introduce additional template families or reselect titles.

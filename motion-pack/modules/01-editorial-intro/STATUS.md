# Module 01 — Editorial Glass Intro

## Current checkpoint — resumed 2026-09-28, v4 native test passed

The PAUSED section below is historical, not the current status.

- Latest usable template: `Hafez-FX Editorial Intro v4.mogrt`.
- Editable AE source: `Hafez-FX-Editorial-Intro-v3.aep`; v4 additionally normalizes exported slider ranges and brand metadata using `finalize-template.ps1`.
- Native Premiere project saved: `Hafez-FX-Intro-Editable-Test.prproj`, sequence `Hafez-FX Intro - Native QA`.
- Two v4 native graphics successfully inserted by the existing Hafez Finisher on V3. Native readback: 20 properties each, enabled, 0–6 and 6–12 seconds. No PNG title clips.
- Text, font family/weight, font size, accent color, line spacing and panel opacity changed by the plan and read back successfully. Both steady-state results visually inspected in Premiere at 00:02:01 and 00:08:02.
- V2 contains two DISABLED v3 failed-test graphics, retained only as QA history. Use V3 clips or the v4 MOGRT, not V2 or older versions.
- Evidence: `native-apply-receipt-v4.json` and `native-inspect-v4.json`.
- Fixes: RTL right-edge anchors; auto-fit maximum text width; last-word accent instead of whole-line glow; full-frame ambient blurs; exported spacing slider range 80–220 instead of incorrect 0–100; title scale 50–140; portrait zoom 100–160; default HAFEZ-FX metadata.
- Font diagnosis: ABAR was installed and not substituted. The earlier suspected font-resolution problem was not confirmed; the original major error was RTL bounds/layout.
- Media replacement is exposed but replacing it with another source in Premiere has NOT yet been verified. Other background colors are exposed and ambient colors linked in AE; not all 20 controls have received individual visual tests.
- Automatic insertion with an explicit plan is verified. Semantic selection and automatic production routing to this new module are NOT connected yet. Music/SFX and remaining graphic roles are not complete. No full editing-app readiness claim.
- Production code, installed extension code, app release, vendor originals, existing user projects and Upscale were not modified. Only the extension's normal local request/receipt queue was used for the isolated test.

Scope approved 2026-09-28: implement the approved split-portrait intro as an independent editable delivery before expanding other graphic roles.

## Delivery gates

- [x] Approved visual reference: proof/editorial-glass-styleframes-20260928/sample-01.png
- [x] Native AE source with supplied Qss background and 20 exposed controls
- [x] Exported v4 MOGRT, not a flattened PNG/video title; two steady layouts passed Premiere visual QA
- [x] Isolated Premiere demonstration project saved
- [x] Text / font / color live-edit verification and native AE motion preview
- [x] Standalone template and Persian usage instructions
- [ ] Optional integration into automatic routing (after native visual acceptance)

No production engine, UI, Upscale, vendor original or existing Premiere project changed. All new work is isolated in this module folder. Existing materials are referenced/copied; their originals remain the rollback point. The standalone title is usable; the full automatic production workflow is not declared complete.

Latest preview: `Hafez-FX-Intro-Preview.mp4`, six seconds, silent, native AE render after final background bindings. Full ffmpeg decode passed. Preview still: `Hafez-FX-Intro-Preview.png`. `Test-Module.ps1` passed 17 artifact/recorded-native-evidence checks (not a full app suite or new Premiere run).

Implementation sequence: inspect exact template controls; assemble the approved layout with live video and editable typography; export with a versioned name; import into a separate Premiere test sequence; change text and color and confirm visually; publish only this finished module. Do not activate unfinished downstream modules.

## PAUSED at user request — 2026-09-28

Resume only when the user says the system is available. No background processing is intended.

Saved native source: `Hafez-Editorial-Intro-v1.aep`. Export: `Hafez Editorial Intro v1.mogrt`.
Channel label updated to `HAFEZ-FX` in the source, builder, and latest MOGRT; app name is unchanged.
`before-channel-brand.aep` / `.mogrt` preserve the previous version.

Actual six-second AE render `native-preview.mp4` and frame `layout-check.png` were inspected. This render predates the channel rename. It FAILED visual QA: Persian text extends rightwards onto the portrait instead of staying in the left column; subtitle and pill text overflow; the rendered typeface does not match the approved ABAR appearance. Do not deliver it as a finished design.

Latest brand script successfully saved/exported, then failed when disabling a DONE render queue item. No new branded preview was rendered. On resume, skip DONE/STOPPED queue items rather than assigning their render flag.

Next bounded milestone:
1. Diagnose actual installed ABAR PostScript names/font resolution; correct RTL anchor/bounds using sourceRectAtTime so text stays left of portrait, including after user edits.
2. Match proof/editorial-glass-styleframes-20260928/sample-01.png; fix accent color and spacing; retain editable text.
3. Render and inspect native motion and steady frames before Premiere testing.
4. Reapply scripts/enable_mogrt_font_controls.py to the latest export (the brand re-export superseded the earlier patched MOGRT). Verify actual text/font/size/color controls in an isolated Premiere project.
5. Publish only this module with instructions and evidence. Automatic routing, music/SFX, and the remaining graphic modules are NOT complete. Upscale remains on hold.

No existing Premiere project, production engine, vendor original, Trading, database, credentials, or security files changed.

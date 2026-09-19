# Body tracking / native placement — 2026-09-09

## Latest checkpoint — preview crash fixed, installed-app recovery passed

This section supersedes the candidate-02 deployment details below. The native
saved Premiere delivery is unchanged and remains usable for review (not publish).

- The first visible app Start test, `HS-MTU5X9HW`, performed fresh ASR and four
  fresh local AI tasks, then FAILED at 76% with Pillow `y1 must be >= y0`.
  The optional preview renderer was attempting a 20px-high rejected placement.
  Failure log and exact isolated reproduction were preserved in
  `proof/body-safe-delivery-20260909-01` before fixing it.
- After backup and fresh boot-bound HERMES_CONFIG_WRITE authorization, only the
  optional preview path in `professional_edit.py` was changed: preserve blocked
  editable metadata but skip its PNG; reject invalid/tiny/nonfinite geometry.
  Native text/placement safety gates were not relaxed. Three new test methods
  include 13 invalid-geometry subcases; all **313 Python tests passed**.
- Frozen `preview-geometry-engine-20260909-03` replayed the failed manifest and
  four cached decisions successfully. The first sandbox replay reached 94% but
  could not write app-local curator history; a normal authorized replay in a
  NEW evidence directory completed. This was a sandbox permission failure,
  not evidence of another unresolved installed-app crash.
- Full original-video finalization, reusing the saved transcript and ten AI
  decisions, completed at 100%. `preview-geometry-candidate-20260909-03/finalize`
  passed the same 95-frame offline preflight. Its eligible MOGRT contract and
  complete XML are identical to native-reviewed candidate 02 except for output
  folder paths. No new native import or replacement of the saved project needed.
- Candidate 03 was deployed to BOTH runtime locations; all 1891 files per tree
  were hash-verified. Previous candidate-02 trees and pre-patch source are in
  `backups/preview-geometry-20260909-03` with `RESTORE.md`.
  Current EXE SHA256: `84e140c3c84c708fc115329cb772a7c41a7aa299ccf9c1de9628a2be693a9b8d`.
  UI app.asar remains unchanged.
- Native installed-app Start was tested again with the same two excerpts.
  Job `HS-MTU6YWL6` RECOVERED the prior failed job in its original output folder
  using the saved ASR/four AI checkpoints. It reached 100% in the UI and emitted
  `completed` at 2026-09-09T14:26:34.225Z. This is native app recovery evidence,
  NOT a second fresh-ASR job. Result: three XML sequences, three draft captions,
  one punch-in, zero active graphics, one blocked proposal, zero PNG clips.
  `installed-app-recovery-03.log` preserves the full evidence.
- Premiere is parked at 00;00;24;00 for the user's MOGRT inspection. Native
  readback exposes font editing but the visual font appearance has NOT been
  certified against ABAR (fallback/substitution still needs an explicit check).

No automatic MP4 export. Read `proof/body-safe-delivery-20260909-01/README-FA.md`.
Remaining: Persian source-audio/text review, five blocked full-video proposals,
Subscribe artwork, calibrated camera transforms, native font/style audit and
complete user review before publishing. Do not claim unattended final editing.

## Earlier checkpoint — native review saved and candidate 02 deployed

This section supersedes all blocked/paused checkpoints below. After the user
brought Premiere to the foreground, native Computer Use succeeded. A NEW project
was created and saved as `proof/body-safe-delivery-20260909-01/Hafez-Body-Safe-Review-20260909.prproj`.
Bear Outro and the September 8 review project were not modified.

- The existing guarded CEP connector imported all three candidate-02 XML sequences
  into an isolated bin; the verified new Director sequence ID is
  `bfd74725-0c3b-46bf-a730-3a59c4bd0398`.
- Finisher imported one real Review 8 MOGRT, updated its text, reported zero
  safety failures and retained five editorial/spatially blocked proposals.
  `ok=false, failed=5` is a PARTIAL result, not a fully successful edit.
- Native inspection confirmed 21 controls, font/size edit flags, both text
  strings, sizes 59/97, leading 65/100, normalized layout position
  `[0.5,0.16046296296296]`, scale 56.4 and expected colors. V3 has zero clips;
  V4 has exactly one enabled native MOGRT from 22.8228 to 25.9926333333333.
- Program Monitor at 00;00;22;26, 00;00;24;00 and 00;00;25;26 showed distinct
  entry/hold/outro states. The card stayed above the visible head and hands at
  these samples and text was readable in the hold frame. This is visual sampling
  plus every-frame source-body evidence, NOT a rendered all-frame pixel audit,
  font-substitution proof, or verification of every possible control value.
- Saved native project: 406145 bytes, initial saved SHA256
  `a50b485405a263d7644f4980ebb54d76d98e580a8d99c079e3d68470fc6eee6a`.
  No MP4/export/render was started. Keep its Motion Graphics Template Media folder.
- After fresh HERMES_CONFIG_WRITE authorization and process/source checks,
  candidate `body-tracking-engine-20260909-02` was deployed to BOTH runtime
  locations; every one of 1891 files matched the candidate by hash.
  Previous engines are retained at `backups/native-placement-20260909-02/installed-engine-before`
  and `packaging-engine-before`; no engine files were deleted.
- Installed EXE SHA256: `a5205f2f6831091fd4a3bc058fe4789956d255f617f60bf258c39576ff436be1`.
  UI app.asar unchanged: `0a1f3d2e18933018d6091ca4ae5c7890eab84440c95384e1a0470678284da874`.
- Native slider check on the installed app: 0% empty/left, 50% half-full,
  100% full/right; restored 80%. This supersedes the earlier unavailable
  Electron slider harness as a visual endpoint smoke test only.
- A fresh installed-app run was started through the visible Start button with
  the two existing 12.012-second excerpts, job `HS-MTU5X9HW`; it failed at 76%.
  The latest checkpoint above records its fix and successful native recovery.

Evidence: `proof/body-safe-delivery-20260909-01/{import,apply,inspect}-result.json`
and `deployment.log`. Publication readiness remains FALSE. Persian ASR/copy,
five blocked proposals, Subscribe artwork and calibrated zoom tracking remain.

## Historical checkpoints (superseded by current section)

## Later resume — offline acceptance completed; native UI blocked

User returned permission to use the PC. The updated Computer Use skill was read.
Fresh boot-bound SENSITIVE_READ authorization passed. Premiere was now on its
Home screen, not Bear Outro. Activation failed with
`failed to activate captured window`, including one retry after re-enumeration.
Read-only state returned a Premiere accessibility tree but images of another app;
no further UI input was sent. An asynchronous request asks the user to bring
Premiere to the foreground and say it is open. No native project was created,
no Finisher request sent, no engine deployed, no video exported.

Additional completed evidence:

- Candidate `doctor --json` with HERMES_STUDIO_ROOT set to the installed resources
  reported the body/face models inside the candidate's `_internal/models`, local
  Persian model present, FFmpeg/FFprobe and Adobe present. CUDA ASR runtime is
  unavailable; explicit CPU fallback remains in effect.
- `proof/test-body-candidate-fresh-20260909.ps1` ran a NEW two-camera 12.012-second
  excerpt job using installed runtime resources, fresh local ASR and FOUR fresh
  local Qwen tasks. No saved AI checkpoint reused. Job HS-BODY-FRESH-20260909
  reached 100%, exit 0 in **72.1 seconds**. Evidence:
  `proof/body-candidate-fresh-20260909-01/fresh-run.log`.
  Result: 39 words, 3 draft captions, 1 punch-in, 0 active graphics, 1 blocked
  proposal and 0 PNG stand-ins. This is engine CLI proof, not an app UI test.
- `proof/verify-body-candidate-20260909.ps1` independently checks the actual XML:
  all **95 snapped MOGRT timeline frames** map to one visible CAM2 source frame
  each, have decoded face/body observations from the approved model and contain
  NO Basic Motion filters. The conservative 96-source-frame tracking interval
  contains these 95 frames. Plate/halo is title-safe and outside protected union;
  apparent Title/Body sizes satisfy 28/30px minima; actual XML SFX begins at frame
  684. Camera 1 voice has no filters, camera 2 audio disabled, no orphan SFX/PNG.
  `proof/body-tracking-candidate-20260909-02/finalize/offline-preflight.json` records
  hashes and exact frame mappings. Status explicitly remains native-review-pending.
- Mock-based Finisher controls, guarded native import, job recovery and packaged
  curated-SFX regression suites passed; Electron main/preload/renderer syntax
  checks passed. Evidence: `proof/body-safe-delivery-20260909-01/javascript-checks.log`.
  These are not substitutes for native visual/control readback. The adaptive
  slider Electron harness was initially invoked with Node and failed to launch
  (Electron app object absent); it was NOT rerun via a desktop-input workaround.
  No new slider visual test is claimed.

Next action still requires a targetable native Premiere window. Do not promote
the candidate or call it finalized solely because offline tests pass.

## Current checkpoint

User requested pausing until evening because they need the PC. No further UI
input is authorized until they say they are ready. No automatic export is wanted.
No background build/finalizer remains running: both finished with exit 0.

**NOT DEPLOYED; NOT NATIVE-VALIDATED YET.** The installed September 8 engine and
the prior saved Premiere delivery were not replaced. No automatic render started.

## Implementation and evidence

- Approved official local OpenCV Zoo PPHumanSeg model: 6,163,938 bytes, SHA256
  `552d8a984054e59b5d773d24b9b12022b22046ceb2bbc4c9aaeaceb36a9ddf24`.
  Weights, license and provenance are under `engine/models`. Runtime verifies
  the hash and has no model download path.
- Every requested visible source frame is decoded/inferred. All segmented
  person components and all detected faces participate in interval unions.
  Missing reads/body detections fail closed. A 6% normalized margin guards
  coarse segmentation; it does NOT guarantee perfect hand coverage.
- Diagnostic real CAM2 frames 2711..2806: 96/96 decoded/body/face observations.
  `proof/body-tracking-20260909-02/real-body-evidence.json` and its contact sheet.
  Inspection showed some individual hand pixels missed; margin expanded bounds.
- Generic layout had treated top-left/right only as side strips and omitted the
  usable top band for short statements. Review 8 now fits its actual 720x380
  plate plus 24px halo in available bands. Existing generic safety constants
  remain unchanged. Actual text measurement and minimum apparent sizes gate fit.
- Uncalibrated camera FCPCurve overlaps, including up to six external ramp
  frames, block graphics; raw-source boxes must not claim transformed safety.
  This is a conservative gate, NOT calibrated per-frame transform support.
- Failure messages distinguish body coverage, placement and camera transform
  causes instead of overwriting all failures with a body-tracking error.
- 310 tests passed: `proof/native-placement-tests-20260909-02.log`.

## Candidate

Frozen executable: `proof/body-tracking-engine-20260909-02/dist/hermes-engine`.
Source snapshot is the adjacent `source` directory. Build completed exit 0.

Full finalization: `proof/body-tracking-candidate-20260909-02/finalize`.
Base filename: `F_Hafez_Youtube_8rdvid_C2963`.
The exact two full original videos were used, deliberately REUSING the saved
transcript and ten saved local review decisions (not fresh ASR/editorial QA).
Completed exit 0: 157 draft captions, 1,353 words, 31 shots, 30 camera switches,
13 punch-ins, ONE eligible editable MOGRT, FIVE blocked proposals, ZERO PNG
timeline assets. `publicationReady=false`. Candidate 01 had incorrectly blocked
all six; candidate 02 restores the eligible term card without waiving safety.

## Native UI checkpoint — important

Premiere was open on the user's **Bear Outro.prproj**, with unsaved changes.
Do not overwrite, close/discard or modify this unrelated sequence.
Ctrl+Alt+N opened the **New Project** dialog. A subsequent set_value on stale
UIA index 63 failed before changing the field. The dialog was last observed with
name **Untitled** and location pointing to the old proof folder. User was told
they can cancel it. Do not assume this state survives; re-enumerate and observe.
No new Premiere project was created, imported, saved or exported this turn.

Empty intended delivery folder exists: `proof/body-safe-delivery-20260909-01`.
Proposed filename: `Hafez-Body-Safe-Review-20260909.prproj`.
No import/apply requests were sent. Existing CEP protocol supports guarded
`import_xml`, `apply`, `inspect`; inspect installed panel before using it.

## Backups / next steps

- Pre-body code/tests: `backups/body-tracking-20260909-01` (RESTORE.md).
- Pre-placement code/tests: `backups/native-placement-20260909-02`.
- Neither backup contains moved runtime engines yet: deployment has not happened.

After user resumes: inspect candidate 02 eligible card geometry/controls; create
a separate native project without altering Bear Outro; import candidate 02 XML,
apply its actual plan, inspect native control readback and entry/hold/outro
placement. Save the editable project (no MP4 export). Only then consider promoting
candidate 02 with the parameterized proof deployment script after local guard,
process and frozen-source checks. Preserve old engines in the backup target.

Remaining: native validation, deployment/app smoke test, calibrated camera zoom
tracking, other template footprints/Subscribe, and Persian ASR/copy accuracy.
Do not describe this as complete unattended publication-ready editing.
Trading, MetaTrader, DB, credentials and original Hermes were not modified.

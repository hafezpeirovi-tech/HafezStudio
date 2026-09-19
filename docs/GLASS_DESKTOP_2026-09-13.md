# Glass desktop/native acceptance — 2026-09-13

This is the newest Glass checkpoint. It supersedes the **current project** pointers in
GLASS_FINALIZE, GLASS_TIMELINE and GLASS_HANDOFF; those files retain historical evidence.
No final movie export/publication. Fonts remain provisional by explicit owner request.

## One current native review

- Project: `proof/glass-finalize-20260913-03/F_Hafez_Youtube_8rdvid_C2963.glass-review/Hafez-Glass-Review.prproj`
- Only sequence in that project: `Hafez Glass — Automatic Timeline Review`.
- Native sequence ID: `72434aa6-bca4-406e-a937-4bde9f667a23`.
- Duration: 16643 frames, 30000/1001 fps, approximately 9m15s.
- Keep its accompanying media folders; older projects remain untouched and are NOT alternative finals.

## Real, not simulated

`scripts/verify_glass_desktop.cjs` dispatched the same broker used by Electron against the
existing real engine completion in `glass-finalize-20260913-03/finalize.log`. A fresh CEP
panel loaded the new handler and Premiere created an independent project, imported the XML,
bound its exact sequence ID, inserted both actual vendor MOGRT layers, created the native
caption track from SRT, and saved the project. No manual XML import, MOGRT insertion, SFX
placement or caption import was needed for this acceptance run.

Receipt: `native-receipt.json`, request `9ceb7fbf-f076-432c-bab8-089bac535419`.
Two MOGRTs / twelve typed bindings verified; no failed, disabled or safety-failed graphics.
This test reused existing ASR/review evidence. It is NOT a new raw-camera/ASR/AI run and
does NOT certify semantic chapter selection. Current complete-video review contains one
neutral fullscreen intro, not content titles/infographics throughout the speech.

`saved-native-verification.json` independently checked the saved binary project against XML/SRT:

- 152 source clips each on V1, V2, A1, A2: exact timeline/source in/out at every cut.
- One six-second MOGRT each on V3/V4; one vendor SFX on A4 exactly frames 0–180.
- A3/A5 empty. Native host checked A1 audible/A2 muted and preserved source clips during finishing.
- All 157 caption strings are exactly the SRT text (including deduplicated BinaryHash references).
  Native display quantization is less than one video frame; imported source cue clocks are exact.
- Zero PNG timeline graphics. No music yet; no music ducking claimed or exercised.
- Saved SHA after the limited visual fix: `a620acc3119d2b13d462601a0dc9ed2a8f2b71989b57dd60b682e77f33f2b08e`.

## Visual QA / manual part clearly separated

Premiere showed missing Poppins-SemiBold. Acknowledged without installation or global font changes.
Typography remains temporary ArialMT/Tahoma, not the final Glass font choice.
The middle Persian intro frame rendered correctly but its glow was banded with the new sequence's
default **Composite in Linear Color** checked. After backing up this newly generated project,
unchecked that option in its Sequence Settings via native UI and saved. Glow visibly softened.
No source/video/audio edit was made by hand. The finisher still reports
`compositing_review_required=true`; it cannot claim this native setting is automatic.
No complete playback/listening/editorial approval or final movie export occurred.

## Source changes

- `electron/glass-finisher.js`: fresh versioned CEP heartbeat, exact paths/hashes, new-project-only,
  exclusive durable dispatch, matching request receipts, no replay of uncertain mutations.
- `electron/main.js`: Glass opt-in, preflight before ASR, wait for native save before completed;
  source engine progress capped at 88%, native phase reported separately; errors not success.
- `electron/job-recovery.js`: recovery requires matching style; no legacy-job reuse for Glass.
- Existing Motion Design Glass card now chooses `glass`; no layout or Adaptive redesign.
- `premiere-cep-plugin/panel.js`: heartbeat and one-shot `finish_glass` consumer.
- `jsx/glass-review.jsx`: independent project/import/sequence bind/typed MOGRT/captions/save.
  Never closes/saves/deletes an old project and never exports a movie.
- Installed existing CEP panel/JSX updated and reloaded for native test.
- `scripts/verify_glass_desktop.cjs ... collect` only collects a prior matching receipt;
  never dispatch the same job twice. Interrupted jobs require inspection, not automatic replay.

## Tests / backups

- 389 Python tests passed this turn.
- `glass_desktop_test.cjs`: actual main.js orchestration with isolated mocks, not native proof.
  Tests opt-in, preflight, flag/recovery, native await, truthful failure, cancel guard and legacy path.
- `glass_finisher_test.cjs`, `glass_bridge_test.cjs`, `proof/test-job-recovery.js` passed.
- Syntax checks of main/renderer/panel passed.
- `backups/glass-desktop-finisher-20260913-01` contains pre-edit sources, exact installed CEP
  backup and `Hafez-Glass-Review-before-visual-QA.prproj`. No original assets deleted.

## Still required

1. Fresh end-to-end two-camera app run with new ASR/review evidence; diagnose source-text errors.
2. Source-grounded important chapters and appropriate title/infographic routing; do not manufacture
   text or relax confidence/boundary gates merely to fill the video with graphics.
3. Full native visual/audio QA; automate the compositing requirement only with a verified interface.
4. Curated local music and Glass subscribe selection remain absent; no Grunge substitution.
5. Full-interval footprint/face/body union checks for Glass overlays, not certified by fullscreen intro.
6. Final Persian/English font choice at the end, native rendering check, then owner publication review.

Candidate build status is recorded below only after verification. Original installed release and
desktop shortcut are not switched by this work.

## Independently packaged candidate — verified

- Executable: `release-glass-candidate-20260913-01/win-unpacked/Hafez Studio.exe`.
- Fresh frozen Python engine, local Electron distribution; no asset downloads or installer run.
- `scripts/verify_glass_candidate.cjs` checked all 11 `app/` + `electron/` files against ASAR,
  the fresh engine binary, CEP source, all 114 MOGRT hashes across seven packages and chapter SFX.
- No CEP `runtime` directory/queue is shipped. Clean-install panel boot creates its runtime directory;
  `glass_panel_test.cjs` verifies success and fail-closed behavior. The final panel patch was also
  copied into the candidate resource after build and its source hash was checked.
- The actual packaged engine ran `doctor --json`, `glass-status`, and `glass-validate --qa` on an
  isolated plan whose template paths were rebound to the candidate's resources. All exited zero.
- Evidence: `proof/glass-candidate-20260913-02/candidate-verification.json` and command stdout/stderr.
  `glass-candidate-20260913-01` is an empty failed-verifier attempt, not another Premiere project.
  That verifier initially used forward-slash nested paths unsupported by ASAR 3.x on Windows;
  the app's fonts/logos were present all along. Native-separator verification passed without rebuild.
- CPU ASR fallback is active: model is present, one CUDA device detected, CUDA runtime not ready.
  Doctor does not establish fresh transcription speed or accuracy. No new ASR was run here.
- Native UI smoke test launched the exact candidate executable, verified logo/UI font/Director,
  opened Motion Design, selected **Glass · Native Review**, and returned to Director.
  No cameras selected/job started/config saved during this smoke test. Original shortcut unchanged.
  The current in-memory candidate selection is Glass; on a later launch select the Glass card before
  starting. Keep Premiere and the Hafez Premiere Finisher panel open for its live preflight.
- The existing HTML Motion Design animation is a schematic preview, NOT the actual vendor MOGRT
  render. Use the native Premiere review for visual judgment; do not treat its generic prose or
  preview controls as certification of identical vendor behavior. Clarifying this UI copy remains.

The candidate is a working **review-mode build**, not a certified full editorial release.
Latest JavaScript regression run passed desktop orchestration, finisher safety, typed bridge,
clean CEP boot, and job recovery. The 389 Python tests above passed earlier in this same work.
The next acceptance task is a fresh raw-camera run plus source-grounded editorial content routing,
not another rebuild of this already-verified intro/bridge.

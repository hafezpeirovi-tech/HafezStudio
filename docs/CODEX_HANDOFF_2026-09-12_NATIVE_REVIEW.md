# Hafez Studio — native review checkpoint, 2026-09-12

This checkpoint continues `CODEX_HANDOFF_2026-09-09_FINAL_EDITORIAL.md`; do not redo its completed source/tests/build work. Scope remains Hafez Studio only. No automatic movie export. No original AE project changes. All editorial/placement gates remain enforced.

## Latest continuation — exact spoken trigger, deployed 2026-09-12

This section supersedes the earlier installed-engine version below; the native Premiere project itself is unchanged.

- Added pure `engine/src/hermes_video/spoken_trigger.py`. Subscribe timing now requires literal adjacent, content-bound source words owned by a retained segment and mapped through the FINAL A1 integer-frame keeps. It does not use prepare clocks or sentence starts as valid word onsets. A later complete occurrence can replace an incomplete first one.
- Rejects partial/uncertain words, removed source gaps, retiming, wrong clocks, duplicate ownership, omitted intervening source words, missing provenance, and insufficient tail room for the full authored animation. It never changes cuts, awards listening verification, approves a native template, or clears existing copy/placement failures.
- `professional_edit.py` carries the detailed `trigger_timing` report and blocks missing valid timing. `autocut.py` supplies context from the existing media-hash-verified caption producer and final tight A1 mapping used by Director.
- Real project result: both exact pairs in segments 80/81 remain `partial-or-uncertain-trigger-word`; `selected:null`, `audio_verified:false`. Proposal start 521.507s remains a disabled draft coordinate, NOT a verified spoken onset. Canonical native Subscribe failure also remains enforced.
- Updated generated edit-notes: six proposals are distinguished from two eligible requests and four blocked proposals; the table shows actual control text and blocking status. Removed obsolete PNG-guide / separate English-Persian video-track wording. This report is explicitly not a native insertion receipt.
- Backups before edits: `backups/spoken-trigger-20260912-02/` (three original source/test files plus original handoff/review-guide copies). New source/tests were initially absent. No trading files touched.
- Final full suite: **333 passed**, `proof/subscribe-source-review-20260912-02/python-tests-final.log`. Twelve exact-trigger tests plus the new edit-notes regression test; initial 332-test log is superseded.
- Final frozen candidate: `proof/spoken-trigger-engine-20260912-03`. Build and full packaged replay passed: `proof/final-editorial-spoken-trigger-20260912-03/finalize/candidate-run.log` completed at 100%. Uses existing ASR and ten validated local checkpoints; NOT fresh ASR from raw files.
- Independent `final-editorial-offline-preflight-v2.json` in that finalize folder passed: 16463 Director frames, 198 actually visible graphic frames, two eligible/four blocked, no PNG clips, exact entry SFX, unchanged source-frame maps for A1/A2, unprocessed A1 and disabled A2. Native visual status in this new replay remains pending: no new native import was performed.
- Deployed the final candidate to both `release/win-unpacked/resources/engine/hermes-engine` and `engine/dist/hermes-engine`; all **1891 files per copy hash-verified**. Both prior engines retained recoverably in `backups/spoken-trigger-deploy-20260912-03/{installed-engine-before,packaging-engine-before}`. Nothing deleted. Evidence: `proof/subscribe-source-review-20260912-02/deployment.log`.
- Current engine EXE SHA256: `91c07f91070ebbe9761b93f52019df1b5a198555c909e1e54f14a6d841deaadc`. UI ASAR unchanged (`0a1f3d2e18933018d6091ca4ae5c7890eab84440c95384e1a0470678284da874`); no catalog or MOGRT changes this continuation.
- Installed doctor passed with normal user access: `proof/subscribe-source-review-20260912-02/installed-doctor.json`. AE/Premiere, ffmpeg/ffprobe, local models and eleven fonts available; ASR runtime imports, CUDA runtime still false. Do not claim GPU ASR ready.
- Hafez was closed normally while idle before deployment, then launched through the computer-use skill. Director displayed Engine/ASR ready, AE/Premiere ready, correctly aligned Glow 80%, idle 0/2 sources. This is launch smoke, not a fresh two-camera app run.
- Native review remains the already saved `proof/final-native-20260912-01/Hafez-Automatic-Review-20260912.prproj`, SHA256 `10d2934eb98c980dc925ec44979547a685ce1d938e0bd7c1d1142b8a0c017e0f`. No reimport, duplicate clips or extra graphics were added in this continuation.

### Listening comparison — prepared, not approved

- `proof/subscribe-source-review-20260912-02/LISTENING_REVIEW_FA.md` contains playable source and final-A1 samples, with relative phrase locations.
- `source-960-980.wav`: 20-second original-camera excerpt.
- `director-526-538-a1-review.wav`: exact verified-XML A1 map, frames 15764..16124, 525.992133..538.004133 seconds; ffprobe duration 12.012042 seconds (sample-rounding tolerance). Four retained pieces, no source edits or gain/EQ/dynamics effects. Both copies are 24kHz mono PCM16 for review, not final delivery audio.
- Creation script `create-listening-pair.ps1` verifies the prior successful replay XML hash, exact 29.97 clock, continuous coverage, literal source identity, no retiming or voice effects, and refuses output overwrite. `listening-pair.json` binds source-map and sample hash. Do not rerun the one-shot script.
- The samples were generated but NOT actually listened to or certified by the assistant. ASR review flags remain flags, not proof of audible clipping. No source restoration or manual approval was fabricated.
- Next actionable requirement: listen to both phrase boundaries, then assess actual approved word-aligned timing and all-frame geometry; a readable independently authored compact layout may still be necessary. All three other editorial review blocks and full subtitle/source listening remain unresolved. No final movie export.

## Delivered native review

- Project: `proof/final-native-20260912-01/Hafez-Automatic-Review-20260912.prproj`
- Sequence: `03 - Hafez Director Cut - Review 20260912`
- Native sequence ID: `23d65225-414a-436b-863d-218d13469e53`
- Imported the frozen successful packaged replay `proof/final-editorial-packaged-20260909-02/finalize`, with only three sequence names mechanically suffixed to prevent collisions. Media and duration unchanged.
- Matched native import/apply/inspect receipts exist in `proof/final-native-20260912-01/`. Do not resend completed requests.
- Apply: 2 attempted, 2 imported, 2 verified/text-updated, 0 safety failures. Four blocked cues were skipped; therefore aggregate `ok:false` is intentional, not a failed native import.
- Inspection: V1/V2 each 153 clips; V3 empty/muted; V4 two enabled actual MOGRT components, each 21 editable parameters. No PNG graphics added.
- `graphic-001`: ANALYSIS PARALYSIS / فلج تحلیلی, 22.8228–25.992633s.
- `graphic-002`: SMART TRADER / تریدر باهوش, 56.189467–59.626233s.
- Native Program monitor observed first title at 00;00;24;00 and second at 00;00;56;08 (entry), 00;00;58;00 (hold), 00;00;59;15 (exit fade). Both visible above head on CAM2, no clipping/subject overlap in observed samples. Full source-frame geometric proof remains in packaged preflight; screenshots are samples, not a substitute for all-frame tracking.
- Text/font/size/leading/color read back from native components; do not equate readback alone with comprehensive visual A/B testing. Prior font A/B evidence remains in September 9 proof.
- Saved via native Ctrl+S, verified title without asterisk and updated disk file at local 17:40:49. Size 702037 bytes; SHA256 `10d2934eb98c980dc925ec44979547a685ce1d938e0bd7c1d1142b8a0c017e0f`.
- Pre-import project retained at `backups/final-native-20260912-01/Hafez-Automatic-Review-before-import.prproj`; old baseline review also preserved.

## Deployment completed

- Candidate `proof/final-editorial-engine-20260909-01/dist/hermes-engine` deployed to both `release/win-unpacked/resources/engine/hermes-engine` and `engine/dist/hermes-engine`.
- Deployment checked all source files against frozen candidate and successful full replay; all 1891 files in each deployed copy hash-verified.
- Prior engines moved recoverably to `backups/final-editorial-deploy-20260912-01/{installed-engine-before,packaging-engine-before}`. Nothing deleted.
- Installed catalog backed up to same backup directory `editorial-element-catalog.before.json`; installed catalog now equals source SHA256 `33919b2b5ce63f4709e378fbb6eccbcb300a7cd7f5a5191291cc55204314138e`.
- Catalog synchronization script: `proof/final-native-20260912-01/sync-deployed-catalog.ps1`. One-shot; refuses repeats/drift.
- App ASAR/UI unchanged. No live Hafez/engine process during deployment.
- Post-deployment native app launch smoke passed: `release/win-unpacked/Hafez Studio.exe` opened on Director with Engine/ASR ready and AE/Premiere ready. Observed Glow 80% with correctly aligned left-to-right thumb/fill. No new editing job was launched by this smoke test.
- Installed `hermes-engine.exe doctor --json` passed with normal user access. The sandbox-only attempt could not read Adobe's existing MOGRT directory; the authorized normal-access retry passed without permission changes. Local Whisper, face/body models, ffmpeg/ffprobe, 11 fonts, and ASR runtime were available. CUDA device count 1 but `cudaRuntimeReady:false`: CPU fallback, NOT verified GPU ASR.
- Installed engine SHA256: `45d424e29684e393d365379af8de72d109efef8f8002220209c4f01a613e7bdf`.

## New native Subscribe Rim alpha proof — completed

- The exact frozen `Hafez Subscribe Compact Rim Review 2.aep` was opened through AE Recents and its full title verified. The correct script path was visually verified before Run Script File. Earlier incorrect filename text was never submitted.
- Ran `proof/subscribe-compact-native-20260905/capture_rim_alpha_all_20260909.jsx` once. Eight chunk receipts and 127 distinct native RGBA frames are complete in `rim-alpha-captures-20260909-01`.
- `node proof/final-editorial-20260909-01/verify-rim-alpha.js` passed. Exclusive `render-manifest.json` and `measurement.json` now exist. DO NOT rerun the one-shot capture/verifier or overwrite proof.
- Correct asset SHA256: `dc19dbff5de351022a3c0d6fc2ddeaec17553d758736b4e7de167a6a5b0f96a4`. New proof is bound to this actual Rim asset, not borrowed from old Compact.
- Alpha >= 1 all-frame union: x733 y374 width440 height347 at root HD, Layout Position 960/540, Scale100, Duration4.2, Show Background0. First visible frame2, last125, frame126 entirely transparent. Zero canvas-edge-contact frames. All 25 controls and anchors unchanged.
- AEP still SHA256 `9b2680d735a339d2fa01016c3c5d1293b18e7eef1dcd3c7a8529906e420cc4dc` after capture; no unsaved asterisk or execution modal. No candidate save, control mutation, render queue or final movie export.
- This is a valid alpha-envelope result, NOT full-video placement approval or automatic catalog promotion. Structural rim intensity/thickness remain distinct from soft glow.

## New offline Subscribe diagnostic — remains blocked for concrete reasons

- Added only `proof/final-native-20260912-01/assess-subscribe-placement.py`; engine/catalog/project were not changed by this diagnostic. Geometry self-tests passed. Matching exclusive `.json` records all-frame evidence.
- At the current segment-start cue (521.507s), decoded/detected face AND body in all 126 source frames on CAM1 and all 126 on CAM2, with the existing independent segmentation model and 6% protected union margin. No readable placement for the measured complete 440x347 alpha envelope within 5% title-safe. The smallest authored root text is 26 HD px; the diagnostic never shrinks below 24px. It does not prune faint alpha to force a fit.
- CAM1 protected union: `[0.205625,0.143125,0.755416667,0.856875]`; CAM2: `[0,0.307295668,0.856875,0.692704332]`. These are exact interval diagnostics, not permission to change cameras.
- Current cue is anchored to segment start, not spoken word start. Both exact adjacent `سابسکرایب کن` occurrences were examined using saved acoustic word evidence. One word in EACH pair is already marked partial-source-coverage/boundary-review-required. Neither passed the diagnostic's complete word timing gate, so no word-aligned candidate interval was silently invented or tracked as approved.
- Source listening review points: first retained phrase approximately 528.361–529.484s in FINAL Director (source 964.26–965.52s); second approximately 534.051–536.554s (source 973.69–976.56s). These were remapped from source against final XML A1, not confused with the longer prepare/safe manifest clock.
- ASR acoustic spans may include silence; partial coverage is a REVIEW FLAG, not proof that an audible syllable is missing. Listen before changing trims. Preserve the strict source/voice policy and reverify all audio/source maps if a future approved repair changes cuts.
- Safe next work: source-audio boundary review, then exact spoken CTA timing, then tracking BOTH angles at that approved timing; if geometry still fails, a separately authored compact layout with its own complete alpha/native typography proof. Do not weaken placement/font/copy gates.

## Remaining — do not claim publication ready

- Three copy/placement-blocked editorial cues plus Subscribe still excluded; native review does not mean every requested graphic is complete.
- Full audio/source transcript and draft subtitle review required; no new listening QA claimed today.
- Final video export intentionally not performed.
- Compact Rim all-frame alpha proof is now complete; source timing and full-video/native-placement gates remain as above.
- Auto-generated older edit-notes count six graphic PROPOSALS and retain legacy PNG-guide wording; that does not mean six inserted graphics. Native inspect receipts prove exactly two real MOGRTs and no PNG timeline assets in this review.
- User-facing review guide: `proof/final-native-20260912-01/REVIEW_FIRST_FA.md`.
- Final native state: Premiere left visible on the saved new Director sequence at 24s, first title visible; Hafez Studio also open and idle. No active engine/capture jobs. Rechecked project SHA256 still `10d2934eb98c980dc925ec44979547a685ce1d938e0bd7c1d1142b8a0c017e0f`.

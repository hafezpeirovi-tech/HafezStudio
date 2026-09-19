# Hafez Studio — final editorial continuation, 2026-09-09

## Scope and acceptance

Finish an editable Premiere review project from automatic Hafez Studio editing. **No automatic final movie export.** Keep original authored AE artwork, native editable MOGRTs, ABAR High FaNum, conservative source-faithful copy, all-visible-source-frame body/face safety, and untouched source voice. No Trading, MetaTrader, database, credentials, or Hermes core changes.

The work is **not fully finished and not publication-ready**. Do not report this candidate as deployed or as the latest completed Premiere project.

## Completed in this continuation

- Hash-verified backup: `backups/final-editorial-20260909-01`, including original editing modules, catalog, CEP JSX, and previous Premiere review file. Separate curator history backup exists here too.
- New `graphic_framing.py`: frame-exact camera coordination for already source-qualified Glass titles; all-frame tracking on candidate angles; protected neighboring graphics; final full tracking recheck and atomic rollback on failure. Source trims/audio are not changed.
- Curated exact topic label policy: `SMART TRADER / تریدر باهوش`, with full original source clause/provenance retained. The display is a topic label, not an invented assertion. Incomplete, negated, uncertain, ambiguous, or unanchored copy is not rescued.
- 320 Python tests passed: `proof/final-editorial-20260909-01/python-tests-02-authorized.log`. The earlier `python-tests-02.log` is only a sandbox runtime-launch denial, not a test result.
- Syntax checks passed for Electron main/preload, renderer, and new alpha verifier. No Director UI redesign in this continuation.
- Source full replay: `proof/final-editorial-source-20260909-01/finalize`.
- Frozen engine built: `proof/final-editorial-engine-20260909-01/dist/hermes-engine`.
- Packaged full replay passed: `proof/final-editorial-packaged-20260909-02/finalize/candidate-run.log`.
- Packaged attempt `final-editorial-packaged-20260909-01` stopped because sandbox blocked writing the app's curator history. Preserve its failure log. A normal-access replay was successful; no permission/security settings were changed.
- Both successful replays reuse saved ASR and 10 local AI checkpoints. **Do not claim a new transcription/AI run.**
- Both outputs: 16463 frames, 549.315438 seconds, 31 camera shots, 30 switches, 13 punch-ins, 1353 mapped words, 157 draft subtitle cues, 2 eligible native MOGRTs, 4 blocked proposals, 0 PNG timeline assets.
- Independent verifier: `proof/final-editorial-20260909-01/verify-finalize.ps1`. Both successful output folders contain `final-editorial-offline-preflight-v2.json`: all 16463 video frames have exactly one active camera; all 198 graphic frames map to independently observed source face/body frames with no transform or overlap; title-safe and font floors pass; SFX starts match cue frame; A1 unprocessed/A2 disabled. Every audio source-frame mapping equals the previous baseline (audio split count changed 152 -> 153, but zero content-frame differences).
- `graphic-001`: 684..779 exclusive; ANALYSIS PARALYSIS / فلج تحلیلی.
- `graphic-002`: 1684..1787 exclusive; SMART TRADER / تریدر باهوش. CAM2 has been selected automatically for this interval; final tracking rechecked. It is not yet imported/visually checked in Premiere.

## Current native Premiere state

Working Save As: `proof/final-editorial-20260909-01/Hafez-Final-Editorial-Review.prproj`.
This is still the previous one-MOGRT review baseline, **not** the newly generated two-MOGRT timeline.

Native A/B changed Title and Body from AbarHighFaNum-Black to Regular at 24 seconds. Both visibly became thinner. Both restored to Black; matching fresh CEP receipts are `font-regular.result.json` and `font-restore.result.json` in the proof folder. No new cue was imported by that test. Save after restoration when UI is available. Do not delete/move the adjacent legacy Motion Graphics Template Media dependency.

Installed app engine is still `preview-geometry-engine-20260909-03`, not this new candidate. Installed catalog also differs from the source catalog. Deployment must preserve/update the approved catalog with backup, not merely swap the executable. Current new source catalog SHA256: `33919b2b5ce63f4709e378fbb6eccbcB300a7cd7f5a5191291cc55204314138e` (case-insensitive hex). Recompute before deployment. Frozen source must still match.

## UI pause: input interference, not a native-render failure

During AE Run Script File, requested path entry instead showed unrelated clipboard text. It was **not executed**. A prior action also reported another app covering the intended point. Input was paused; the user was asked asynchronously whether the system/clipboard can be left free or whether only file work should continue. No answer received at this checkpoint.

Read-only AE observation still showed the Run Script File dialog with incorrect text highlighted. Do not click Open on that text. Refresh real window state, confirm exclusive input availability, clear/correct and visually verify the intended path before executing. Use Computer Use skill only for native UI, not PowerShell UIAutomation/SendKeys or a command-line UI bypass.

## Subscribe Rim: prepared, not promoted

Private AEP open in AE:
`proof/subscribe-compact-native-20260905/rim-controls-candidate-01/Hafez Subscribe Compact Rim Review 2.aep`
SHA256 `9b2680d735a339d2fa01016c3c5d1293b18e7eef1dcd3c7a8529906e420cc4dc`.

Correct final MOGRT:
`proof/subscribe-compact-native-20260905/rim-controls-candidate-01/Hafez Hermes Subscribe Compact Rim Review 2 - Native.mogrt`
SHA256 `dc19dbff5de351022a3c0d6fc2ddeaec17553d758736b4e7de167a6a5b0f96a4`.
Alias with proper native import basename in `premiere-rim-qa` has same hash. Do not use the different raw MOGRT in the candidate folder.

Prepared AE entry script:
`proof/subscribe-compact-native-20260905/capture_rim_alpha_all_20260909.jsx`.
It sequentially runs 8 validated chunks of 16 native RGBA captures (127 total), no controls/project/queue mutation, no movie export. The companion chunk script is hash-bound to the new private AEP and MOGRT. **It has NOT run.** Target `rim-alpha-captures-20260909-01` was absent on last check.

After successful capture run:
`node proof/final-editorial-20260909-01/verify-rim-alpha.js`
Its preflight already passed; full mode verifies exact frozen hashes, 25 unchanged controls, anchors, all frames/times/CRC/alpha and writes exclusive measurement receipts. Old Compact alpha evidence must not be re-labeled with the new Rim hash.

Existing Sept 5 Rim native A/B proves structural rim intensity/thickness affect native pixels and restore correctly. This is an edge/rim control, **not independent soft glow**; do not relabel it as soft glow or bind global Glow to it. Existing native typography tests are in the same proof tree. These do not establish all-frame body-safe placement in this full video.

Subscribe still blocked in catalog/runtime, correctly. It needs new alpha envelope qualification, actual full-frame alternate-camera tracking, readable size, exact spoken CTA timing, and native review before any automatic promotion. Do not shrink below font floor or clear safety/copy gates to force it in.

## Remaining order

1. Resolve input interference and complete AE alpha measurement on the unchanged Rim candidate.
2. Import the packaged `...20260909-02/finalize/F_Hafez_Youtube_8rdvid_C2963.xml` into an isolated new bin in the working Save As project. CEP import protocol must pin exact project path and verify the newly returned Director sequence ID, not an older identically named sequence.
3. Apply the matching packaged Premiere plan with a fresh request ID, empty queue, matching fresh receipt, expected active project/sequence. Verify two real native MOGRTs/21 controls, entry/hold/outro, body-safe visual layout, text and editable controls. Save this review project natively; no video export.
4. Attempt Subscribe integration only if the native/placement/copy prerequisites above genuinely pass. Other three blocked claims require reliable source review; do not publish bogus copy or placeholders as finished titles.
5. Only after native review: deploy frozen engine with recoverable backups/hash verification and sync the approved catalog; installed app smoke test. The existing deployment script alone does NOT sync catalog.
6. Write a truthful final review handoff: remaining copy/listening/visual review flags, no claim of publication readiness and no automatic movie export.

No active engine/build/test sessions remain after the recorded successful checks. UI is the remaining immediate dependency. Guard validation remains mandatory for sensitive operations after any restart; never unlock the guard on the user's behalf.

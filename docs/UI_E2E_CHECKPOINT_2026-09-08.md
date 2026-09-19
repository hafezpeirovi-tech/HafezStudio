# Hafez Studio — actual app E2E checkpoint, 2026-09-08

Later the same day, the user selected the full camera files and a real full
edit was started from the app. See `FULL_VIDEO_RUN_2026-09-08.md` for that
completed full run, native full-length project and editorial limitations. The short-run handoff state below is
historical; do not confuse its test outputs with the new full-video output.

## Verified in the native desktop application

- Launched the installed `release/win-unpacked/Hafez Studio.exe` (candidate02 engine, SHA256 `cf4c82628f3ba4d347a365a6d17c420726389493ed450940fe565751a056b1e6`).
- Selected two existing real 12.012-second source excerpts using the native file dialogs: `proof/fresh-prepare-word-evidence-20260905/C2963-source-65p065-12p012.mov` and `C2955-source-57p3890625-12p012.mov`.
- Clicked Start in the app. Job `HS-MTSMICL6`, output directory `C:\Users\1SKY.IR\Videos\Hafez Studio Outputs\20260908-153558-C2963-source-65p065-12p012-MICL6`.
- Actual job log ran 12:05:59–12:07:05 UTC. New local ASR: 39 words, CPU fallback explicitly reported because CUDA runtime was unavailable. Four actual local model tasks (subtitle, visual, director, YouTube) returned `valid=true backend=ollama-local-json`; no bypass/checkpoint substituted for this review.
- Engine process ended; both completed event/progress100 and native app display100 were observed. The old 50-percent stop did not reproduce on this bounded input. This is NOT a guarantee for every full-length input.
- App settings migrated and saved to version7, source-faithful copy and balanced density, Glow0.8. Director design and slider code were not changed this session.

## Important quality finding

The only proposed title is `review_blocked=true`, with `NATIVE_TYPOGRAPHY_FIT_FAILED`. Its ASR source contains garbled words. A source-faithful copy is not proof that ASR matches the audio. No replacement sentence was guessed and the block was not waived. The XML has zero PNG timeline assets, no active title and no title SFX. Four SRT cues exist but are drafts requiring source-audio review.

The old completion summary counted that blocked proposal as one editable motion, with copyReviewRequired0. A scoped fix now separates eligible counts from blocked proposals. `graphicsReviewRequired` covers either blocked graphics or manual copy without double counting. Existing copyReviewRequired retains its narrower meaning. Renderer warns about blocked text/readability/placement proposals without calling them ready.

## Scoped changes and verification

- `engine/src/hermes_video/studio_cli.py`: completion counts only; no generation/cut/typography gate changes.
- `app/renderer.js`: one additional blocked-graphics warning; unchanged HTML/CSS and all other app archive files.
- `tests/test_graphics_completion_counts.py`: five regression tests. Initial run reproduced three failures and two missing-field errors. After the fix, full Python suite: **277 tests PASS** in28.46s.
- `proof/verify-summary-app-20260908.js`: three actual completion-branch executions with DOM/log stubs, PASS. Archive comparison confirms only renderer.js changes. An initial packaging attempt included a differently normalized package.json and was rejected; it was not deployed. `app-verified.asar` preserves the prior packaged metadata exactly.
- `proof/summary-engine-candidate-20260908-01/verification.json`: all18 bundled project modules equal frozen/current source,1888 runtime files. Verified packed CLI definitions return graphics0, editableMogrtLayers0, plannedGraphics1, blockedGraphics1, graphicsReviewRequired1 on the actual app job. All original job bytes unchanged.
- New candidate engine SHA256: `ca12b8ac07e341a175626f93785a1bf4d8317a319de7214523aa6d89adb31e3e`. `--help` and `doctor --json` passed; ASR remains CPU fallback.
- Backups before edits: `backups/ui-e2e-20260908-01` includes engine source, renderer/electron, settings and app.asar.
- **Deployed and runtime-tested.** `proof/deploy-summary-fix-20260908.ps1` completed after normal app closure and local authorization. Both live/packaging engine trees matched all1888 candidate files. Five files replaced, no deletion, backup verified in `backups/summary-fix-deployment-20260908-01`. The one-shot script must not be replayed. Its `runtimeSmokePending=true` is the historical state at installation; subsequent evidence is below.

## Installed runtime smoke and visible-warning follow-up

- Clicked Start again in the installed app using the same real source excerpts. New job `HS-MTSO65MD`, directory `C:\Users\1SKY.IR\Videos\Hafez Studio Outputs\20260908-162228-C2963-source-65p065-12p012-O65MD`.
- Fresh ASR39words, four actual valid local model tasks, native100% completion and **MOTION0** observed. Completed event reports planned1, blocked1, graphicsReviewRequired1, editable0, PNG0, publicationReady=false. XML again contains three351-frame sequences and is byte-identical to the first app-run XML.
- Installed `doctor --json` passed. ASR still uses CPU fallback. App+engine hashes verified; engine process ended. Evidence: `proof/ui-e2e-20260908-02/runtime-verification.json` plus copied log/XML/Plan.
- Native QA exposed a secondary UX bug: the existing completed layout hides the live log, so an appended warning alone was invisible. Renderer now adds the blocked count/review note to the existing `#summaryKinds` line. No HTML/CSS/layout redesign and no Python/engine changes in this follow-up.
- Follow-up backup `backups/summary-warning-visible-20260908-01`; candidate/deployment proof `proof/summary-warning-visible-20260908-01`. Five completion-branch cases passed, including mixed eligible+blocked and legacy summaries. Archive comparison proves only renderer.js differs. Current installed app SHA256: `0a1f3d2e18933018d6091ca4ae5c7890eab84440c95384e1a0470678284da874`; engine SHA remains `ca12b8ac07e341a175626f93785a1bf4d8317a319de7214523aa6d89adb31e3e`.
- **Final native display smoke passed.** Third actual Start-button job `HS-MTSOH54X`, output `C:\Users\1SKY.IR\Videos\Hafez Studio Outputs\20260908-163101-C2963-source-65p065-12p012-OH54X`, again ran fresh ASR and four valid local model tasks. Native100%, MOTION0 and the visible existing summary line `1 پیشنهاد مسدود؛ نیازمند بازبینی متن/چیدمان در Premiere Plan` were observed. Engine ended. Final deployed hashes, log, XML, Plan and assertions: `proof/ui-e2e-20260908-03/runtime-verification.json`. The final job XML is not byte-identical to the earlier jobs; do not mix its Plan with a different job's sequence. No further installation or picker click is pending for these fixes.

### Exact installed state at handoff

- App running normally, last bounded job completed; original12-second QA excerpts remain selected, NOT the full original sources. Select the intended full CAM01/CAM02 before starting a real new edit.
- Premiere remains open on the saved isolated `Hafez-App-E2E-20260908.prproj`, not the user's publication working project.
- 277 Python tests passed before the engine build; warning-only follow-up changed no engine code and passed five real renderer completion-branch cases. Native app smoke passed after final install.
- Further editorial/ASR work is still needed. Do not read `100%`, `doctor ok` or a blocked-graphic rejection as publication approval.

## Native Premiere negative-gate test — completed and saved

Created a separate native Premiere project:

`C:\Users\1SKY.IR\.n8n\products\HafezStudio\proof\ui-e2e-20260908-01\Hafez-App-E2E-20260908.prproj`

Imported byte-identical proof copy `App-Run.xml` through Import Media. Three sequences and two sources appeared. Opened `03 - Hafez Director Cut`:351frames,29.97fps, A1 original audio, A2 visibly muted, reserved empty V4/V5. Native monitor shows actual video. Saved through File > Save at16:18:46 local; title-bar asterisk cleared. File25757bytes, SHA256 `12cb016952e5da7e75505b22e74613a780cffe10b965940474fb10f5e8acb0fa`.

The earlier CEP-owned Plan picker could not be clicked through Sky because of an owner-window mismatch. On continuation the picker was closed, but no new Plan result existed. Used the existing inspected Finisher queue API (`mode=apply`), after confirming installed bridge hashes match source, to submit the exact proof Plan to the active isolated Director sequence. No mouse targeting restriction was bypassed.

Fresh request `ui-e2e-20260908-01-blocked-plan-apply` completed12:43:50.907UTC. Result: attempted0, inserted0, imported0, updated0, failed1, with `REVIEW BLOCKED: graphic-001` and typography-fit reason. Native Finisher shows the correct Plan and error/review state. Exact result retained at `proof/ui-e2e-20260908-01/finisher-result.json`.

This is a successful **negative safety-gate test**, not a successful insertion/publication result. A positive fresh-run native MOGRT insertion remains unproven for this sample because its sole title correctly stays blocked. No user click is pending.

## Preserve user's working project

`proof/Hafez-Publication-QA-20260905.prproj` was observed at2617526bytes with modification Sep7 15:57:28, newer than the old handoff. Do not overwrite it or assume its timeline still matches the Sep5 proof. It was not opened or modified this session. Existing full delivery and Subscribe native samples remain in the weekly guide.

## Still not publication-ready automatically

ASR lexical accuracy, complete auditory review, independent all-frame body tracking, automatic Subscribe enablement and general word-boundary cut repair remain unresolved. No template QA block was removed. No trading, credential, database, system-security or original media change was made.

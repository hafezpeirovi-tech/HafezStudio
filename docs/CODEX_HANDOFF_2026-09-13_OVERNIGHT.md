# Hafez Studio — overnight checkpoint, 2026-09-13

Read this before repeating September12 work. Continues `CODEX_HANDOFF_2026-09-12_NATIVE_REVIEW.md`. User authorized unattended completion, but explicitly does NOT want automatic final movie export. No final movie was exported or published. No Trading/Hermes originals, credentials, database or original AE project were modified. Official local boot-bound authorization passed before sensitive operations.

## Outcome — not publication-ready

The installed engine is usable and the automatic cached project replay completed. A new authored horizontal Subscribe MOGRT has actually been built, imported, visually tested and saved in Premiere. Full-source listening, uncertain copy/retakes, subtitle correction and spoken-CTA approval remain unresolved. Do not turn process100% or readback success into publication approval. Do not invent manual listening evidence.

## User's two real Premiere files

1. Full automatic Director review: `proof/final-native-20260912-01/Hafez-Automatic-Review-20260912.prproj`. Sequence `03 - Hafez Director Cut - Review 20260912`, about9m9s. Exactly two genuine editable titles on V4, no PNG overlays. Original file remained unchanged: SHA256 `10d2934eb98c980dc925ec44979547a685ce1d938e0bd7c1d1142b8a0c017e0f`.
2. New horizontal template QA: `proof/subscribe-horizontal-20260913-01/Hafez-Horizontal-QA-20260913.prproj`. This SaveAs contains the prior review plus a separate10s QA sequence `Hafez Horizontal Subscribe Native QA - 20260913`, ID `74a07c26-6af9-4487-a858-4aca564736af`. It is NOT an additional completed full-video edit. Saved712681bytes SHA256 `329e1991a6b9b19c5fe8272d747bed6d0b5767e58c6f926eab3733fae0986b88`.

Do not move projects separately from their Motion Graphics Template Media dependencies. No completed native request should be resent.

## Horizontal Subscribe completed

Full proof/readback/limitations: `proof/subscribe-horizontal-20260913-01/NATIVE_QA_COMPLETE.md`.

- Preserved frozen compact source by exact backup in `backups/subscribe-horizontal-20260913-01`. Original user AEP never overwritten.
- Build01 was reviewed and refined for internal vertical padding. Build02 is the delivered isolated template; no generated artwork or added effects, fonts ABAR High FaNum verified non-substitute.
- New AEP `build-02/Hafez Subscribe Horizontal Review 2.aep`, SHA256 `c12e868c401f1719cfe17fb768e455435843117454953ffbfaf5367c800bb9d0`.
- Importable `build-02/Hafez Hermes Subscribe Horizontal Review 2 - Native.mogrt`, SHA256 `be6d474b9cb17dba0b563da18a5e92c23805a4c24c4cb7c8c8eddbcff25c1bb2`. Only definition metadata flags changed for native font/size editing; all other ZIP payloads preserved byte-for-byte.25 public controls.
- All127 actual RGBA frame files decoded/CRC checked/hashed; alpha>=1 union728x246, terminalframe126 empty, no canvas-edge contact. The first script initially queued more captures than were physically written; missing files were completed with stable-file checking, so use `measurement.json`, not the early queue report as completion proof. All capture work is now done.
-504 source-frame observations across both cameras and two candidate word windows completed. New QA uses CAM2 at identityscale, Layout971/171Scale100Duration4.2, smallestauthoredfont26HDpx. Complete alpha envelope is title-safe and above protected all-frame face/body union. This does NOT approve ASR word timing.
- Real import1 then7 control changes and restore, all distinct exclusive requests. Native25-parameter verification passed for8cases (font,size,multiline,leading,colors,rim-intensity,rim-thickness,restore), no duplicates or source-track changes. Visual responses separately observed in Premiere. Native entry2:08, hold4:06 and exit6:03 sampled; restored/saved.
- Rim Intensity/Thickness control actual luminous edge, not soft glow or Deep Glow. Glass Surface color response was subtle (measured small delta), not dramatic; name text color responded strongly.
- Actual native preview `proof/horizontal-baseline-20260913.png`; comparison `proof/horizontal-colors-20260913.png`. These are QA exports, never timeline PNG substitutes.
- Not catalog-promoted. Isolated QA has no SFX; final Director still has its existing two synchronized entry SFX. No Subscribe was inserted into full Director at an invented onset.

## Newly fixed engine bug — deployed

Found `write_youtube_package` was receiving Safe mapping/markers although final Director inherits Tight. Changed only `engine/src/hermes_video/autocut.py`:

- Added `write_director_youtube_package` and wired finalization to actual Director mapping/markers/duration/name.
- Reject chapters outside final duration or on a removed source segment.
- Clearly labels the generated package as a draft requiring content/link review. Does not silently rewrite transcript, source speech or model description.
- Added5tests in `tests/test_director_youtube_package.py`. Full suite **338passed**, log `proof/director-package-20260913-01/python-tests.log`. Electronmain/preload/renderer syntax checks passed at their real paths. A preliminary check at nonexistent root filenames failed harmlessly and was corrected; no UI source edits.
- Source backup: `backups/director-package-20260913-01/autocut.py`.
- Frozen candidate `proof/director-package-engine-20260913-01`, build passed. Standard excluded converter/CUDA DLL warnings remain; CPU ASR supported, GPU ASR not claimed.
- Packaged full replay `proof/final-editorial-director-package-20260913-01/finalize`, completed100% with ten validated local AI checkpoints and cached ASR; NOT fresh ASR. One-shot runner `proof/director-package-20260913-01/run-replay.ps1`, do not repeat into existing output.
- Independent preflight16463Directorframes,198visiblegraphicframes passed. Twoeligible/fourblocked preserved. A1 untouched, A2 disabled, no PNG. New XML exactly byte-identical to prior verified XML SHA256 `ea8845ad6d5a5512e8a127eb8e24e403c2280a56567f32dd523693bfc5faee8f`. Bothsafe/tightsubtitles also byte-identical. No new native reimport was needed.
- Deployed to both engine locations; all1891files per copy hash-verified. Hafez closed normally while idle before deployment, relaunched afterward.
- **Current engine EXE SHA256 `7b36cdf114a42182061f62ddddfc29f69ed4be44fccc46207fa2edd99565ce37`.** Supersedes September12 engine.
- Both prior engines recoverably retained at `backups/director-package-deploy-20260913-01/{installed-engine-before,packaging-engine-before}`. Nothing deleted. Deployment evidence `proof/director-package-20260913-01/deployment.log`.
- Installeddoctor passed (`installed-doctor.json` in that proof folder): ASR imports true, localbody/face/Persianmodels ready,11fonts, CUDA runtimefalse. ASAR/UI unchanged SHA256 `0a1f3d2e18933018d6091ca4ae5c7890eab84440c95384e1a0470678284da874`; catalog unchanged.
- Actual Hafez Director shown idle0/2, Engine/ASR and Adobe ready, Glow80%correctLTR. App `release/win-unpacked/Hafez Studio.exe` open.

## Remaining publishing review, with useful prepared material

`proof/director-package-20260913-01/REVIEW_BEFORE_PUBLICATION_FA.md` and hash-bound `review-index.json` map suspicious sections from original ASR SOURCE timestamps through the exact final A1 clips. This avoids confusing prepare/safe/final clocks. No cuts changed. Full index includes source pieces, not fabricated audible onsets.

- First old opening segment is already absent from Director; do not re-delete a retake based only on prepare transcript.
- Around0:38–0:54, possible restarted introduction; around1:27–1:38, possible off-presentation conversation. Need actual hearing before cuts.
- Three other blocked graphics remain excluded: time-efficiency sentence, account-cost title, broker comparison. Incomplete copy is never displayed as a complete headline or baked PNG.
- Subscribe phrases around8:48–8:50 and8:54–8:57 still have partial-word boundary flags. Listening files already exist in `proof/subscribe-source-review-20260912-02`; no actual audio approval this turn.
- Generated YouTube timestamps now use correct Director clock, but the model's semantic chapter labels/segment IDs can STILL be wrong (e.g.giftlabel near4:30 rather than actualgiftsection~8:04). Do not claim semantic chapter validation fixed by a clock fix.
- Review guide provides a separate conservative topical chapter proposal mapped independently from source sections, plus shorter draft titles/description/pinned comment without invented links, profit promises or unsupported broker superiority.
- PDF gift URL/file still needs owner validation; nothing uploaded.
- Full subtitle/text listening QA remains.338tests and playback samples are not substitutes for that.

## Safe next work

User/source-audio review at flagged times, grounded copy corrections, then approved spoken timing and all-frame/native insertion for the new horizontal CTA with exactly synchronized curated SFX. Any changed text/font/duration invalidates prior alpha footprint. Do not weaken source-word/native-release gates, invent review approvals, rerun completed one-shot proofs, overwrite originals or automatically export the final video.

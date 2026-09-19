# Automatic editing acceptance — 2026-09-08

## Deliverable

Open `proof/automatic-quality-20260908-06/Hafez-Automatic-Quality-20260908.prproj`.
Use sequence **03 - Hafez Director Cut**. Keep its adjacent
`Motion Graphics Template Media` directory; camera originals remain on drive F.
The matching full native render is `Hafez-Automatic-Quality-20260908-REVIEW.mp4`;
the short real-render excerpt is `Hafez-MOGRT-Preview-21s-28s.mp4` in that folder.
User-facing Persian instructions are in the adjacent `README-FA.md`.

The 1920×1080 review render is 16,463 frames at 30000/1001 fps (549.315438 s).
Full FFmpeg decode finished with exit 0 and no reported errors. This is a review
delivery, not an audio/editorial approval for publishing.

## Proven scope

- 30 camera switches, 31 shots, 13 punch-ins; 8.57 additional seconds removed
  in Tight using bounded abandoned-take/setup rules. Safe remains conservative.
- 157 word-timed caption cues, 1,353 mapped words; caption text stays source-ASR
  draft. Captions are not burned into this MP4.
- One real Glass Insight Review 8 MOGRT on V4, 22.8228–25.992633 s. Title
  `ANALYSIS PARALYSIS`, Persian `فلج تحلیلی`; 21 native Premiere parameters read
  back, including ABAR High FaNum fonts, size, leading, colors and layout.
  Five other proposals stay blocked. No PNG graphics are inserted on the timeline.
- Native SFX begins on frame 684, the same frame as the MOGRT. A1 contains
  unprocessed camera-one audio; camera-two audio is disabled. No background
  music was added, so this delivery does not demonstrate music ducking.
- Native Premiere project was saved separately. Automatic decisions came from
  the app/engine; native import, Finisher application, saving and MP4 export were
  assisted host operations, not newly implemented unattended export automation.

## Engine changes and verification

Backups precede all edits: `backups/automatic-quality-20260908-01` and
`backups/automatic-copy-gate-20260908-01`. Original installed/packaging engine
directories are retained inside those backups; nothing was deleted.

The local review contract now requires complete action/confidence/reason/removal
fields. Retake removal protects a later matching surviving version. Graphics
must be uniquely grounded in source words. Bounded ASR timestamp recovery retains
plausible original words rather than inventing a replacement transcript.
Word-timed captions follow actual A1 keeps, and source media hashes are checked.
Whisper loading is local-only; unavailable CUDA dependencies lead to explicit
CPU fallback, not an implicit download.

A real short-clip UI test exposed a malformed ASR sentence that fitted a card and
therefore passed the old geometry checks. The new `guard_automatic_graphic_copy`
blocks unverified machine sentences even when grammar/fit look acceptable.
Only re-derived local glossary term labels with unchanged native controls pass.
This is a conservative eligibility gate, **not a fix for poor ASR accuracy** and
not a general user-approved copy ledger. Rejected graphics also lose their SFX.

298 tests pass (`proof/automatic-quality-20260908-06/tests-copy-gate.log`).
The final frozen candidate is `proof/automatic-quality-engine-20260908-04`.
Its full finalization in `proof/automatic-quality-candidate-20260908-02/finalize`
finished successfully, deliberately reusing ten saved local-model review tasks.
The earlier full app run HS-MTSP6VMT performed fresh ASR and ten fresh local tasks.
The negative replay in `proof/automatic-copy-gate-candidate-20260908-01` produces
zero graphics and zero SFX, with `UNVERIFIED_MACHINE_GRAPHIC_COPY` recorded.

The saved native delivery was imported from candidate 01. Candidate 02's XML and
both SRTs are byte-identical; eligible MOGRT parameters/timing/layout and SFX are
also identical. `delivery-verification.json` records this reuse verification,
artifact hashes and the honest publication/tracking limitations. Both installed
and packaging engine copies were replaced with candidate 04 and all 1,888 files
hash-verified (`deployment-copy-gate.log`). The existing Director UI/app.asar was
not redesigned or rebuilt in this update.

After deployment, a fresh real UI job **HS-MTT2Q2HB** ran both 12.012-second
camera excerpts from 19:39:53 to 19:41:04 UTC. Fresh offline Whisper and four
fresh valid local Qwen tasks completed (no AI checkpoint reuse). The app reached
100%, displayed 3 draft captions / 0 motion / 1 punch-in, and showed one blocked
copy proposal. The exact malformed clause is withheld with
`UNVERIFIED_MACHINE_GRAPHIC_COPY`, and there is no orphan SFX. Evidence:
`proof/automatic-quality-20260908-06/installed-ui-copy-gate-job.log`.
Installed engine SHA256:
`b5b0822947b62a9bb280680e24508d91adcd6e8410dc60f460beaa4871d90d82`.
After this smoke test, both full originals C2963.MP4 and C2955.MP4 were restored
in the app's camera pickers and visually verified. No second full job was started;
the completed result counters still describe the short smoke test until a new run.

## Remaining publication gates

1. Listen to and correct source ASR, especially names, numbers and technical
   vocabulary; check cut boundaries/remaining false starts. Captions remain draft.
2. Independent body/hand detection across every frame is not implemented. The
   demonstrated placement uses nine sampled frames and a conservative face-derived
   envelope, not the requested complete-body tracking proof. A small official
   local body model was proposed; it was **not downloaded without permission**.
3. Additional template families, automatic Subscribe and complete unattended
   native rendering are not accepted as production-ready by this evidence.
4. MOGRT controls being exposed/read back does not certify every third-party
   effect reacts correctly at all values. Do not infer such coverage from tests.

Trading/MetaTrader, database, credentials and original Hermes were not changed.

# Full source-video run — 2026-09-08

## Completed engine run; native full-length project saved

The full job completed at 13:59:03.025 UTC (17:29 Tehran), approximately
38 minutes after native Start. All ten local-model review tasks returned valid
JSON. The engine process ended. The old 50% stall did not reproduce on these
full camera files. Completion is NOT publication approval.

With the user's explicit availability and native-control approval, a separate
Premiere project was created, the exact job XML imported, and the matching
unmodified Plan applied through the installed Hafez Finisher. No earlier
Premiere project, source media, or installed application code was modified.

- Project: `proof/full-ui-20260908-01/Hafez-Full-Auto-20260908.prproj`.
- Active Director sequence ID: `cb4f1759-f696-4cff-a4b0-1492697c3a6d`.
- Three imported sequences: Safe 16720 frames; Tight and Director 16699 frames.
  Rate 30000/1001; Director duration 557.189967 seconds (9m17s).
- Import result, Finisher result and native parameter readback are preserved
  in that proof directory. File > Save completed; the title-bar asterisk cleared.
- Initial saved project: 416536 bytes, SHA256
  `376bdda11a3618c7ae9889cf6e3553242bbfffed526c952caf7e73f8cb20bbbb`.
- Native Premiere frame export at 00:00:32:00:
  `proof/full-ui-20260908-01/Hafez-Full-Auto-20260908-32s.png`.
  This is evidence only; Import into project was unchecked.
- A full native H.264 review export completed to
  `proof/full-ui-20260908-01/Hafez-Full-Auto-20260908-REVIEW.mp4`.
  Verified: 1920x1080, 30000/1001 fps, 16699 frames, AAC 48kHz stereo,
  557.189967 seconds, 1414524437 bytes. Full decode-to-null exited 0 with
  no errors. SHA256 `09ac31520e2077eda7b1d98a83f446215878f8eac9bf8f31d9ab98cfc3cc82d9`.
- An 8.008-second viewing excerpt (28–36 seconds of this native render) is
  `proof/full-ui-20260908-01/Hafez-Automatic-MOGRT-Preview-28s-36s.mp4`.
  It was extracted from the Premiere export, not reconstructed from PNGs.
- Saved prproj decompresses successfully, contains both original camera media
  and Glass Insight Review 8, and contains no `.png` reference. Its local
  aegraphic media exists (7638582 bytes). The app's native completion summary
  also shows 140 subtitle cues, 1 motion, 13 punch-ins, 30 camera cuts and the
  warning for 8 blocked proposals. No new full edit was started.

## Verified output and remaining editorial issues

There are 31 camera shots, 30 switches, 13 punch-ins, 140 draft subtitle cues,
9 proposed graphics, and only 1 eligible editable MOGRT. Eight proposals remain
blocked (four unreliable source clauses; unapproved chapter template;
two typography failures; failed canonical Subscribe native QA). The Finisher
returned inserted=1, attempted=1, imported=1, safetyFailures=0, warnings=[],
failed=8 exclusively from preserved REVIEW BLOCKED decisions. Its ok=false is
therefore a partial editorial result, not a failure to import the eligible MOGRT.

The actual MOGRT is Glass Insight Review 8 on V4, enabled at frames 920–1015
(30.697333–33.867167 seconds). Native getMGTComponent returned 21 properties.
Live Title is `ANALYSIS\rPARALYSIS`, Body is `فلج تحلیلی`; font and size editing
flags are true, both AbarHighFaNum-Black, sizes 67/87. Line spacing 74/100,
colors, layout, glass and glow controls read back correctly. This readback
proves application of controls, not fresh A/B visual validation of every effect.
The hold frame renders both texts and the glass/glow element outside the face.

The XML references no PNG timeline media, all three unique media paths exist,
and the entry SFX starts exactly at frame 920. Original voice is on enabled A1,
camera-2 audio is muted on A2, and there is no background music or ducking.
Native export has all extra export effects, including loudness normalization,
unchecked. Placement used nine sampled frames and a conservative face-derived
body envelope; it is NOT independent all-frame body tracking.

Important: native frame zero still shows an empty chair. The first two retained
pieces total 26 frames (source frames 253–265 and 1468–1482); spoken content
starts later. Retakes and incomplete sentences remain. The draft SRT includes
ASR errors and e.g. a 40ms cue at 30.651–30.691 and an isolated word held for
several seconds. Positive, ordered SRT timestamps do not establish usable
caption timing or correct transcription. 41 word-boundary review candidates,
54 rejected lexical/numeric subtitle proposals and 4 copy-review items remain.
Do not burn these draft subtitles into a publication export or guess corrections.
No safety gate was waived; no manual editorial polish is being presented as an
automatic engine improvement. The September 5 manually refined delivery is
separate and remains untouched.

## Original run record

The user selected the full camera files in Hafez Studio. Native UI inspection
confirmed both paths and an idle app. Local HERMES_CONFIG_WRITE authorization
passed before Start. No source, installed code, original media or existing
Premiere project was changed in this turn.

- CAM01: `F:\Hafez\Youtube\8rd vid\C2963.MP4`, duration999.999seconds.
- CAM02: `F:\Hafez\Youtube\8rd vid\2\C2955.MP4`, duration994.4935seconds.
- Native Start clicked at16:51:02 Tehran,8September2026.
- Job: `HS-MTSP6VMT`; initial engine PID34972, started at the same time.
- Output: `C:\Users\1SKY.IR\Videos\Hafez Studio Outputs\20260908-165102-C2963-P6VMT`.
- Settings observed: balanced density, fa-en, Glow80%, GPU First with actual
  CPU ASR fallback because cuBLAS12 is unavailable.
- Camera synchronization and original-source fingerprint completed. Fresh ASR
  began on566.87seconds of retained speech audio. Log progressed from0% to9%
  by13:23:31UTC; this is ASR progress, not whole-pipeline completion.

## Background follow-up

Thread heartbeat automation `hafez-p6vmt` was originally created ACTIVE,
every5minutes, read-only and limited to this job. It checks actual progress,
quiet on non-actionable state, then validates outputs at completion or reports
a terminal failure. It must stop after the terminal result. It must not start
another edit, cancel this job, control mouse/keyboard, or alter any project.
Verify process identity/start time before trusting a reused PID.
After full completion was verified, this heartbeat was set PAUSED through the
official automation tool; no further monitoring or duplicate edit is needed.

Full-source selection here supersedes the short-excerpt selection noted in
`UI_E2E_CHECKPOINT_2026-09-08.md`. The installed hashes and successful short-run
tests in that checkpoint still apply, but do not prove this full job completed.

After completion, import only this job's XML and matching Plan into a new
Premiere project, with the user's availability confirmed for native UI work.
Do not overwrite `proof/Hafez-Publication-QA-20260905.prproj` or confuse the
short `Hafez-App-E2E-20260908.prproj` with the full source-video job.

`100%` means editing artifacts were generated, not that wording, cuts, MOGRT
placement and the entire video are publication-approved. Source-audio review
and existing editorial limitations remain in force.

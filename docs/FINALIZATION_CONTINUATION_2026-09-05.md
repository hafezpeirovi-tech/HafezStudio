# Finalization continuation — source repairs, not a publish-ready release

## State at handoff

The latest full Python suite passes **179/179**. Evidence:
`proof/finalization-source-tests-20260905.log`.
No new engine build/deployment or native Premiere import/export occurred in
this continuation. The existing desktop executable still uses the previously
verified engine (`c4b6f96a520fdf293db55bff7b5a8cf7518c7f65b99bdb59716442d6ce90e59c`).
The prior Delivery Review MP4, native project and two Glass clips are preserved.
This is NOT a declaration of end-to-end automatic publication readiness.

## Implemented source changes

- `word_boundary_guard.py` and narrow `autocut.py` integration preserve raw
  acoustic word times, ASR run/model/media provenance separately from clipped
  timeline times. Exactly contiguous source+timeline fragments map once.
  Nonzero gaps remain **report-only**; no source audio frames are restored.
  Ordinary or targeted ASR, clipped legacy timestamps and protected phone/
  retake/manual removals cannot self-authorize repairs.
- `caption_layout.py` and `subtitle_pipeline.py` preserve numeric fragments
  without changing their digits/spacing, keep them together in wrapping, reject
  invalid/overlapping timing, and preserve hard boundaries. Legacy production
  segments are hard boundaries by default because they lack reliable remapped
  source-word ledgers. The proof word-based regrouping is NOT yet the normal
  variant-caption path.
- `spatial_audit.py` is an **opt-in evidence validator**, not an implemented
  body detector or a replacement for current planner tracking. It maps every
  requested frame, rejects missing observations/unknown transforms, globally
  duplicate clip IDs, stale render context and incomplete artwork frame IDs.
  Real independent-body inference, native transform calibration and all-frame
  artwork footprint measurement remain pending.

## Real isolated artifacts

- Subscribe font and size editing flags were enabled on Review 1 after backup.
  An additional, separate defaults candidate exists at:
  `proof/subscribe-finalization/defaults-candidate-20260905/Hafez Hermes Subscribe Review 1 - Defaults Candidate.mogrt`.
  It repairs 25 control defaults with correct Unicode/schema and Studio palette;
  AE payload and font/style schema are preserved. It is **not** a compact layout,
  has not passed a fresh native import/edit test, and was not promoted.
- Geometry: the authored wide Subscribe cannot fit the current approximately
  326×278 HD side region readably. The proposed compact reflow must retain the
  authored logo/plate/artwork/easing; see
  `proof/subscribe-finalization/geometry-and-binding-audit.md`.
  Metadata includes `ADBE Noise2`: inspect its actual layer/use before any
  no-grain certification; absence of the word “grain” is insufficient.
- Corrected caption-layout proof V2:
  `proof/publication-job-20260905/caption-layout-review-v2-20260905/`.
  Safe preserves1241 words (147→145 cues); Tight preserves1238 (146→144).
  Four short cues remain explicitly flagged because regrouping would cross a
  source-take boundary. Decimal screen splits and the isolated long «بدم» cue
  are improved without lexical changes. These are unverified raw-ASR drafts.
  The first `caption-layout-review-20260905` proof is superseded and labelled;
  its zero-short-cue result must not be used to claim all timing issues fixed.
- Strict spatial proof V2 reads existing native integer bounds for Glass.
  Subscribe's native bounds are unresolved; any outward-rounded plan coverage
  is provisional. No video decoding, body inference or new native QA occurred.

## Outstanding user responses / blockers

1. Computer Use could not activate Premiere (`failed to activate captured
   window`). Fresh selection and one retry both failed. Following the skill's
   recovery limit, no more UI input was attempted. User was asked to bring
   Premiere forward from Taskbar and reply “Premiere بازه”. No reply yet.
2. User was asked to authorize ONLY official OpenCV Zoo PP-HumanSeg (~6 MB)
   plus its license, stored in HafezStudio for offline processing. Existing
   local-only/no-download restrictions remain active; nothing was downloaded.
3. Opening four/five-frame intraword cuts, specific repeated/abandoned clauses,
   raw ASR names/numbers and full dialogue still require audio review. See
   `proof/publication-job-20260905/DELIVERY_EDITORIAL_NEXT_PASS_2026-09-05.md`.

## Backups / boundaries

- `backups/finalization-20260905-subscribe`: catalog, original Review 1, owned
  publication AEP and native QA project before this pass.
- `backups/word-boundary-guard-before-20260905-180413`: pre-edit autocut source.
- `backups/caption-layout-before-20260905-181505`: pre-edit subtitle source.
- Spatial review hardening has its own source/test backup recorded by its helper.

Fresh local authorization checks succeeded. No security configuration or guard
was changed. A legacy proof wrapper contains PowerShell ExecutionPolicy Bypass;
it was inspected but **not run** in this continuation. Use the official guard
directly in the current permitted shell, never bypass execution policy.
No Trading/MT5/database/credentials, original Hermes or original user AE project
was edited. No media/model downloads, uploads or UI redesign occurred.

## Next bounded steps

Restore native UI access; obtain model download permission; implement/infer
independent body masks on exact visible frames and calibrate XML transforms;
build the compact authored Subscribe, inspect/remove actual grain effects,
render all-frame alpha and native editable-control proofs; audition and repair
only evidenced bad joins; integrate source-word variant caption mapping; run
regressions, build/deploy with backup, and perform a new cache-only end-to-end
smoke and actual Premiere export. Keep current delivered media until those pass.

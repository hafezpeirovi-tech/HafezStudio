# Review of the owner's accepted editing requirements

**Current handoff:** use the **Delivery Review pass** and **Deployment** sections
below, plus `proof/publication-job-20260905/START_HERE_DELIVERY_REVIEW.md`.
Earlier dated evidence is retained as history; old durations, test counts and
Review 7 limitations are superseded where the later sections explicitly say so.

This audit supersedes obsolete PNG/Relaxe/colloquial-copy claims in the older
Step 1, architecture and release documents. The latest approved basis is the
owner's After Effects elements, ABAR High FaNum, the Director UI palette, and
editable Premiere MOGRTs. Existing title animations are approved; this task
repairs execution and validates the actual September 5 video.

| Requirement | Evidence / acceptance condition |
| --- | --- |
| YouTube two-camera edit today | Continue C2963/C2955 from the saved transcript and synchronization; produce Safe, Tight and Director sequences. |
| User-owned templates | Fourteen canonical Hermes MOGRTs; prioritize Glassmorph lower thirds and Title Hero 3/2. |
| Editable graphics | Text, font/style/size, text/background colors, line spacing and tracking remain MOGRT controls. XML carries no PNG stand-ins; the Premiere Finisher must insert real components and read text back. |
| Approved title glow | Preserve actual PEDG2 Radius 200 and Exposure binding; Title Hero 3's normal slider value uses the accepted Intensity 20 baseline. |
| Visual identity | Dark glass and green Director palette; maximum four families; history shared across successive jobs. |
| Text accuracy | Source-faithful Persian, no register conversion or invented claim. Complete corrected take preferred; an uncertain graphic field remains editable `…` and must be flagged for review. |
| Sparse meaningful graphics | Model proposes semantic events; rules gate facts, density, family and element selection. |
| Grain | No grain asset or effect in the canonical MOGRTs. |
| Timing/audio | Authored easing; curated local SFX at MOGRT first frame. Camera 1 dialogue kept without gain/EQ/compression; no voice ducking. No background music has been supplied. |
| Spatial safety | Sample the graphic lifetime across the camera angles that are actually visible. Face boxes are detected; body boxes are conservative face-derived envelopes, not an independent body detector. A numeric safe-layout flag is not a substitute for checking the actual MOGRT in Premiere. |
| Qwen Vision | Final visual QA only. A template-selection rule or JSON metadata does not prove that visual QA ran. |
| Local assets | No asset/model download is needed for this repair. |
| Output acceptance | XML/Plan/SRT/YouTube package, actual Premiere MOGRT import, editable text readback and visible output; test counts alone do not prove an end-to-end delivery. |

## Defects found in the previous readiness claim

- At 50 percent, ten local AI tasks could run silently for many minutes;
  successful intermediate responses were not checkpointed.
- The range input inherited RTL while its fill was LTR. The old geometry test
  calculated both endpoints using the same assumed direction.
- The old UI test preload omitted the progress callback used by the renderer.
- The previous smoke test established only a live process, not a rendered
  window or a completed edit.
- History was saved per job but not shared with the next video's selection.
- Camera 1 alone was used to place graphics although camera 2 can be visible.
- Generic layout handling displaced curated template layers as though they
  were small Persian companion captions.
- Substring matching could confuse `Title` with `Title Text Color`, and a
  successful color change was counted as successful editable-text delivery.
- The final report still described PNG fallback even though XML now omits it.

## Recovery and scope

Backup: `backups/today-edit-recovery-20260905-122314`.
The original September 5 manifest remains the analysis checkpoint. Reels and
Podcast remain later workspaces. Installer/model-pack commercial distribution
is separate from today's personal editing acceptance.

## Verified recovery on September 5

- Recovered the original C2963/C2955 job from its existing manifest, word
  transcript and cached review tasks, without repeating the long ASR pass.
- Generated Safe, Tight and Director sequences (Director approximately 9:17),
  subtitle files and the review package. Camera 1 dialogue is not processed;
  camera 2 audio is muted. No background music was supplied.
- Saved a separate native project at
  `C:/Users/1SKY.IR/Videos/Hafez Studio Outputs/20260905-114715-C2963-40NWM/Hafez-Director-Recovered-20260905.prproj`.
  The original owner project was not overwritten.
- The native Director timeline contains three actual MOGRT components on V4
  (two enabled, Subscribe disabled after failing native visual QA),
  not PNG cards. V3 is empty/muted. The plan was applied repeatedly without
  stacking duplicate clips. Exact text was read back from native parameters.
- Hero 3 displays `فلج تحلیلی` around 00:32. The glass quote uses the exact
  source clause `تریدینگویو یک بخش کامیونیتی داره.` around 03:22. These are
  two reviewed selections, not proof of a fully reviewed nine-minute script.
- Restored the approved Glass Insight Review 7 wrapper from the development
  archive. The previous canonical file was the obsolete vendor capsule.
- Found a real Premiere coordinate defect: UI point [400,260] reads back as
  [400/1920,260/1080]. Pixel values sent directly had clamped the control to
  32767, placing graphics offscreen. The Finisher now normalizes point values
  and verifies the native readback.
- Glass Review 7 has a 720x380 plate. Its authored size plus halo is now fitted
  to the tracked safe region, with a regression covering HD and 4K footage.
  This does not yet certify physical bounds of every other catalog template.
- The range input direction is explicitly LTR. In the branded application,
  0/50/100 percent were visually checked for empty/half/full fill and correct
  thumb direction. Existing Director styling was otherwise preserved.
- All 69 Python tests pass. Four JavaScript control-test groups pass (exact
  text/aliases, native ARGB colors, normalized point controls, isolated
  review-blocked cue handling). The rebuilt
  engine is deployed in `release/win-unpacked/resources/engine/hermes-engine`.
  Its doctor reports required media tools, Adobe apps, fonts and local ASR.
- The deployed `release/win-unpacked/Hafez Studio.exe` was launched through
  native UI and its actual Director window rendered successfully. At the
  restored 80% Glow value the thumb and green fill agree. This is a launch
  check, not a second complete from-zero ASR/edit run.
- Actual Premiere Export Frame outputs, for viewing only and not imported:
  `proof/Hafez-Title-Premiere-Actual-20260905.png` and
  `proof/Hafez-Glass-Premiere-Actual-20260905.png`.

## Remaining acceptance gates — not publish-ready

1. Full transcript-versus-audio review remains. Source-drifting AI corrections
   were rejected; the system must not claim these were all professionally
   corrected or reliably translated. No colloquial rewriting is requested.
2. Review 7 exposes live Title/Body font and size; a native change to ABAR Black
   visibly changes the Persian weight. Latin glyph appearance and readability
   of the small side card still need owner acceptance. Separate text-color,
   line-spacing and tracking controls are not all exposed by this wrapper.
3. Authored exit timing must be tested for trimmed MOGRTs. Native template
   source durations are longer than the placed cue lengths. Successful import
   and a visible hold frame do not prove the ease-out survives trimming.
4. Subscribe's source comp is 3840x2160, unlike the 1920x1080 glass wrapper.
   After re-centering, the complete pill became visible, but its rendered text
   did not match the populated fields. At a readable size it cannot fit the
   tracked side region. The component is preserved DISABLED in the review
   project and the fitted plan marks it `review_blocked`, so it cannot silently
   render an incorrect CTA. Repair its AE bindings and responsive timing before
   re-enabling. The Finisher honestly reports two inserted/updated and one
   review failure; this is NOT an all-green delivery.
5. Body safety currently uses a conservative face-derived envelope over sampled
   frames and both visible cameras, not independent per-frame body tracking.
   Hero is an intentional full-frame exception that can cover the presenter.
6. Qwen Vision final QA has not run. No claim of automated final contrast,
   balance or collision approval is made.
7. CUDA runtime is unavailable to the ASR engine on this installation. CPU
   fallback works; a detected CUDA device does not mean accelerated ASR works.

The executable can be tested and this recovered project can be reviewed now;
the evidence above does not justify describing the entire product as complete
or one-click publication-ready.

Final evidence: `proof/native-saved-timeline-20260905.json` confirms Hero and
Glass enabled, Subscribe disabled; `proof/native-review-gated-result-20260905.json`
preserves the honest partial Finisher result. The separate project was saved
again after disabling the failed cue. Original media, original owner project,
Trading workflows, MetaTrader connections and credentials were not changed.

## Later publication pass — native video evidence (supersedes earlier counts)

The user clarified that manual intervention is allowed, but the desired product
is the best automatic Hafez Studio edit. The following separates automatic
engine evidence from manual publication-review changes.

- The original cached job was independently finalized without new ASR and
  without the legacy manual review override. It reached 100 percent; 89 Python
  tests passed. Its two source-gated graphic clauses were preserved, while five
  unreliable copy drafts and the failed canonical Subscribe were blocked.
- The rebuilt engine was deployed and all 1,888 build files hash-checked. See
  `proof/engine-publication-deployment-20260905.json`. This is not a second
  from-zero ASR run. CUDA ASR still uses the documented CPU fallback.
- The Premiere bridge now checks exact native control readback, required text,
  native colors and normalized layout positions before enabling a component.
  It supports per-field font/size maps. There are 25 Finisher and 12 isolated
  import regression groups. The import protocol cannot overwrite existing
  sequences or save the project implicitly.
- Glass Review 8 is a new versioned asset, not an overwrite of Review 7. It
  exposes 21 controls including separate Title/Body colors, leading, tracking
  and a responsive Duration control. Native readback confirms editable ABAR
  Black text and font-size capability on both fields.
- A complete native Premiere H.264/AAC export was produced at
  `proof/publication-job-20260905/Hafez-Director-Native-Review-20260905.mp4`:
  1920x1080, 30000/1001 fps, stereo 48 kHz, 556.322438 seconds. This is the
  actual timeline/MOGRT render, not FFmpeg-generated graphic substitutes.
- The corresponding saved separate project is
  `proof/Hafez-Publication-QA-20260905.prproj`. Its Clean Opening Director
  sequence has two enabled real Review 8 MOGRTs on V4, no PNG layer, and an
  empty/muted V3. Native evidence is in `native-clean-inspection.json`.
- Manual presentation QA selected the exact source key term `فلج تحلیلی` for
  the first card and kept the complete Community clause with a line break on
  the second. It did not silently reclassify these manual changes as a fully
  automatic headline result.
- The two first pre-dialogue islands (26 frames) were removed in an isolated
  Clean Opening artifact. Original source media and earlier outputs were kept.
  Seven artifact-consistency tests verify synchronized A/V, source in/out,
  markers, SFX, graphic provenance and SRT shifting.
- Actual exported frames at 4 fps and a 10 fps Community tail show entry,
  hold, fade-out and clean disappearance on both short MOGRTs. Native Duration
  readback is 3.193666667 and 3.466033333 seconds. This validates these two
  short cues, not every template or possible duration in the catalog.
- Local Qwen vision QA was run on two actual hold frames, as QA only. It
  returned visual PASS for contrast, balance, clipping and static overlap.
  Its first Persian OCR reading was wrong, so its text reading and any implied
  motion-safety assessment are NOT treated as reliable evidence. Correct text
  comes from native parameter readback; temporal inspection comes from the
  actual rendered frame samples.
- Subscribe Review 1 has repaired AE bindings, responsive timing and the RTL
  subtitle origin. Its new AE proof is correct, but it has not passed native
  Premiere readable safe-placement QA. Canonical Subscribe remains disabled.

### Remaining editorial findings

The 9:16 Clean Opening export is an intermediate review, not a publish-ready
master. Further inspection found aborted/repeated introductions and a phone
interruption still retained by the automatic edit. Targeted offline ASR also
recovered introductory speech absent from the saved transcript, and showed
that a cut could clip the beginning of the spoken `99`. Cached subtitle
rewrites sometimes change grammatical person or borrow subsequent speech.
Those rewrites must not be presented as verified captions. The exact repair
evidence and subsequent isolated review artifacts live under
`proof/publication-job-20260905`.

The source-only, opt-in Review 8 typography fitter adds 11 tests (100 Python
tests total). It measures the exact installed ABAR weight, preserves all words,
checks the safe-layout scale and title/body separation, verifies the asset
hash, and blocks unreadable copy. Merely promoting this fitter is insufficient:
the unmodified automatic job's long bilingual copy fails the readable fit.
Source-grounded concise term selection is a separate acceptance gate.

## Delivery Review pass — actual automatic typography (latest)

The next native Premiere export is
`proof/publication-job-20260905/Hafez-Director-Delivery-Review-20260905.mp4`.
It contains 15,260 frames at 30000/1001 fps, 509.175333 seconds (8:29),
1920x1080 H.264 with stereo 48 kHz AAC. The saved separate project remains
`proof/Hafez-Publication-QA-20260905.prproj`; select
`03 - Hafez Director Cut - Delivery Review 20260905`.

### What this version really demonstrates

- The two enabled Glass Review 8 MOGRTs now use the new engine's source-grounded
  term selection and measured typography, not the manual presentation settings
  from Clean Opening. The first English title is ANALYSIS PARALYSIS, and its
  Persian field is the literal source term `فلج تحلیلی`. The second is COMMUNITY
  with the unchanged source clause. A small local glossary selects term labels;
  it does not invent summaries, alter claims or force colloquial language.
- Native readback confirms 21 controls per clip, editable ABAR Black text/font
  and size, separate text colors, leading, tracking, glass, layout, glow and
  responsive duration. Automatic Title/Body sizes are 67/87 and 84/69. The
  actual short durations are 3.169833333 and 3.4034 seconds. First-frame SFX
  entries are frame 525 and 4611. The second was explicitly retimed one frame
  in the isolated XML to agree with the fitted graphics.
- Native application inserted two clips with zero safety failures and zero
  unsupported-control warnings. Five intentionally blocked drafts (including
  the unapproved Subscribe) remain excluded; the overall result is explicitly
  partial, not an all-green delivery. The guide track has no PNG clips.
- The main agent inspected both actual native 1080p hold frames and 4 fps
  entry/hold/exit contact sheets. Text is contained and the short cues fade
  away cleanly. This approval is for these two placements, not every asset,
  duration, camera/body pose or future input video.
- A full decode of all 15,260 frames passed. No black interval >=0.15 seconds
  was detected at the configured 98-percent-black threshold. Sample audio
  peak is -4.394795 dBFS; NaN and Infinity counts are zero. These technical
  checks do not replace full listening or editorial approval.

### Production changes and provenance boundaries

The source suite now has **123 passing Python tests**. The strict default
subtitle path accepts formatting-only changes and rejects changes to person,
negation, numbers, names or meaning. On the existing cache, 84/84 source
segments were recovered, nine formatting edits were accepted and 59 lexical
or numeric rewrites were rejected with review metadata. This is a fidelity
gate, not proof that the underlying ASR is correct. Raw captions remain draft.
The 25 Finisher and 12 isolated-import regression groups also passed again.

The isolated Review V2/Delivery Review cuts remove evidenced incomplete
opening/analysis/self-introduction takes and the failed take plus phone
interruption. Fifteen linked source frames restore the lead of the retained
spoken 99. Eleven artifact tests and inverse structural comparison verify
unchanged surviving media, A/V links and unaffected keyframes. These are
manual, source-supported publication-review cuts. They MUST NOT be described
as a newly solved general automatic retake/phone detector.

Proofs: `native-delivery-import-result.json`, `native-delivery-apply-result.json`,
`native-delivery-inspection.json`, `delivery-review-artifact-evidence.json`,
`delivery-media-qa.json` and `delivery-finisher-import-regression.log`, all under
`proof/publication-job-20260905`.

Full-video listening/content approval, draft subtitle correction, independent
body tracking (rather than the current conservative face-derived sampled
envelope), and Subscribe native QA are still outstanding. The current export
is a useful substantially cleaner review, not a claim of unattended
one-click publication readiness.

Local Qwen visual QA was repeated on `delivery-glass-hold.jpg` and
`delivery-community-hold.jpg`, with visual PASS on both. It again misread the
first Persian term; no Qwen OCR/translation or semantic approval is claimed.
Native parameter readback and source provenance remain authoritative for copy.
The rendered retake-join contact sheet around 56.5–63.5 seconds was also
inspected: no phone appears in those samples. This is not a listening test.

### Deployment of the strict/automatic typography engine

The final 123-test source build was deployed after native automatic typography
QA. All 1,888 files were hash-verified; no files were deleted. The deployed EXE
SHA-256 is `c4b6f96a520fdf293db55bff7b5a8cf7518c7f65b99bdb59716442d6ce90e59c`.
Embedded bytecode matches the checked production source modules. The canonical
and packaged catalogs were promoted with only the Glass Review 8 name and its
hash-bound runtime contract changed. The new versioned MOGRT was copied into
packaged `motion-pack/dist`; Review 7 and other assets were preserved.

Rollback backup: `backups/strict-engine-deployment-20260905-170837`.
Deployment evidence: `proof/engine-strict-publication-deployment-20260905.json`.
Doctor and help passed; ASR is still CPU fallback. This deployment did not
repack or redesign the app UI. The separate final smoke uses only an isolated
clone of the existing checkpoint and does not rerun ASR or model inference.

### Packaged SFX defect found by the final smoke

The first strict deployed smoke reached 100 percent, but its post-run audit
correctly failed: the packaged resources did not include the local sound kit.
Both active cues had `missing-curated-local-sfx` and the plan contained zero
SFX entries. The native Delivery Review video is unaffected: it references
the already-existing verified project-local sounds.

`sound_design.py` requires both original MP3 source files even when derived
WAVs exist. The scoped packaging repair therefore needs exactly the two
approved `Text Animation/Sound Effects` MP3s and four approved `Hafez Motion SFX`
WAVs, plus durable narrow package resource entries. The failed smoke is retained
unchanged as regression evidence; its 100-percent status is NOT called a pass.

Separate installer caveat: the current sound-kit loader still writes its
manifest beneath the resources tree. Today's writable personal win-unpacked
deployment can support that, but a read-only Program Files installation needs
a user-data cache or a read-only recipe path before installer readiness can be
claimed. This commercial installer work is not silently included in today's
personal video acceptance.

The exact six-file packaging repair is now deployed and recorded as six
narrow `extraResources` entries in `package.json`. No entire personal-assets
directory was added. All six source/deployed SHA-256 hashes match; no audio
was generated or downloaded for this repair. Backup:
`backups/packaged-sfx-fix-20260905-172502`. Regression:
`proof/test-packaged-curated-sfx.js` (pass). Evidence:
`proof/packaged-curated-sfx-verification-20260905.json`.

### Final deployed smoke — PASS after SFX packaging repair

`proof/strict-deployed-smoke-sfx-20260905/strict-deployed-smoke-audit.json`
records a complete unrelaxed pass against the deployed executable and packaged
catalog/assets. Normal finalize reached 100 percent in approximately 129
seconds, with all ten AI tasks from the cloned checkpoint, zero model inference
and zero new ASR. Original manifest/cache hashes remained unchanged.

The audit verified nine formatting-only edits accepted, 59 lexical corrections
rejected, 84 source segments recovered, two active measured Review 8 graphics
with editable ABAR Black typography, two exact-first-frame SFX entries in both
plan and XML A4, zero PNG timeline assets, unprocessed A1 and muted A2. Six
drafts remain blocked (five copy, one Subscribe); 140 Safe and 140 Tight SRT
cues remain draft. `publicationReady=false` is intentionally retained.

This final smoke is the automatic, untrimmed job, not the manually cleaned
8:29 Delivery Review video. It proves the installed personal runtime produces
the expected editable plan and sound assets from the recovered job; it is not
a new from-zero ASR test or full unattended Premiere publication test.

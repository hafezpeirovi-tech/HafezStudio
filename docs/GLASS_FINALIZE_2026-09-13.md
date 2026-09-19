# Glass opt-in finalizer + native entry SFX — 2026-09-13

## Scope and handoff

Continue the approved vendor Glass style; do not repeat UI, palette/template selection or the
native visual sample. Fonts remain explicitly provisional until the owner chooses at the end.
No automatic movie export, publication, downloads, Trading, credentials, database or original
AEP/media changes. Original voice is not processed. Current installed Windows app is unchanged.

**One native project for the owner:**
`proof/glass-timeline-20260913-03/Hafez-Glass-Timeline-Review.prproj`

**One current sequence:** `Hafez Glass — Automatic Timeline Review`.
The earlier 28-second `glass-pack-20260913-01` visual preview is historical template QA.
The `glass-finalize-*` folders below are file-only technical tests, not additional final projects.

## Implemented

- `run/finalize --style glass --glass-review` explicitly opts into the real engine finalizer.
  Bare `--style glass` remains blocked. `prepare --style glass` remains analysis-only.
- Existing cut/camera/punch-in logic feeds an isolated source XML, source-bound captions and
  chapter proposals into the chapter compiler, returning before legacy graphic generation,
  PNG generation, original-voice mastering or old visual-history changes.
- `glass_finalize.py` only forwards explicit CHAPTER copy/segment IDs to the strict source
  checker. It does not turn comments into titles or mark old AI text as verified.
- Routing commits last; new output folders cannot overwrite existing reviews. Resume validates
  completed Glass artifacts without calling the engine/model again. Changed review decisions
  require a new job. Stale legacy output paths are not advertised by newly generated manifests.
- Fresh chapter timestamps, XML, SRT and typed MOGRT plans share integer-frame mapping.
- `glass_audio.py` uses the existing FosLight SaaS vendor SFX_01 asset, copied unchanged into
  `personal-assets/Glass Audio/FosLight SaaS`. `config/glass-audio.json` pins its SHA and gain.
  Only this asset is read by audio conversion. No synthesis, loop, stretch or dialogue input.
- 180-frame cue = 6.006 seconds = 288288 samples at 48 kHz; stereo 24-bit PCM, -9 dB,
  smooth 350 ms tail fade. Exactly one cue per title/background composite, on A4 at first frame.
- The validator checks actual XML cue path, channel layout, timing, enabled state and lack of
  added filters against the plan; all source-frame identities, subtitle/card separation,
  camera coverage and artifact hashes are independently recomputed. Missing SFX fails closed.
- Package resource list includes the local SFX/catalog for a future build. No deployment done.

## Native project verification

The generated six-second SFX was imported and placed by native UI on existing review A4
at frame zero, ending at frame 180. Saved successfully; no unsaved marker remained.
This manual native QA step is NOT evidence that the new full CLI XML was imported automatically.

Read-only `scripts/verify_native_glass_audio.py` compared the saved project to the exact
pre-audio backup. All 153 clips on each of A1/A2/V1/V2, and one MOGRT each on V3/V4, retain
their IDs, source in/out, timeline ranges and effect graphs. A1/A2 track processing also matches.
A3/A5 are empty; A4 has exactly one matching SFX and no additional native clip processing.
Receipt: `proof/glass-timeline-20260913-03/native-audio-verification.json`.

Premiere showed a residual missing `Poppins-SemiBold` font warning when importing the WAV.
Acknowledged without installing fonts or changing global settings. Current diagnostic text
bindings remain ArialMT/Tahoma; do not infer final font readiness from metadata alone.
The SFX is available to audition; no claim of completed listening or full playback QA.

## Automated checks and real evidence

- 389 Python tests passed: `proof/glass-finalize-20260913-02/python-tests.log`.
- Node Glass bridge contract tests passed; main/preload/renderer syntax checks passed.
- New tests cover opt-in/reset, prepare and resume routing, source-copy proposals, absence of
  legacy rendering, immutable outputs, vendor hashes, exact XML SFX, shared composite audio,
  independent source/timing/coverage validation and adversarial output modifications.
- `glass-finalize-20260913-02`: actual finalizer generated 31 camera schedule sections,
  13 punch-ins, 157 SRT cues, one intro/two native-MOGRT plan layers and one vendor SFX.
  First validation failed on a path-string/Path hashing bug. Fixed and rerun via actual
  CLI resume: exit 0, completed. Its initial `finalize.log` deliberately retains the error.
- This uses existing ASR evidence and resolved review decisions, NOT fresh ASR or fresh AI.
  The old decisions contained no explicit CHAPTER proposals; only neutral intro navigation
  copy was produced. No claim of fresh semantic chapter selection. Earlier compiler proof
  separately rejected five manually authored proposals under the strict source gates.
- `scripts/verify_glass_finalizer.py` creates a new isolated proof, hashes the original input
  manifest/review, and records the actual process exit code. Never rerun onto an existing folder.
- Clean full rerun in `proof/glass-finalize-20260913-03` completed successfully with exit 0,
  after the routing/path fixes. `cli-receipt.json` confirms original manifest/review unchanged,
  no new ASR/AI request and no native import. Its `finalize.log` has the actual completion event.
  Counts remain 31 camera sections, 13 punch-ins, 157 subtitle cues, two MOGRT layers planned,
  one native-vendor entry SFX and zero PNG timeline graphics. All advertised output files exist.
  This is the latest engine proof; the single owner-facing Premiere project above remains current.

## Usage

```text
python engine/src/hermes_video/studio_cli.py finalize
  --manifest <NEW-job.edit.json> --review <source-bound-review.json>
  --style glass --glass-review --performance balanced
```

For a completed Glass manifest, omit `--review` to validate/resume without regeneration.
The output `.prproj` path in the plan is an intended native target, NOT a created project.
Never report that XML alone contains editable MOGRT instances; the native finisher must import
the XML once, bind the exact project/sequence ID and apply the typed plan.

## Remaining, in order

1. Generate fresh source-bound semantic chapter proposals and review speech evidence where
   needed; never weaken gates or reword unreliable text simply to add decorative cards.
2. Wire opt-in Glass review through the desktop orchestration/native finisher; test a fresh
   two-camera job in a separate project, then build/deploy a candidate Windows app.
3. Choose local music (asked once; no response yet). SFX_01 is an effect, not approved music.
   Music-only ducking is not exercised while music is absent. Audition/approve SFX variants.
4. Import captions as a native caption track; automate and verify native compositing/timing.
5. Source-bound infographics and full-interval safe placement for overlays; Glass subscribe
   choice remains unselected. The fullscreen intro does not certify those capabilities.
6. At the end choose fonts, verify native rendering, then full human review before final export.

Backup before this work: `backups/glass-finalize-audio-20260913-01`, including the exact native
project before audio. No original asset was deleted or replaced.

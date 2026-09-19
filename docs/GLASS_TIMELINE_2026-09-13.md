# Glass timeline integration — 2026-09-13

## State and user choice

The owner accepted the prior Glass visual sample; final Persian/English fonts are
explicitly deferred. Do not restart template/style selection or redesign Director UI.
This milestone adds a working isolated timeline compiler, not a deployed one-click Glass app.
No final movie was exported or published. Trading, original media/AEP and old projects are unchanged.

Later same-day continuation: `GLASS_FINALIZE_2026-09-13.md` adds opt-in real CLI finalization,
vendor entry audio and 389 passing tests. The current native review now has one SFX on A4.
The historical implementation/next-step details below describe the earlier compiler milestone.

## Current review

- Project: `proof/glass-timeline-20260913-03/Hafez-Glass-Timeline-Review.prproj`
- Only current review sequence: `Hafez Glass — Automatic Timeline Review`
- Native sequence ID: `c46cc85f-2920-47c9-abd7-cc5d3c9ce65b`
- Compiled XML: `Glass-Director.xml`; aligned subtitle sidecar: `Glass-Director.srt`.
- Typed plan: `Glass-Director.premiere-plan.json` (bound to exact imported sequence ID).
- Source: existing completed two-camera edit in `proof/final-editorial-spoken-trigger-20260912-03/finalize`.
- Input timeline 16463 frames; output 16643 frames at 30000/1001.
- Intro occupies [0,180); original picture/dialogue starts at frame 180 (6.006 seconds).
- Two actual native MOGRTs: Qss SaaS Gradient Background 01 and FosLight SaaS Pack Title 01.
- 12 typed bindings read back; ArialMT/Tahoma provisional, Glow Radius 200, title Motion scale 65.
- One shared smoked-emerald palette. No PNG timeline graphic, no fake metric, no Grunge fallback.
- `import.result.json`, `apply.result.json`, `inspect.result.json` contain the real native receipts.
- Subtitle sidecar has 157 cues; it is NOT yet imported as a Premiere caption track.
- Saved native SFX on A4 [0,180), verified against pre-audio backup: V1/V2/A1/A2 each
  retain all 153 clips and their source in/out, timing and effect graphs. V3/V4 unchanged.
  See `native-audio-verification.json`; full playback/listening review remains.

The opening copy is explicitly a neutral navigation label (HAFEZ STUDIO / شروع ویدیو),
not a content-specific title inferred from speech. It still needs editorial copy approval.

## Implemented

`chapter_timeline.py` provides strict integer-frame half-open insertion mapping shared by
camera clips, dialogue, subtitles, camera schedule, punch-in intervals and markers.
An independent per-frame source-identity assertion verified all 16463 frames of each of
V1/V2/A1/A2. Retiming, overlapping sources, transitions and processed dialogue are rejected.
Static equal-value Basic Motion can split safely; animated picture clips cannot be split.
Caption cues may not straddle chapter gaps. Old additional tracks are omitted only in the new
compiled sequence; original source XML/plan/media are preserved.

`glass_assembly.py` verifies fresh source content SHA, exact XML frame clock and A1 source path.
All raw acoustic words block unsafe insertion points, including uncertain ASR words.
Trusted copy requires literal contiguous source words, unique ownership, intact source coverage,
evidence identity and sufficient confidence. Quotes are not paraphrased or colloquialized.

Five chapter requests were manually authored as bounded test proposals, not produced by a fresh
AI run. The rule engine rejected all five: non-sentence partition, unreliable/removed words,
or no shared picture/speech/caption-safe gap. The accepted intro is not evidence that mid-video
semantic chapter selection is complete. Never loosen source gates simply to fill the timeline.
Rejections are recorded in `assembly-report.json`.

Glass planning/review prompts now consume actual local candidate IDs/capabilities instead of
legacy Hermes templates. `prepare --style glass` is enabled for analysis/planning only.
Ordinary `run/finalize --style glass` still stops early; no silent legacy-style fallback.
Explicit `--glass-review` now enables an isolated real finalize path; see the later handoff.

## Reusable command

From the project root with the authorized engine environment:

```text
python engine/src/hermes_video/studio_cli.py glass-assemble
  --manifest <completed.edit.json> --xml <completed.xml>
  --base-plan <completed.premiere-plan.json> --captions <completed.tight.srt>
  --chapters <source-bound-proposals.json>
  --output <NEW-isolated-directory> --project <NEW-isolated-directory/review.prproj>
```

The output directory must not exist. The command creates XML, SRT, typed MOGRT plan and a
machine-readable report, but never invokes Premiere, overwrites input or exports a movie.
Create the separate project, import the XML once, bind the returned sequence ID, then apply
the plan. `scripts/glass_native_request.ps1 -Target timeline` is intentionally restricted to
this exact native proof folder/project and refuses uncertain or duplicate requests.

## Verification and backup

- 377 Python tests passed; log: `proof/glass-timeline-20260913-03/python-tests.log`.
- Node Glass bridge contract tests passed (typed controls, locks, ownership, duplicates).
- The stricter source/ownership/subtitle validators were also run on the actual completed edit.
- Native import/apply/inspect succeeded: 2 inserted, 0 failed, 0 disabled, no duplicate imports.
- Final native visual spot-check: at 00;00;03;00 the Persian title and soft glow are visible
  over the smoked-green gradient; at 00;00;07;00 the original camera picture is visible.
  Premiere renders asynchronously after seeking: an immediate stale monitor image is not a
  missing-title failure. These spot-checks do not constitute full playback/audio QA.
- Saved the separate current review project in Premiere; the unsaved marker cleared. Older
  review projects were not overwritten. No final video export was started.
- Composite in Linear Color was unchecked for this isolated new sequence, matching the approved
  sample. This is still a manual native step, NOT automatic enforcement by the bridge.
- Backup before changes: `backups/glass-timeline-20260913-02` (scoped source originals).
- `proof/glass-timeline-20260913-02` is the earlier file-only compiler pass; no Premiere project
  was created there. Keep it as evidence, not another final sequence.

## Next, without redoing completed work

1. Source-bound semantic chapter proposals and listening review. Investigate why candidate words
   are uncertain/removed; do not stamp them trusted. Add safe interior chapters only with evidence.
2. Bind the compiler into normal run/finalize and one clear user-review project. Current packaged
   app/engine is unchanged; source improvements alone do not enable automatic Glass in release.
3. Local curated music/SFX, synced entrances, music-only ducking, caption-track import and native
   timing/compositing automation. None are newly present in this intro proof.
4. Safe full-interval placement for actual overlays, source-grounded infographics, Glass subscribe
   choice. The intro is fullscreen before camera and does not certify overlay tracking.
5. At the end, owner font choice and actual native render verification; no new font downloads yet.
6. Fresh full automatic two-camera run and packaged-app QA. User reviews before final movie export.

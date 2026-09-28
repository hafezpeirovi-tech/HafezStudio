# Editorial Glass: current-source binding checkpoint

Status: **one reusable module compiled and verified in native Premiere**, not a completed automatic edit or an installed-app release.

## Implemented

- `engine/src/hermes_video/editorial_source.py` validates one existing, reviewed semantic cue and maps its frame interval through every primary-camera cut using A1's video-bearing source references. It rejects gaps, overlaps, transitions, retimed/filtered/disabled clips and mixed frame rates rather than inventing a mapping.
- `scripts/compile_editorial_intro.py` renders only a silent portrait insert, compiles the existing native AE template with that media and heading, enables editable font controls, and emits a one-cue Premiere plan plus a separate-project request. It does not dispatch that request or modify the installed app.
- `scripts/editorial_source_export.jsx` preserves unrelated/unsaved AE projects, exports into a new folder, re-resolves the composition after MOGRT export, and hides an empty optional Topic panel. Adding Topic Label text later restores its animation.
- Premiere XML media URLs use `file://localhost/C%3A/...`; the plain three-slash drive form caused a real Link Media failure and now has a regression test.
- Source files and selected media are hashed before/after compilation. Existing edits, dialogue processing and duration are retained. No pauses or flattened title PNGs are inserted.

## Verified local artifact

Relative to the HafezStudio project root:

`proof/editorial-source-bound-20260928-03/`

- `Hafez-FX-Source-Bound-Review.prproj`: saved separate Premiere project.
- `Editorial-Editable.mogrt`: native editable graphic, not a rendered video substitute.
- `Editorial-Preview.mp4`: **silent six-second AE QA preview**, not a full-video export.
- `Editorial-Preview.png`: actual rendered preview frame.
- `Editorial-Source.aep`: source-bound AE project.
- `recipe.json`, `ae-receipt.json`, `native-receipt.json`, `native-inspect.json`: traceable preparation/export/insertion/readback evidence.
- `Editorial-Review.plan.json` and `Glass-Native-Bound.plan.json`: prepared and exact-native-sequence-bound plans.

Job `Editorial-069ca4a8d618` uses the current C3009 camera media, not the older module demonstration footage. Cue `glass-semantic-0` displays **بهترین استراتژی** and brand **HAFEZ-FX**. The existing recorded spelling correction is retained; this milestone did not re-transcribe or independently approve all speech.

Native timing: frames **221–401** at **30000/1001 fps**, seconds **7.374033–13.380033**. The portrait spans two source edits: source frame 1008 for 110 frames, then source frame 1543 for 70 frames. Existing primary dialogue remains below it; the portrait asset has no audio.

Native Finisher: inserted 1, imported 1, textUpdated 1, failed 0, disabled 0, safetyFailures 0. Nineteen typed controls were verified during insertion. Native inspection found one enabled MOGRT on **V4**, a real Graphic Parameters component and **20 exposed controls** including media replacement. The six text controls expose font and font-size editing. Title readback is `AbarHighFaNum-ExtraBold`, size 102; line spacing is 132. Colors, panel opacity, title scale and portrait zoom are exposed.

Visual QA in Premiere at **00:00:09:15** confirmed the current white-shirt portrait, clear title on the left, HAFEZ-FX branding, no empty Topic pill and no heavy text-glow halo. Existing subtitle text remains underneath and still needs editorial correction; it was intentionally not silently rewritten. The test project was saved at this review position.

## Verification

- 8 editorial Python test methods passed, including rejection subcases and URL regression.
- 73 existing Glass Python test methods passed.
- `glass_finisher_test.cjs`, `glass_panel_test.cjs`, `glass_bridge_test.cjs` passed.
- All **594 XML clip items** retain start/end/in/out/enabled/filter values from the input edit.
- Copied SRT is byte-identical to its input.
- Native MOGRT enabled state, exact cue timing, ABAR title/text/size editing and 20 controls were verified from Premiere, not inferred from unit tests.
- Short preview decoded successfully with FFmpeg.

## Explicit limitations / next implementation

1. **The installed Hafez Studio editing button does not yet call this compiler.** `app_routing_enabled` and `publication_ready` remain false. Do not announce a completed automatic editing release.
2. This QA sequence retains the complete original camera/audio edit but inserts **only this single graphics cue**. Other graphics, including the older six-second opening gap, are not supplied by this isolated test. It is not the final watch-through/export sequence.
3. The verified template duration is approximately six seconds only. Other durations fail closed until responsive-duration behavior is tested.
4. The compiler selects the primary camera intentionally; it does not reproduce the alternate-camera or existing punch-in appearance inside the portrait card. It does not yet track portrait cropping over arbitrary new footage.
5. Short headings are limited to six words/90 characters. Readability of every arbitrary heading is not automatically proven by splitting text. Full text review, subtitles, numbered problems, lists/comparisons/charts and CTA variants remain separate work.
6. Native media replacement is exposed, but scripted replacement is not assumed reliable: this implementation binds current media in AE before export. AE remains a local dependency for compilation.
7. Next: add an explicit compiled-asset contract to the Glass pipeline, route verified editorial cues through this compiler, preserve other approved template families, then test a complete new job before updating the existing app build. Do not replace all roles with this one title.

## Reproduction and preservation

Requires local licensed template prerequisites under `motion-pack/modules/01-editorial-intro/`: `Hafez-FX-Editorial-Intro-v3.aep` and `Hafez-FX Editorial Intro v4.mogrt`, their media dependencies, ABAR fonts, installed Adobe After Effects/Premiere, and bundled FFmpeg. These binaries/media are not redistributed in the source-code commit.

Run from the HafezStudio root with the existing approved Glass plan/XML/report and a **new** output folder:

```powershell
python scripts/compile_editorial_intro.py compile --plan <plan.json> --xml <edit.xml> --report <assembly-report.json> --cue <reviewed-cue-id> --output <new-output-folder> --preview
```

AE must be empty or have the clean saved module source open. The compiler refuses to close a different/unsaved project. Native execution has a bounded 15-minute wait; inspect a timed-out job before retrying. `prepare` and `finish` are also available for explicit native-stage control. Dispatch `premiere-request.json` only through the existing guarded Finisher, with a live heartbeat and empty queue. No final movie export is requested.

Pre-change backup: `backups/editorial-source-binding-20260928-01`. Failed test folders `...-01` and `...-02` are retained for diagnosis and are **not** the deliverable. Existing module work and unrelated files were preserved. Upscale, Trading, Hermes services, credentials and databases were not modified.

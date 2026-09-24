# Automatic Glass engine — tested checkpoint, not native-release approval

Update: a desktop candidate now bundles this engine. See
`GLASS_DESKTOP_2026-09-23.md` for packaged verification and legacy style migration.
The installed release remains unchanged; native Premiere approval is still pending.

## Scope and owner instruction

Owner's latest instruction: work on the engine only. Do not touch the currently
open Premiere project, which contains new unsaved Bear for Site edits. No native
input, save, import, or export was performed in this update. A read-only window
inspection preceded that instruction.

## Current executable

`engine/semantic-candidate-20260923-02/dist/hermes-engine/hermes-engine.exe`

SHA256: `E3B0DC7F24729528B643EF12F77FEB47E286F5A59FBF10547F59DD79EEE2CE9D`

Source hashes verified unchanged during this build are saved in
`engine/semantic-candidate-20260923-02/source-hashes.json`.
Revision 01 is superseded (source was still changing during that earlier build).
Neither candidate replaces the installed release. Do not run the exe with no
arguments as if it were the desktop app. Existing desktop engine selection
supports a process-local `HERMES_ENGINE_EXE` override for later supervised testing.

## Implemented and exercised

- Local AI selects IDs from a literal phrase menu derived from the actual
  transcript. It cannot supply alternate copy, asset paths, timestamps or fonts.
- A separate contextual review checks meaning, importance and spelling. Model
  judgments are fallible and do not constitute publication approval.
- Authoritative retained word evidence, confidence, source identity and timeline
  mapping gate each selected title. Removed, ambiguous and low-confidence words
  cannot become timed graphics. Density and chapter-intersection checks apply.
- Important text is now compiled, not merely written to a report: approved
  FosLight Trendy over Qss Gradient, fullscreen voice-continuous cutaways.
  These are NOT face-safe transparent overlays; no body-tracking claim is made.
- Existing chapter/intro path remains FosLight SaaS over Qss Gradient. Three
  vendor families, one smoked-emerald palette, ABAR ExtraBold/SemiBold throughout.
- Explicit spelling-only display correction `استراتیجی → استراتژی` records the
  original quote separately. No colloquial rewrite or invented claims.
- One vendor SFX at each composite's first frame. Source dialogue is unchanged.
  No new pauses for important-text cutaways; existing standalone intro is retained.
- Normal Glass finalizer calls the AI review and card compiler. CLI glass-assemble
  also accepts --storyboard for reproducible engine-only tests.
- Progress messages during local selection/review replace an opaque long stage.

## Actual real-video result

Authoritative compiled-engine package:
`proof/automatic-semantic-glass-20260923-05/frozen-package`

Source version is the existing September 22 analysis / isolated glass-source XML,
NOT the owner's newly edited live Premiere timeline. Never import it over that edit.

| Timeline seconds | Editable title |
| --- | --- |
| 7.374 | بهترین استراتژی |
| 220.787 | احتمالات |
| 292.626 | دیتا |
| 393.593 | تکنولوژی |
| 431.364 | ریاضی و احتمالات |

Plus neutral intro: 6 composites, 12 planned real vendor MOGRT layers, 6 actual
frame-synchronized SFX clips in XML, 142 subtitle cues, 26 camera shots and
11 punch-ins; zero PNG timeline assets. Original source preservation verified.
There is NO newly created .prproj in this package yet. XML alone does not insert
MOGRT: the existing Finisher must consume Glass-Director.premiere-plan.json.

AI report: `proof/automatic-semantic-glass-20260923-05/gemma4-12b.report.json`.
15 contextual proposals, 5 compiled, 10 rejected by acoustic/density rules.
One model response contained an invalid candidate ID; it was not used. This is
partial editorial coverage, not proof that every important moment was found.
Earlier experiments 01–04 are not approved delivery packages.

## Verification and remaining work

- 432 Python tests passed; four Node Glass bridge/desktop/finisher/panel test files passed.
- Both required ABAR font files and their internal family/weight metadata verified.
- Frozen exe actually ran glass-assemble on real media evidence and vendor assets,
  generated the above result, and returned publicationReady=false.
- Native Premiere import, parameter readback, complete animation/RTL/layout QA,
  and candidate desktop deployment are still pending; owner currently disallows
  Premiere work. Do not claim app finalized or these new MOGRTs already on timeline.
- Dedicated table/chart/metric/subscribe routing is not completed by this title
  compiler. Unsupported or data-insufficient roles remain blocked, not faked.
- Body-safe transparent overlays, Glass subscribe choice, and music choice remain
  separate work. No final movie export is authorized or necessary.

Backup before this engine work: `backups/glass-semantic-routing-20260923-01`.
Trading, credentials, database, original Premiere files and UI design unchanged.

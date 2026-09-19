# Glass editorial continuation — 2026-09-13

## Superseding owner decision — 2026-09-14

The owner rejected globally longer pauses for YouTube pacing. The 600/350ms initial
Glass silence policy described at the end of this document is RETIRED, not active.
Source `build_initial_timeline` again delegates exactly to the original 200/200ms
planner for every style. Candidate02 and the current native project never received
that experiment and are unchanged. Experimental module/proofs remain historical only.
Future word-boundary work must be targeted; no blanket handle increase or timing-gate
relaxation. Backup before this reversal: `backups/glass-restore-pacing-20260914-01`.

Verified: 417 regression tests passed. On the prior real detector ranges, the active
Glass planner exactly reproduces all 129 clips for EACH camera, the source-word
mapping and 16,720-frame initial duration: zero added frames. Receipt:
`proof/glass-restore-pacing-20260914-01/verification.json`. No ASR rerun or native
project mutation occurred; current project SHA256 remains
`8c5eea2808674f698ca630053accc2149e664d08b7967719a21817598020e67e`.
Targeted word repair remains unimplemented; do not claim that reverting padding fixes it.

Continues GLASS_DESKTOP without repeating the approved intro/native broker work.
Scope: HafezStudio only. No Trading, database, credentials, original camera media or AEP changes.
Fonts remain provisional. No automatic final movie export or publication.

## Implemented

- `glass_editorial.py` creates source-literal proposals from explicit topic transitions,
  named features and named concepts; no fixed-time chapters or title paraphrasing.
- `glass_assembly.py` merges these with editor proposals, then retains the existing strict
  retained-word confidence, original-source identity, sentence boundary, acoustic occupancy,
  subtitle and shared-picture-gap checks. Rules propose; they do not authorize unsafe insertion.
- Unverified English translations remain in the audit only. A Persian-only content title is
  displayed once, not duplicated in both template text fields. The bilingual neutral intro is unchanged.
- Metric/comparison/important-word/subscribe suggestions are explicitly review-only, not inserted
  until the corresponding native layout/number/placement checks pass. No Grunge subscribe substitute.
- New outputs beside future Glass XML: `editorial-candidates.json`, `EDITORIAL_REVIEW_FA.md`.
  Original-camera source start/end are the stable lookup clocks. See the clock-label erratum below.
- The local Glass model prompt now explicitly requests CHAPTER and a 1–6 word literal `quote_fa`.
  It no longer relies on the generic GRAPHIC example/6–18-word clause instruction for chapter labels.
  Transcript is data, not instructions. Non-Glass local prompt behavior remains unchanged.
- Glass local-response fingerprints include the effective prompt, preventing stale generic answers
  from being reused after the contract changed.

## Evidence / scope of tests

Backups: `backups/glass-editorial-20260913-01` (pre-change glass_assembly, glass_finalize,
subtitle_pipeline). New files were created via patches. Original release/candidate not overwritten.

Read-only audit of prior source evidence found three real topic proposals: all were rejected by
unchanged safety checks (one unsafe shared gap; two unreliable/removed source-word cases).
That audit was NOT fresh ASR and was NOT evidence of successful chapter insertion.

Full regression passed 404 tests before the final cache-fingerprint test; the 16-test editorial
suite including that cache regression subsequently passed. Final full-suite count recorded below.

## Fresh acceptance job

`proof/glass-fresh-asr-20260913-01` is an independent real prepare job from the same owner-selected
two camera files, not a clone of previous ASR. `scripts/prepare_glass_fresh.cjs` runs the actual
packaged engine, local model, balanced CPU profile, no network inference/downloads/Premiere mutation.
Intent and stdout/stderr/exit status are persisted. Do not rerun/overwrite that directory.

`scripts/finish_glass_fresh.cjs` continues only a successful fresh prepare, backs up its manifest,
then runs the updated source engine with fresh local Qwen review and the new Glass rules.
It does not reuse an older review response, dispatch to Premiere or export a movie.

At document creation the fresh prepare was still running. No completion or editorial-quality
approval is implied by this checkpoint. Final outcome and current review pointer are recorded below.

## Completed acceptance outcome

- Final full regression: **405 tests passed**. Candidate02 built independently and verified;
  original release, candidate01 and desktop shortcut retained. Candidate02 contains the new
  editorial rules and local prompt contract. Its packaged doctor/status/plan QA passed, including
  hashes for 114 MOGRTs in seven available families. Selection is still capped at four core families.
- Fresh ASR actually ran from the owner's two camera originals: 1,353 mapped words, 86 review
  segments; seven recovery windows, five machine recoveries accepted and two rejected. This
  is not a speech-accuracy approval: lexical errors still exist. No new model/asset download.
- Updated source-engine finalization used local Qwen, not cloud inference: nine of ten task
  responses valid, one deterministic fallback. Subtitle fidelity guard accepted 64 formatting-only
  changes and rejected 22 rewrites. 159 draft caption cues, 31 camera shots and 13 punch-ins.
- Eleven content chapter proposals all failed the unchanged source/timing gates. Zero content
  chapters inserted. Nine additional graphic ideas remain review-only. The sole insertion is the
  neutral six-second intro: two real editable vendor MOGRT layers and one vendor SFX, no music/PNG.
- Same Electron native broker dispatched this fresh package once and Premiere saved it successfully:
  `proof/glass-fresh-asr-20260913-01/F_Hafez_Youtube_8rdvid_C2963.glass-review/Hafez-Glass-Review.prproj`.
  Single sequence: `Hafez Glass — Automatic Timeline Review`, ID `1a75660f-a9ea-4f5f-8bad-c2c18488ed33`,
  16,853 frames at 30000/1001 (~9:22). Native receipt includes successful typed MOGRT controls.
- Independent saved-project verification matched all 151 edits on each camera/voice track to XML,
  all 159 caption texts exactly to SRT, display quantization <1 frame, intro/SFX frames0–180.
  A1 timing unchanged, A2 muted in Premiere; no final movie export. This is structural QA, not a
  claim of full listening/playback or publication readiness.
- Fresh prepare used candidate01's packaged prepare path; finalization used updated source; native
  dispatch used the shared Electron broker. Candidate02's entire UI-to-raw-to-native path has NOT
  been run as one uninterrupted packaged-app job. Do not describe it as such.

## Known clock-label erratum

`glass_editorial.review_markdown` in candidate02 calls each proposal's `segment.start`
"timeline" before cards; it is actually the initial analysis clock, before retake edits, NOT the
final Director/Premiere clock. Original-camera `source_start`/`source_end` remain correct.
The fresh review Markdown header was corrected explicitly. Source renderer wording is now fixed
and tested; candidate02 remains unchanged. Include that fix in the next engine build;
do not use these proposal timeline numbers for automatic placement. The actual
placement/ASR/SRT source mapping remains separate and passed its checks. Candidate02 was not
silently altered after verification just for this documentation fix.

## Remaining production work

ASR lexical quality and owner-listened source text are still the main editorial limitation. Do not
rerun the same full ASR merely to hope for different words; compare a bounded source excerpt first.
Then validate literal topic titles and safe insertion gaps. Numbers/infographics/subscribe require
their own content and placement validation before insertion. Fonts are provisional; Poppins-SemiBold
missing-font warning was acknowledged without installing fonts. Native compositing visual review
is separate from a successful save. No automatic export/publication is authorized.

## Saved visual-review adjustment

Native preview at00;00;03;00 showed stepped glow with `Composite in Linear Color` enabled.
After backing up the newly saved project to
`backups/glass-editorial-20260913-01/fresh-native-before-compositing.prproj`, the computer-use skill
was used to disable that checkbox in THIS new sequence only. At the same frame the glow became
soft; the project was saved with no unsaved marker. This is a manual native QA adjustment, NOT an
automated engine/broker feature. No other project or source media was edited.

Post-adjustment independent XML/SRT/native verification passed again and was written separately
as `saved-native-post-compositing.json`, preserving the first receipt. Current project SHA256:
`8c5eea2808674f698ca630053accc2149e664d08b7967719a21817598020e67e`.
Premiere is left showing the new project at the intro sample frame. Full playback/listening remains
unverified; successful native save alone is not publication approval.

## Subsequent speech-boundary work (source only)

See `GLASS_SPEECH_PADDING_2026-09-13_FA.md`. Three bounded excerpts decoded in both CPU int8
and float32 produced identical wording; increased compute precision did not fix those lexical errors.
No source text changed and no model downloaded. Fresh silence detection reproduced all 129 initial
keeps exactly, then a conservative 600ms head /350ms tail policy with frame-exact union was measured.
Initial duration:557.891->618.618s; partial machine-word coverage:122->40, 83 prior partial words fully
covered, no prior full-word regressions; one previously absent word now partial. All prior source frames
remain, none duplicated. Two real before/after video pairs were made, not a final movie export.

Only NEW Glass Prepare in source uses this policy; existing projects/finalization and other styles
are unchanged. This is initial silence planning, not retroactive ASR-authorized restoration or loosening
chapter gates. The existing independent audio-review boundary contract remains unchanged.416 tests pass.
Source and old project hashes/receipts are retained. No source-code packaging change to candidate02,
no fresh full ASR-to-native rerun, no listening approval, no newly inserted content chapters this stage.

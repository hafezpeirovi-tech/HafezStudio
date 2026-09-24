# Current Glass recovery — 2026-09-23

Latest checkpoint supersedes status below: [GLASS_ENGINE_2026-09-23.md](GLASS_ENGINE_2026-09-23.md).
Owner now requests engine-only work; do not touch the live Premiere project.

## Owner contract (not a completion claim)

- Deliver the automatic editor using the owner's existing Envato Glass MOGRTs, not PNGs or the rejected internal Hermes Glass template.
- Chapters: FosLight SaaS Text Animation Pack over Qss SaaS Gradient Backgrounds, before camera footage. Important words: FosLight Trendy Titles. Data graphics: motionstate Liquid Glass, only with grounded data and verified placement.
- Optional alternatives, not extra simultaneous families: Nitrozme SaaS, Vio Elegant Infographics, Melkor Number Counter. Maximum four families per video.
- One smoked-emerald palette throughout, editable exposed vendor text/color/font/size controls. Owner now requires ABAR High FaNum. Do not change template design or download unapproved visual assets. Local AI model/tool downloads are explicitly authorized.
- Do not add global speech padding. Source audio preserved. No final movie export/publication. No Grunge substitution; Glass subscribe and music are not selected.
- Current source job: Videos/Hafez Studio Outputs/20260922-115656-C3009-EUL9E, C3009/C2974. Do not redo ASR.

## What actually happened this turn

- Official local SENSITIVE_READ and HERMES_CONFIG_WRITE checks passed.
- Read the latest Glass desktop/editorial/pacing handoffs and current compiler/broker.
- Added `scripts/resume_existing_glass.py`: requires existing review and speech evidence, copies both inputs to an isolated backup, remaps outputs to a new proof directory, runs existing finalizer, checks original hashes. No native dispatch or export.
- Actual run completed in `proof/c3009-vendor-glass-20260923-01`; receipt confirms original input hashes unchanged and exit 0. Existing review reused; no new ASR. Camera motion generation did run.
- Result is ONLY a neutral intro: two vendor MOGRT layers, one vendor SFX, 142 draft captions, zero PNGs. No content chapters. NOT a final deliverable, and NOT dispatched to Premiere. No new prproj exists there.
- The actual editorial candidates file had zero chapters. Added recognition of explicit numbered-topic labels such as “مشکل شماره‌ی دو، نداشتن دیتا”. This generates the literal proposal “نداشتن دیتا” on segment 39; it is NOT an approved placement. All downstream acoustic/source/safe-gap checks unchanged. No rerun after this source patch.
- Backup of edited source/test: `backups/glass-editorial-20260923-01`.
- 18 editorial tests passed (model calls in those tests are mocked). Three Node test files passed: Glass bridge, desktop orchestration, finisher. No full-suite run this turn.

## Blocking target ambiguity — ask owner, do not overwrite

Premiere is currently open on `D:\Premiere Proj\Me Youtube 9.prproj` with an unsaved `*` and sequence duration about 6:58, different from the supplied September 22 automatic output (~7:49). Another project is open too. Only activated Premiere and its Hafez Finisher tab. No save, import, insertion, or project close performed.

An asynchronous question asked whether to use the currently manually edited Premiere version or the September 22 automatic output. Await that choice before native placement. Never assume the old XML preserves current manual edits. If current project is chosen, save a separate scoped copy preserving unsaved edits and map MOGRTs to its actual source/timeline clocks.

## Remaining

1. Resolve target edit above; avoid regenerating the wrong timeline.
2. Complete content routing (not only intro), source-faithful title copy and verified placement; never mark collision-free merely to bypass checks.
3. Native broker insertion/typed readback and visual animation QA in a separate project.
4. Deploy the correct executable path only after verification; default release is older than Glass candidate02. Source improvements are not yet in candidate02.
5. One clearly identified review project/sequence for owner; no automatic export, no claim of finished automatic editing until real content MOGRTs work.

## Later update — automatic semantic / ABAR work

The target ambiguity above was resolved: owner chose a COPY of the current project.
See `proof/current-project-glass-20260923-01/Me-Youtube-9-Glass-Review.prproj`.
Six vendor layers were previously inserted into that copy; this is a manual integration proof,
NOT evidence that the desktop automatic workflow is complete. Its older text fonts remain
to be verified/replaced with ABAR. Preserve the owner's original project and manual cuts.

- Source backup: `backups/automatic-semantic-abar-20260923-01`.
- Glass plan construction and validation now reject non-ABAR text fonts.
- Automatic SaaS chapter builder keeps Persian text in its second animated phase instead
  of leaving it blank; uses ABAR ExtraBold/SemiBold.
- New `glass_storyboard.py` validates AI proposals against original source segments,
  discards AI paths/timestamps, reports rejects, and keeps native approval false.
  Local review supports model-specific checkpoints. This is NOT yet the nonchapter
  native layout/placement compiler. Finalizer currently records semantic proposals only.
- 67 Glass unit tests passed (mock model tests are not native/render certification).
- Official model research followed by successful download of Ollama `gemma4:12b`.
  Existing `qwen3.5:9b-q4_K_M` and Gemma were actually run on the same first 12 original
  review segments; receipts: `proof/local-model-comparison-20260923-01`.
  Qwen: 13.58s, two invalid field-type proposals, zero source-validator passes.
  Gemma: 64.06s, one source-validator pass, one noncontiguous rejection.
  IMPORTANT: Gemma's passing quote is still semantically incomplete. Source matching
  alone is NOT meaning validation and does NOT authorize rendering this proposal.
  Neither model was promoted to production based on this small sample.
- Explicit JSON field types added after this experiment; repeat comparison in
  `proof/local-model-comparison-20260923-02`. Inspect receipts for completed results.
- No binary deployment, new native Premiere insertion, or final export in this update.

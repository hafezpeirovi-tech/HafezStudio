# Runtime finalization — verified engine, native graphics QA in progress

This checkpoint supersedes the deployment and native-access sections of
`FINALIZATION_CONTINUATION_2026-09-05.md`. It does not certify publication readiness.

## Installed application

- The actual portable engine was replaced with the tested complete candidate
  tree, not just its EXE. All 1,888 files matched after a fresh deployed-EXE smoke.
- New EXE SHA-256:
  `1f46c319f3c871ae9552c666bfad691fb52602604be536774323f4a09f02613c`.
- Full prior tree remains in both
  `backups/caption-engine-deployment-20260905-192146/engine-before` and
  `release/win-unpacked/resources/engine/hermes-engine.before-caption-20260905-192146`.
- Source suite: 179 passing tests; caption validator: six passing self-tests.
- Actual deployed help, doctor and isolated cached finalize passed. Finalize
  reached 100%; independent caption validation passed. Safe/Tight each contain
  140 ordered, positive, nonoverlapping cues, with numeric fragments preserved.
- The cached test did not rerun ASR or language generation; it did perform local
  face inference. A separate fresh-input prepare test subsequently passed in
  51.90 seconds using two real 12.012-second source excerpts and local CPU-int8
  Whisper. It generated 39 new raw words and 39 uniquely mapped words under a
  new run UUID, without ASR cache reuse, downloads or a review-model call.
  PCM hashes match the original selected audio windows. Two partially clipped
  words retained their complete acoustic bounds; the four/five-frame gaps stayed
  review-required, with zero restored frames. This verifies evidence capture,
  not lexical accuracy or an approved cut repair. Evidence:
  `proof/fresh-prepare-word-evidence-20260905/validation.json`.
- Hafez Studio was reopened normally from `release/win-unpacked/Hafez Studio.exe`.
  Native UI shows Engine/ASR, AE and Premiere ready, zero selected sources and
  no active job. The glow slider was visually consistent at 80% after reopening.
- GPU remains an explicitly reported CPU fallback; this is not verified CUDA ASR.
- The packaging source `engine/dist/hermes-engine` was also synchronized to the
  same approved candidate. All 1,888 files matched, staging `--help` passed,
  and all live-release hashes stayed unchanged. Both previous-staging copies
  are outside `engine/dist`, so the packaging wildcard cannot include them.
  This prevents the next pack from silently reintroducing the old engine.
  Evidence: `proof/caption-engine-staging-sync-20260905/sync-result.json`.
  Reversible backup/retained copies:
  `backups/caption-engine-staging-sync-20260905-201132-758/`.

Evidence: `proof/caption-engine-deployment-20260905/DEPLOYMENT_RESULT.md`,
`deployment-verification.json`, `caption-validation.json` and `smoke/`.

## Real native Subscribe test

The owned Premiere project is `proof/Hafez-Publication-QA-20260905.prproj`.
A new ten-second sequence, **Hafez Subscribe Defaults Native QA - 20260905**,
was imported into a unique bin. It contains real source video/original A1 and
one actual AE-derived MOGRT on V4. It does not replace the Delivery Review.

The Defaults Candidate was installed using Premiere's native graphics-template
import and dragged onto frame 60. Its untouched defaults were inspected:
25 controls, three editable Unicode texts and enabled font/size capabilities.
The initial 4K layout was too large for 1080p; this was not treated as a fit.

Native control QA V2 intentionally exposed a real defect: all three exported
Line Spacing sliders had maximum 100. Requests 110/105 were clamped; mandatory
readback rejected the mismatch and disabled the partial item. V3 retained all
15 required controls and used valid leading values 90/95/100. Actual result:
`ok=true`, `imported=0`, `updated=1`, `disabled=0`, `failed=0`. No duplicate was
inserted. Readback confirms texts, fonts, sizes, colors, leading, tracking,
duration and layout; the native image visibly changed all three text strings
and colors. Controlled same-text font/size A/B still remains to prove rendered
style propagation, not merely the UI/readback. Center placement and test colors
are deliberate QA overrides, not approved production composition.

Evidence: `proof/subscribe-native-qa-20260905/finisher-controls-v3/`.
This native QA has not yet been saved/exported as a new reviewed deliverable.

## Separate importable caption proof

`proof/caption-editorial-audit-20260905/reflow-v1/` now contains two new SRTs
for the automatic **Safe/Tight sequences only**, not the shorter manually
reviewed Delivery sequence. An evidence-bound generator applied three tail
rebalances and two adjacent-cue merges. Each variant changed from 140 to 138
cues and from ten to five orphan findings. Exact token order/count, numeric
strings and pair outer endpoints were preserved; audio/video/XML are unchanged.
Twenty-one regression groups, actual-output reread and refusal to overwrite an
existing output passed. The expanded tails/merged pairs are checked against
their actual A1 source-continuous keeps, not merely neighboring transcript text.
Root reran all 21 groups successfully. A separate read-only audit, using a
different SRT parser rather than the generator, confirmed both outputs' exact
tokens/numbers, all 130 untouched cues per variant, every pair outer endpoint,
all ten XML interval/source mappings and all bound input/output hashes.

This is an isolated, importable layout proof, not a production-engine integration
or a correction of ASR spelling. Original orphan IDs 3, 4, 21, 64 and 125 remain
for acoustic/continuity review. See `REFLOW_RESULT.md` and
`reflow-v1/reflow-validation.json` in that proof directory.

## Compact authored template

Native read-only AE inventory confirmed exactly three `ADBE Noise2` effects in
the Subscribe hierarchy. Glass Opacity already has 17 actual fill bindings;
Glow Radius and Intensity did not have corresponding live visual bindings.

`proof/subscribe-compact-native-20260905/` contains a reviewed, isolated builder
for a real HD wrapper and compact reflow of the same authored artwork. It is
intended to remove those Noise effects entirely, preserve real Glass bindings,
connect existing glow passes, and export a new MOGRT/AEP without overwriting
the source. A separate metadata finalizer extends leading ranges and enables
font/size controls while checking non-definition payload bytes. These scripts
are not a qualified native Premiere candidate yet. The first builder has now
run; the current native continuation checkpoint is recorded below.

Windows automation resumed after the user's explicit continuation. The correct
JSX path was observed in the dialog before submission. The builder created four
private comps in memory and `build-01/source-before-compact.aep`, then failed
closed on the controller-only base-text invariant; no AEP save or MOGRT export
occurred. Its log verifies removal of all three Noise effects, 17 preserved
Glass bindings, the four eased scalar animation channels and three default
ABAR text/font/size/bounds checks. The original builder and failure log remain
unchanged.

`diagnose_controller_probe.jsx` ran independently against that private
in-memory candidate without save/export. All nine font/size/leading probes
passed: AE's `valueAtTime(2.2,true)` reports evaluated Source Text styles here,
while reading with `expressionEnabled=false` proves the stored base text is
unchanged. The expression string was unchanged and every default was restored.
Evidence: `controller-probe-01/diagnostic.log` and ten actual HD PNGs. These
single-line images cannot prove visible line spacing; a multiline proof and
native Premiere check are still required. No source AEP was saved.

## Current native continuation: measured corrections

- A separate Premiere project was saved at
  `proof/subscribe-compact-native-20260905/premiere-qa/Hafez-Compact-Subscribe-Native-QA-20260905.prproj`.
  The new 300-frame Compact QA XML was actually imported into a new bin and
  activated with sequence ID `c27929b5-a4f7-4a85-a929-40e27268339d`.
  It preserves five original video/A1 cuts and adds no PNG/filter/SFX.
  The later Compact native import and placement below have now
  been saved in this separate QA project; the source Delivery project is intact.
- Native `eg-inventory-01` proves the 25 fresh EG names are enumerated in exact
  reverse registration order, using indices 1..25. Both failed preflight
  assumptions and prior scripts are preserved; no control was renamed to fit
  the validator.
- A real private-template bug was reproduced: `Show Background=0` still gave
  background opacity100 because a Property object was used as a ternary
  condition. Only the private background expression was changed to an explicit
  `.value > 0.5` check. Native0/1 probes now produce0/100; enabled exit is0;
  all25 control defaults and original source AEP remain unchanged.
  Evidence: `background-checkbox-fix-01/before.json` and `after.json`.
- The resumed exporter again passed all nine controller-only style probes, then
  failed its immediate file-size check after its first frame save. The actual
  `build-01/rgb-diagnostics-01/baseline-hold.png` subsequently exists and is a
  valid52,308-byte HD RGBA8 PNG. Thus no intrinsic flattening limitation of
  `saveFrameToPng` has been established. The earlier opaque images had the real
  background-expression bug. The new image has alpha0..255 and1,949,540 fully
  transparent pixels. At this hold, alpha>=64 bounds are288x210; faint
  alpha>=1 bounds are423x329, exceeding the proposed326x278 slot. One hold is
  not full-animation/body-placement certification. All partial evidence remains.
- Caption `reflow-v2` applies only the exact source-backed question merge F to
  prior `reflow-v1`: each original automatic Safe/Tight variant now has137 cues
  and four orphan findings. Root reran27 tests and the independent disk/XML/
  literal-token verifier successfully. All words/numbers and unrelated cues
  are unchanged. These SRTs are NOT for the separate509-second Delivery Review,
  are NOT yet production-engine integration, and do not correct uncertain ASR.
- Fourteen proof-only PNG/alpha/A-B fixture groups pass. Alpha>=1 full-frame
  support and genuinely opaque255 pixels are now explicitly distinguished.

## Subsequent verified Compact native export and import

- The actual private candidate AEP and raw MOGRT were exported to
  `proof/subscribe-compact-native-20260905/build-01/`. A post-export reporting
  error did not invalidate the already-written files. No exporter was rerun
  to conceal that error. Original source AEP and its backup remain byte-identical.
- `Hafez Hermes Subscribe Compact Review 2 - Native.mogrt` is a real ZIP-based
  AE MOGRT, SHA-256
  `999c675f9a12dae171e750dcc3601e60474a8bc0762616e2e4b4013e78551edc`.
  Independent ZIP/CRC audit confirms the AE graphic and thumbnail payloads are
  byte-identical to the raw export; only the intended font/size capabilities
  and leading ranges (1..400) changed in metadata. All 25 names, IDs and defaults
  stayed unchanged. It is not a PNG replacement.
- Premiere's native Graphics Templates import installed this exact candidate.
  Untouched defaults were inspected in the separate Compact sequence: 25 actual
  controls, all three nonblank texts, ABAR fonts/sizes and leading 76/62/72.
  `premiere-qa/inspect-defaults.native-result.json` is the actual response.
- The byte-identical alias without the ` - Native` suffix enables strict reuse
  of the already-observed native clip name. Applying the reviewed placement
  updated exactly one existing V4 item: imported=0, updated=1, failed=0,
  disabled=0, no warnings. The clip spans frames 60..187 (127 frames), position
  [1510,260], scale100, duration control4.2, original text/colors and glow34/22.
  This is a manual visual QA position, NOT body-safe certification.
- The QA project was saved with that native item, and preserved again as
  `premiere-qa/before-native-ab.prproj` before control A/B. A real native Export
  Frame at sequence frame125 is `proof/Compact-Native-20260905-00-baseline.png`,
  SHA-256 `0aef0e2f7521bdd80fc071a7a26148c8571015b24fa5740f714984e40c8aaccd`.
  The frame was not imported into Premiere or placed on the timeline.
- All 127 actual HD RGBA frames were captured and CRC/hash checked against the
  frozen candidate and unchanged controls. Two chunk06 dispatches occurred
  before a receipt appeared; receipts subsequently show completed chunks06 and07.
  No inferred completion, invented frame, deletion or reset was used. Manifest
  and measurement are in `alpha-captures-01/`. Full-animation union at alpha>=1
  is [733,374,440,347], at >=16 [781,407,357,280], at >=64 [804,425,312,230].
  Thus the former 326x278 slot fails. Visible frames are2..125; frame126 at
  4.2042 seconds is fully transparent. No canvas-edge contact was detected.
  These are AE alpha measurements, not independent body tracking or native
  Premiere full-animation equivalence.
- Actual AE same-frame A/B pixels respond to glow radius/intensity and each of
  the three multiline leading controls. Native Premiere same-control visual
  A/B is still in progress, with prepared requests under `premiere-qa/native-ab/`.
- A new pure `caption_evidence.py` helper passed 29 regression tests plus the
  existing 13 caption tests (42 total, independently rerun). It refuses missing
  ownership/media/acoustic/Keep evidence and preserves literal selected words.
  Float and SRT millisecond serialization are checked against source bounds.
  It is NOT yet called by production finalize or included in the deployed EXE.
  Legacy full-job metadata is insufficient; helper tests do not establish that
  old captions were corrected. A narrowly scoped new-word ownership prerequisite
  is being implemented separately; no production caption merge is claimed.

## Native control proof and corrected Glow diagnosis

- Actual Premiere A/B 01, 03, 04, 05 and 06 completed at sequence frame125.
  Glow-zero, same-text font weight, size64→84 and multiline leading76→116
  changed rendered pixels, not merely readback. Independent PNG CRC/decode and
  pixel comparison found zero differences outside the declared upper-right
  graphic ROI. All1,684,800 outside pixels were byte-identical. The leading
  pair differed in3,767 pixels and exactly one of25 native controls.
- Restore99 independently verified all25 placed-baseline values. The separate
  Compact QA project was saved again at22:32 local,1,590,371 bytes. Test PNGs
  were never imported into a timeline. Deliberately overlapping multiline test
  text is not an approved production composition.
- **The current Compact Glow names are semantically wrong.** The builder wired
  Glow Intensity/Radius to the four structural CC Light Sweep edge
  intensity/thickness properties. Setting intensity0 removes the glass rim;
  this is not independently adjustable bloom. Do not qualify that asset on the
  strength of its earlier pixel-response tests.
- The isolated `soft-glow-probe-01` kept the authored rims at50/10 and changed
  only the existing soft passes. All six actual HD PNGs are byte-identical,
  SHA-256 `b103d978e531ffe2be74e7b25db883f44542f6d3afb641602ea61a70951d4b68`.
  The exact probe report confirms all25 defaults and12 effect properties and
  expressions restored, no error, no save/export. These existing soft-pass
  bindings showed no visual contribution at the tested hold. They must not be
  presented as working Glow controls. This does not disprove other templates'
  actual Deep Glow effects.
- The first command-line dispatch produced no observable receipt/output and
  was not counted as success. The separately logged wrapper was selected and
  run once through AE's native File > Scripts dialog. Its receipt records one
  invocation, the verified probe SHA, six captures and successful return.

## New source-only engine safeguards

- `build_review_segments` now preserves explicit new-word ownership and actual
  boundary reasons. Old1268-word/84-segment metadata stays identical. It does
  not fabricate ownership for legacy manifests.
- Optional `caption_context.py` binds selected caption chunks to owned words
  and final1× A1 Keeps. Missing SHA, exact clock, acoustic coverage or literal
  ownership fails closed. A peer-found internal manual-boundary issue was
  reproduced and fixed: old regrouping cannot hide protection and thereby
  authorize another merge. Legacy Safe/Tight remain byte-identical140-cue SRTs
  when no context is supplied. Fresh-job producer wiring is still in progress.
- `_catalog_review_failure` now allows only the catalog's existing exact
  `native-qa-approved` status. Unknown, pending, missing, failed and uncatalogued
  assets remain editable blocked drafts, with no SFX or active family selection.
  Existing approved Glass stays eligible; no catalog asset was promoted.
- Root independently reran246 tests successfully in5.666 seconds after these
  changes. These new source changes are NOT yet included in the deployed EXE.
  Backups: `backups/caption-context-integration-20260905-222951-968/`,
  `backups/caption-context-internal-boundary-20260905-224312-097/`, and
  `backups/native-template-release-gate-20260905-223741-574/`.

## Remaining publication gates (latest)

- Ten caption review findings in normal engine output; four in the separate
  reflow proof. Raw-ASR lexical accuracy, abandoned clauses and the documented
  short intraword audio cuts remain unverified.
- Independent-body detection, all-frame transformed subject union and calibrated
  native footprint/placement. Actual AE every-frame alpha coverage is complete
  for the frozen Compact candidate, not arbitrary edited text/layout variants.
  The previously proposed local human-segmentation model download is still
  unapproved; no model was downloaded or substituted.
- Compact Subscribe's misleading Glow control semantics, qualified final asset,
  readable full-duration placement and final entry-frame SFX. Font/size/leading
  native A/B is complete for the frozen previous candidate, not future variants.
- A new complete native Premiere delivery containing the qualified replacement.

`publicationReady=false` remains intentional. No model/asset downloads, uploads,
UI redesign, Trading/MetaTrader/database/credential or original Hermes changes
occurred. Existing full Delivery Review video and its approved Glass clips are
preserved. Backup before this native test:
`backups/subscribe-native-before-20260905-1905`.

## Weekly-use checkpoint — candidate02 installed, 2026-09-05

This section supersedes earlier source-only/deployment-pending statements above.
It does not turn earlier failed proofs into successes or certify publication.
The user requested a usable weekly checkpoint while retaining at least 10% of
the account's weekly allowance. No additional feature work is started here.

### Engine and deployment

- Root's complete source suite passed **272 tests**. Candidate02 contains the
  fresh caption provenance/context producer, strict native catalog release gate,
  and the short-sequence camera validation fix. A legitimate single-shot short
  sequence no longer fails the unconditional two-shot assertion. Validation
  still binds the exact final XML clock, schedule coverage and long-cut policy.
- Candidate02 EXE SHA-256 is
  `cf4c82628f3ba4d347a365a6d17c420726389493ed450940fe565751a056b1e6`.
  All18 embedded Hafez modules match frozen source;25 build inputs are frozen.
  Its build uses an isolated PyInstaller cache from process launch.
- The real12.012-second two-camera excerpt proof ran new local Whisper, without
  reusing ASR cache:39 words, prepare48.44s and finalize4.10s, both exit0.
  SHA-bound source evidence and the exact30000/1001 XML clock passed. No review
  model was called in this finite producer proof. Ambiguous ownership remained
  review-required; no unsupported caption merge was applied. See
  `proof/fresh-caption-producer-e2e-20260905/run-candidate02/validation.json`.
- Candidate02 full cached finalize and the separately executed **installed**
  cached finalize both passed. The installed engine reached completion/100%.
  Ten checkpoint tasks were reused, with zero ASR/LLM calls in the cached test.
  Nine formatting changes were accepted and59 lexical changes rejected. There
  are two active approved Glass graphics/two SFX, six blocked drafts, zero PNG
  timeline clips, and unprocessed original voice. Legacy Safe/Tight remain
  byte-identical140-cue outputs with ten review findings; they were not silently
  upgraded to new source evidence or declared editorially corrected.
- The complete1,888-file runtime is now installed in BOTH
  `release/win-unpacked/resources/engine/hermes-engine` and
  `engine/dist/hermes-engine`. Full-tree hashes, help, doctor, cached finalize
  and caption validation passed. No old trees remain inside the packaging
  wildcard. Both complete prior trees are retained under
  `backups/final-caption-engine-deployment-20260905-234443-195/`, in
  `prior-live-retained` and `prior-packaging-retained`. Nothing was deleted.
- Authoritative result:
  `proof/final-caption-engine-deployment-20260905/deployment-result.json`.
  An independent read-only reviewer confirmed the deployed hashes, retained
  copies and actual smoke/caption reports. Do not replay the one-shot deploy
  helper or reuse its proof directories.

### Native Rim controls and saved project

- A separately identified authored Subscribe replacement now exposes truthful
  **Glass Rim Intensity / Glass Rim Thickness** controls. These control the
  structural glass edge, not independent bloom/Deep Glow. Inert soft passes
  are not advertised as functional Glow controls. Existing effects/artwork
  were retained; no new AI graphics or Grain was introduced.
- Native asset:
  `proof/subscribe-compact-native-20260905/rim-controls-candidate-01/Hafez Hermes Subscribe Compact Rim Review 2 - Native.mogrt`,
  SHA-256 `dc19dbff5de351022a3c0d6fc2ddeaec17553d758736b4e7de167a6a5b0f96a4`.
- Actual Premiere A/B at sequence frame126 tested each rim control at zero.
  Independent CRC/decoded-pixel audit found15,324 changed pixels entirely
  inside the288x210 plate; the camera image outside was exactly unchanged.
  Both zero variants yield equal decoded images. The PNG files are exported
  QA evidence, NOT timeline overlays. All25 control readbacks passed for
  baseline/each change/restore99. Baseline values were restored.
- Root saved the separate QA project with Ctrl+S; its title lost the unsaved
  marker and its file hash is
  `f517ac9ff2b65bc8a1ee742e90dfb24e7bd0132f63dcc5b03adcc259209b86db`:
  `proof/subscribe-compact-native-20260905/premiere-qa/Hafez-Compact-Subscribe-Native-QA-20260905.prproj`.
  Select `Hafez Subscribe Compact Rim Native QA - 20260905`.
  This new asset has NOT been promoted to the automatic catalog. Manual QA
  placement is not independent-body/full-duration safe-placement certification;
  the previous candidate's alpha envelope does not transfer to this new hash.

### App handoff and honest remaining boundary

- Before deployment, native Hafez UI was observed idle with0/2 sources,
  Engine/ASR/AE/Premiere ready, and a visually consistent80% glow slider.
  Root closed it normally, completed deployment and reopened the actual
  `release/win-unpacked/Hafez Studio.exe`.
- The reopened window/process was observed, but subsequent native state capture
  and its single recovery returned `foreground window did not report a process id`.
  Computer-use input stopped according to its recovery rules. Therefore this
  checkpoint proves installed-engine completion, NOT a newly completed
  start-button-to-finish UI job after this deployment.
- The preserved8m29s Delivery Review project/video remain the practical working
  deliverable. Its reviewed take/phone removals include earlier manual work;
  do not attribute those repairs to an already-generalized automatic policy.
  It has two real editable Glass MOGRTs, no burned-in draft subtitles and no
  newly added Subscribe. See `docs/WEEKLY_USE_2026-09-05.md` for exact links.
- Next work remains: source-audio review of wording and short cut boundaries;
  caption cleanup with evidence, not paraphrases; independent body tracking and
  full-animation placement; qualified Subscribe onset/SFX and catalog integration;
  a fresh complete UI run when native control is available. The word-boundary
  guard currently REPORTS findings; it does not repair cuts automatically.
- No downloads, Trading/MT5/database/credential/original Hermes changes, app
  redesign or new model substitutions were made. `publicationReady=false`.
  Pre-append documentation backup: `backups/weekly-handoff-20260905-01/`.

## 2026-09-08 — native UI continuation and installed summary fixes

See `docs/UI_E2E_CHECKPOINT_2026-09-08.md` for the new authoritative continuation.
Three real Start-button jobs on the same two12.012-second source excerpts each
ran fresh ASR and four valid local model tasks and reached native100%. Two
post-deployment runs verify the installed changes. This supersedes the earlier
missing UI-run proof, not the pending full-length editorial review.

Blocked proposals no longer count as ready editable motions. The existing
summary line now visibly states blocked/review-required counts. Source changes
are scoped to CLI summary counts, five Python regression tests, and renderer
completion text; no Director HTML/CSS or slider redesign.277 Python tests and
five renderer cases passed. Live/packaging engine SHA256:
`ca12b8ac07e341a175626f93785a1bf4d8317a319de7214523aa6d89adb31e3e`.
Final app.asar SHA256:
`0a1f3d2e18933018d6091ca4ae5c7890eab84440c95384e1a0470678284da874`.
Final runtime report: `proof/ui-e2e-20260908-03/runtime-verification.json`.

Native Premiere imported the first app XML in a separate new project and the
Finisher rejected its sole blocked title without insertion. Saved proof project
`proof/ui-e2e-20260908-01/Hafez-App-E2E-20260908.prproj`. This is negative-gate
evidence, not a new successful MOGRT insertion. No picker action is pending.
The full working publication project was newer than this old checkpoint and
was preserved. New retained backups: `backups/summary-fix-deployment-20260908-01`
and `backups/summary-warning-visible-20260908-01`; nothing deleted.

At handoff Hafez has the short QA excerpts selected. Full source files must be
selected for a real full edit. ASR CPU fallback, lexical/caption review, word-cut
repair, independent all-frame body tracking and automatic Subscribe remain
unfinished. `publicationReady=false` remains intentional.

# Glass native-review handoff — 2026-09-13

> Later continuation: see `GLASS_TIMELINE_2026-09-13.md` for the new real full-timeline
> review, 389 tests, shared chapter timing and connected Glass planning catalog.
> Latest continuation: `GLASS_FINALIZE_2026-09-13.md` records opt-in CLI integration
> and actual local SFX on the saved native review. Packaged app remains undeployed.
> Fonts are explicitly deferred by the owner; the original sample below remains unchanged.
> The older remaining-work list below is historical, not the latest integration status.

## Exact status

Working native editable template sample, NOT a released automatic Glass editing pipeline.
The Windows application has not been rebuilt/deployed with Glass support in this work.
Do not tell the owner that selecting two cameras now produces this package automatically.

Project root: `C:\Users\1SKY.IR\.n8n\products\HafezStudio`.
Backup: `backups/glass-pack-20260913-01` (engine, config, tests, CEP, package/build files,
and original installed hafez.jsx). Original vendor assets and old Premiere projects unchanged.

## Deliverable to open

- Project: `proof/glass-pack-20260913-01/Hafez-Glass-Pack-Review-20260913.prproj`
- Sequence: `Glass Pack - Native Review - 20260913`
- Sequence ID: `8e0d1a31-eb21-479b-865c-ac5974ba4fd1`
- Native preview: `proof/glass-pack-20260913-01/Glass-Pack-Native-Preview-20260913.mp4`
- Actual export: H.264 1920x1080, 30000/1001 fps, AAC 48kHz, 27.994633 seconds.
- Contact sheet: `proof/glass-pack-20260913-01/native-preview-contact-sheet.jpg`
- Canonical QA plan: `proof/glass-pack-20260913-01/visual-review.plan.json`
- Final readback: `proof/glass-pack-20260913-01/visual-review-inspect.result.json`

This short preview export was authorized QA, not a final movie export or publication.
No PNG is used as a timeline graphic. The separate PNG still/contact sheet are evidence only.

| Approximate time | Native content |
| --- | --- |
| 0–6 s | FosLight SaaS title over Qss gradient; English then Persian vendor animation |
| 6–14 s | Real camera/source-audio excerpt from the existing video edit |
| 14–20 s | FosLight Trendy words over the same Qss palette |
| 20–28 s | Motionstate Liquid Glass progress card; clearly labeled DEMO |

Five native MOGRT instances, four distinct templates/families. The demo titles and 83% number
are template QA copy, not AI-extracted facts or a validated editorial decision for this speech.
No newly curated music/SFX are present. The preview's source audio is not a final audio mix.

## What was implemented and verified

- Seven distinct user-supplied packs, 114 unchanged local MOGRT assets copied and hash-indexed.
  Source 3 duplicated source 2. Trendy directory actually ends with `utc_2`.
- Independent registry/compiler in `engine/src/hermes_video/glass_pack.py` and
  `config/glass-library.json`; four core families, three optional. 21 assets have some locked
  font controls; never represent all 114 as fully editable or natively approved.
- One smoked-emerald palette bound to every exposed color in each chosen template.
- Typed native binding by name + kind + occurrence, including duplicate names shared by text,
  color and groups. Font/size capability checks, set-and-readback verification.
- Forty-three bindings verified across five clips (6+6+6+6+19).
- Idempotent reapplication: final receipt reports imported=0, updated=5, failed=0;
  no duplicate clips. Missing/failed bindings disable incomplete clips rather than substituting PNG.
- Explicit exact-project/sequence apply guards and native Motion scale support.
  Premiere component matchName is `AE.ADBE Motion`; sampled scales are 65 for titles,
  70 for Liquid card, 100 for the two backgrounds. Uniform Scale=true.
- Palette/hash/control/type/path validation and no metadata-only native approval.
- CLI `glass-status` and `glass-validate --qa --plan ...` are read-only.
- `--style glass` through the ordinary engine path now fails early: automatic chapter routing
  is not implemented and must not silently invoke the legacy visual style.

## Native visual findings

1. ABAR Source Text metadata accepted the correct PostScript name, and Premiere displayed
   the family/style, but actual rendering showed a wrong/fallback appearance. Switching to
   ArialMT/Tahoma changed the real rendering. The cause of ABAR resolution is NOT established.
   No system font install, font-cache purge, or global settings change was performed.
2. Current QA uses Tahoma for Persian and ArialMT for English/numbers. These are diagnostic
   placeholders, NOT the selected Glass identity. Font choice and actual native rerender remain.
3. In this QA sequence, disabling Sequence Settings > Composite in Linear Color visibly fixed
   the stepped/banded SaaS glow. Only this isolated sequence was changed. This setting is recorded
   in the plan but NOT automatically enforced by the bridge; do not assume it applies elsewhere.
4. The native preview/contact sheet show actual animated entry, title changes, counter progression
   and departure movement. This is sampled visual review, not frame-by-frame motion curve proof.
   Some template timing and bilingual simultaneous hierarchy still need final design review.
5. The graphics are separate fullscreen cards, not overlays on the camera excerpt. Consequently
   this sample does not certify full-interval face/body tracking for future Glass overlays.

## Verification

- 356 Python unit tests passed: `proof/glass-pack-20260913-01/python-tests-release-gate.log`.
- `node tests/glass_bridge_test.cjs` passed (typed controls, locks, ownership, retries, scale).
- Node syntax checks passed for electron main/preload, renderer and CEP panel.
- Canonical plan CLI validation passed with actual file/hash checking and publicationReady=false.
- Native export successfully decoded/probed and 1 fps contact sheet visually inspected.
- Premiere project saved after the scale and compositing fixes; no unsaved-star remained.

## Deployment distinction

Source CEP JSX and installed `.../Adobe/CEP/extensions/ir.hafez.studio.cep/jsx/hafez.jsx` were
updated during the authorized native trial. Original installed file is in the backup.
The small source `panel.js` inspect-request forwarding change has NOT been deployed/reloaded
in the live panel; current final inspection used the already-running legacy no-argument panel
handler against the visually verified isolated project. Apply targeting was enforced in JSX.
The packaged app/engine release is unchanged. `package.json` now includes the Glass library
resource for a future build. Local npm shim is broken; direct node checks were used.

## Remaining work in dependency order

1. Owner chooses final Persian/English pair. Suggested: Estedad Medium/SemiBold + Geist;
   alternative Vazirmatn Medium + Inter. Verify installed desktop font resolution in actual
   Premiere and rerender before approving typography. Do not add downloads silently.
2. Finalize selected variants' bilingual hierarchy, line spacing, duration, in/out framing and
   native effect requirements. Approve only exact verified asset hash + font/layout contract.
3. Connect the Glass availability/approval catalog to editorial planning/review. `prompt_summary`
   exists but is not currently consumed by the old subtitle/local-AI review prompts.
4. Implement real chapter insertions before camera footage and a single shared timeline remap
   for camera clips, dialogue, captions, graphics, markers and cue times. No cut-off sentences.
5. Curate local licensed music/SFX, frame-sync entrance sounds, duck only background music.
   Glass subscribe template is still unselected; do not substitute Grunge without approval.
6. For overlays, measure new rendered text/template footprints across the full interval against
   face/body unions; old approved template footprints are invalid for these vendor templates.
7. Run fresh end-to-end two-camera automated project QA, build a candidate application, verify
   the packaged path, and deliver one clear review sequence. No automatic final movie export.

All original constraints about Trading/credentials/DB/Hermes remain. Grain prohibition was
explicitly revoked. Director UI and Adaptive slider were not redesigned in this Glass work.
The owner requested font suggestions for a choice; do not claim the package is production-ready
while the above integration/audio/native-QA items are outstanding.

## Font reference pages (design pairings are recommendations, not native certification)

- Estedad: https://aminabedi68.github.io/Estedad/
- Geist: https://vercel.com/font
- Vazirmatn: https://github.com/rastikerdar/vazirmatn
- Inter: https://rsms.me/inter/

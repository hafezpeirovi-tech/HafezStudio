# Hafez Studio 0.3 operational status — 2026-09-09

## Current installed build and delivery

Installed engine: `preview-geometry-engine-20260909-03`, EXE SHA256
`84e140c3c84c708fc115329cb772a7c41a7aa299ccf9c1de9628a2be693a9b8d`.
Both runtime trees were deployed with all 1891 file hashes verified; previous
trees retained in `backups/preview-geometry-20260909-03`. UI was not redesigned.
313 Python tests pass. The inverted-slider endpoint smoke test passed in the
native app: 0% empty/left, 50% half-full, 100% full/right; restored 80%.

The latest saved native review project is:
`proof/body-safe-delivery-20260909-01/Hafez-Body-Safe-Review-20260909.prproj`.
Its full Director timeline lasts 00;09;09;11 (30000/1001), with 31 shots,
30 camera switches, 13 punch-ins, ONE eligible native editable MOGRT and FIVE
blocked proposals. No PNG timeline clips. The MOGRT's 21 controls were read back
in Premiere, and entry/hold/outro inspected. Every one of its 95 XML frames maps
to independent source-body/face evidence with identity camera transform.
This is not a rendered pixel audit or proof against font substitution.

A real installed-app Start run exposed a 76% crash in optional preview geometry;
it was reproduced and fixed. After deployment, a second native Start recovered
that job (`HS-MTU6YWL6`) with cached ASR/AI and visibly reached 100%, generated
three XML sequences and no PNG clips. Full original-video finalization also
passed with saved ASR/AI; its XML/native MOGRT contract matches the saved project
except for output paths. Neither rerun should be described as fresh full ASR.

**Usable editable review baseline; not publication-ready or unattended finish.**
Persian ASR still needs listening/review. Five graphic proposals, Subscribe,
calibrated zoom placement and visual font verification remain. For a NEW job,
XML and its matching Plan still need Premiere Finisher and a native project save.
No automatic MP4 export is wanted or was started this turn. The user reviews
before manually exporting. See `BODY_TRACKING_2026-09-09.md` and the delivery README.

## Historical September 8 acceptance (superseded where noted)

## Scope update — 2026-09-09

The user explicitly approved the local body-model download and clarified that
automatic MP4 export is **not required**. Acceptance ends at an editable Premiere
timeline for the user's review; export is a deliberate manual action afterward.
Body-tracking implementation/evidence is recorded separately in
`BODY_TRACKING_2026-09-09.md`; the September 8 results below remain historical.

This section supersedes the historical 0.2 claims below. The installed Windows
engine was rebuilt offline and verified against all 1,888 deployment files.
298 engine tests pass. A full two-camera automatic cut has been imported into
Premiere, its native editable MOGRT read back, and a 9:09 full review MP4 exported
and decoded without error. See `AUTOMATIC_QUALITY_2026-09-08.md` for exact evidence.

**Operational editing baseline, not unattended publication-ready.** Current ASR
still makes Persian lexical/name/number errors. Draft captions are not burned in.
Unverified machine-generated sentence graphics are blocked; only narrowly
grounded curated term labels can pass the automatic copy gate. The demonstrated
full cut has one genuine editable MOGRT, five blocked proposals, and no PNG clips.
Background music and automatic Subscribe are not active in this delivery.
Placement is sampled multi-frame face detection with a face-derived body envelope,
not independent every-frame body/hand tracking. GPU ASR uses explicit CPU fallback
on this machine; the local model is available and no new models were downloaded.

The generated XML and plan still require the Premiere Finisher/import and a native
save/export. Computer Use performed those host operations in the demonstrated run;
they must not be represented as an unattended end-to-end publishing feature.

## Historical 0.2 status (not current acceptance evidence)

### Earlier feature inventory

- Standalone Windows desktop application and portable Python engine.
- Branded Hafez Studio shell with adaptive monogram, persisted dark/light mode,
  bundled Estedad variable font, and YouTube/Reels/Podcast workspaces.
- Offline Persian speech model, FFmpeg/FFprobe and face-detection model.
- Two-camera sync, silence editing and mutually exclusive camera decisions.
- Camera-1-only broadcast voice master; camera-2 audio stays disabled.
- Premiere FCP 7 XML, two SRT variants, edit notes and YouTube package.
- Complete Persian editorial statements, English kickers, flowcharts,
  comparisons, HUD metrics and dense Signal OS motion-graphics planning.
- Nine original editable Liquid Glass MOGRT systems plus transparent PNG fallback assets.
- Premiere CEP Finisher used by the verified Director Cut, experimental UXP source,
  and optional private Telegram/n8n adapter.

## Portable build

The complete folder `release/win-unpacked` is the current verified Windows
distribution. Copy the whole folder; do not copy only the EXE because the AI
engine and offline runtime live under `resources`.

## Before a commercial sale

- Add an original application icon and Windows code signing.
- Sign the Premiere CEP Finisher ZXP with a production certificate and reserve
  production UXP IDs for the experimental successor.
- Run a clean-machine acceptance suite on CPU-only and NVIDIA systems.
- Add an installer/updater strategy that supports the large offline model pack.
- Complete a dependency, font and codec redistribution audit for the intended
  sales channel.

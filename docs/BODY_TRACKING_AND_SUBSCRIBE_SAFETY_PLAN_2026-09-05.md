# Independent body tracking and Subscribe placement — bounded implementation plan

Status: read-only audit complete; production implementation, model download and model inference have NOT started. Existing Delivery Review media, native project and two approved Glass clips must remain unchanged. This plan follows the fresh boot-bound `SENSITIVE_READ` authorization check.

## Verified current limitations

- `smart_crop.py:284` unions sampled face boxes plus `_presenter_envelope_from_face`; it does not detect a torso or body silhouette. The envelope expands a face by fixed horizontal/vertical ratios. The current metadata correctly names this `conservative-face-derived-envelope`, but it is insufficient evidence for independent body protection.
- `professional_edit.py:597` samples approximately every 0.45 seconds, capped at 11 per visible source overlap. Every-frame coverage is not currently available. Detection coverage is recorded but is not a condition of `collision_free`; missing results can fall back to a fixed central rectangle and still be labelled safe.
- The two enabled Delivery Glass cues contain 95 and 102 timeline frames but have 9 and 10 face samples. Both overlap a 116% semantic punch. Raw source bounding boxes currently do not include the actual XML Basic Motion scale/center transform.
- Subscribe spans approximately 125 frames across both visible cameras but has 13 samples total, including only one CAM2 sample. Its current inferred body union is `[0.2376, 0.0691, 0.5348, 0.9309]`; this is a heuristic, not measured body evidence.
- Existing title-safe area is the central 90% (`0.05,0.05,0.90,0.90`), subject clearance is 0.018, overlap threshold is 0.001, and generic minimum fit ratio is 0.58. Preserve these settings during the first proof; do not relax them to force a fit.
- Subscribe's audited source and Review 1 wrapper are 3840×2160. Catalog geometry/coordinate-space fields are absent; the planner currently inherits 1920×1080 controls and a generic scale of 67.9. Its chosen region is approximately 326×278 HD pixels. A full-comp dimension is NOT the visible artwork footprint, and point/scale behavior needs native calibration.

## Local capability inventory

Inside accessible HafezStudio assets, the only relevant image model found is `engine/models/face_detection_yunet_2026may.onnx`; other model weights are Whisper and Silero VAD for audio. No person, pose or human-segmentation weights were found. Some `.test-deps` / `.test-deps-run` dependency directories deny enumeration even outside sandbox; permissions were not changed, and this audit does not claim their inaccessible contents were inspected.

The packaged runtime includes OpenCV 5.0.0.93, NumPy and ONNX Runtime. Its `cv2.pyd` contains names for Farneback/PyrLK/DIS optical flow, GrabCut, MOG2/KNN background subtraction and connected components. These are available implementation candidates, not executed feature tests. No default HOG person-detector entry was found, so a usable bundled pedestrian model must not be assumed.

Optical flow/background subtraction alone cannot prove absence of a stationary torso or a briefly still hand. GrabCut without a trustworthy seed can miss clothing or merge background. They may conservatively EXPAND a verified mask or produce a manually reviewed proof, but must not substitute for independent body evidence or earn automatic `body_verified=true`.

## Immediate implementation, without downloading anything

1. Back up only the touched Hafez engine/tests, validate `HERMES_CONFIG_WRITE`, then add an opt-in strict spatial-audit contract. Do not overwrite or reapply existing delivered plans. Existing native Glass remains a separately documented, visually reviewed legacy result.
2. Enumerate every timeline frame in the final snapped `[start_frame,end_frame)` interval. Map it to every actually visible source layer/camera, respecting edits, disabled clips, frame rate and source in/out. Decode contiguous source runs, cache by media identity and exact frame, and reset temporal state across cuts. No sparse interpolation can count as a measured frame.
3. Record face observations separately from body observations. With no independent body model, report `body-model-unavailable`, `strict_spatial_verified=false`; return an editable blocked candidate with no entry SFX. Never convert a fixed central fallback or a face-derived envelope into proof of body absence.
4. Apply the actual per-frame XML Basic Motion transform before unioning boxes in sequence coordinates. Unknown/non-supported transforms, missing clip mapping, decode failure or missing face/body evidence block the cue. First qualify transformation math against a graphics-free native plate from the same sequence; do not approximate the 116% punch with an unverified static scale.
5. A future strict cue may become safe only with 100% required-frame decoding/observation, verified transform and verified template footprint. Any gap stays review-blocked. Full-frame conservative fallback may reserve the entire image, but it must not become a successful placement. Qwen remains final visual QA only.

Proposed metadata: expected/decoded/observed frame counts per camera; exact source-frame mapping; `body_observation_method`; model/version/hash; failed frame IDs; source and sequence unions; transform verification; template-footprint verification; `strict_spatial_verified`; explicit blocking reason. Keep old envelope metadata separately for diagnostics.

## Smallest independent model candidate — explicit download approval required

Recommend the FP32 `human_segmentation_pphumanseg_2023mar.onnx` from the official OpenCV Zoo (approximately 5.88 MB), not an arbitrary third-party model. It is a human-segmentation model and its directory declares Apache 2.0 licensing. [Official model documentation](https://github.com/opencv/opencv_zoo/blob/main/models/human_segmentation_pphumanseg/README.md), [official weight file metadata](https://github.com/opencv/opencv_zoo/blob/main/models/human_segmentation_pphumanseg/human_segmentation_pphumanseg_2023mar.onnx).

The official adapter uses OpenCV DNN with a 192×192 RGB input, normalized around 0.5; it resizes output scores to the source image and derives a foreground mask. This matches already packaged dependencies, so no new Python framework is intended. Runtime compatibility still needs a real local load test. [Official adapter](https://github.com/opencv/opencv_zoo/blob/main/models/human_segmentation_pphumanseg/pphumanseg.py), [official CPU backend example](https://github.com/opencv/opencv_zoo/blob/main/models/human_segmentation_pphumanseg/demo.py).

Approval request scope: download this single official model plus its license, record source revision/SHA256, store under HafezStudio only, then run offline. No asset search/download freedom, uploads or unrelated installations. The model has NOT been downloaded. Its performance on the actual seated presenter, black clothing, moving hands and blue lighting is unproven; low-resolution masks require conservative uncertainty dilation and native proof before approval.

After approval: process every required frame, retain all human foreground components rather than discard small hands, combine with face observations and conservative motion-based expansion, transform to sequence coordinates, and union every frame. Missing/implausible masks, model errors or observed foreground outside the mask keep the candidate blocked. A model result is evidence, not a guarantee; complete temporal coverage and visual validation remain required.

## Subscribe artwork-footprint proof

- Use a separate proof copy of the already authored `Hafez Hermes Subscribe Review 1`; do not alter the canonical asset or replace its artwork.
- Through the existing AE/aerender workflow, render native RGBA over its full actual 4.2-second cue, at output frame rate, with transparent optional background. No render or process has been started by this audit.
- Measure alpha support for every frame, including entry travel, authored overshoot, tail, shadows/glow and the tested editable text/font/size values. Record union bounds relative to the actual layout anchor in the 3840×2160 comp and the tested alpha thresholds; verify low-alpha fringe containment separately.
- Calibrate native Premiere point/scale mapping using the same asset. Fit the measured transformed footprint—not the full comp and not a generic card rectangle—inside safe area, outside the transformed all-frame human union. Maintain a readable apparent-text minimum. If no fit exists, keep Subscribe blocked; do not shrink to unreadability or cover the presenter.
- Changing text/font/size/leading beyond the validated footprint requires a fresh footprint measurement or an author-defined, verified maximum bounds contract.

## Required tests and acceptance

- Frame mapping: both interval edges, edit/camera boundary, one-frame visibility, disabled layer, repeated source interval and 29.97fps rounding; no frame outside the real cue falsely counted.
- Gates: zero/partial detection, single missing decode, absent body model, invalid mask, unknown transform and unavailable footprint must never return strict collision-free.
- Spatial: synthetic arm crossing outside face envelope between old sample points; seated stationary torso; two people; hand at border; camera cut; moving crop/zoom; 4K Subscribe coordinate conversion; entry/glow bounds larger than hold.
- Regression: current Python suite and Finisher/Import tests remain passing; a new strict audit must not mutate delivered files or existing native clips.
- Current-job proof: all 95+102+approximately125 visible frames, per-camera masks/bounds and transformed unions, contact sheets at all extrema plus entry/hold/outro. Parent performs native comparison before any candidate promotion.

Acceptance is scoped: independent-body and footprint verification may remain blocked until model approval and real proof pass. Do not describe the existing delivery as fully body-tracked or silently remove its already reviewed Glass clips.

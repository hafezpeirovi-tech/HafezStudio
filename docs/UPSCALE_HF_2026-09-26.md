# Requested HF video — active full upscale

Owner explicitly requested this supplied video be upscaled with the installed model.
Input: `C:\Users\1SKY.IR\Downloads\hf_20260926_115117_4bddb16c-37fc-493d-8e99-39be23f85b52.mp4`.
Input technical properties: 1280x720, 24fps, 385 frames, 16.041667s, AAC stereo 32kHz.
Target: 1920x1080, same frame rate, original audio packet copy. Master ProRes HQ;
playback MP4 H.264 CRF14 slow, audio unchanged. No original overwrite.

Current job: `proof/upscale-hf-20260926-02/request.json`.
Worker session 26453; PID 17424 as recorded in runtime lock when launched.
Delivery watcher session 51872 runs `scripts/deliver_upscale.py` after successful
full receipt; outputs `Upscaled-1080p.mp4` and `delivery.json` only after technical
validation. Watcher performs no model generation, uploads or unrelated process stops.

SeedVR2 3B FP16, batch9, temporal overlap4, prepend0, tiled VAE512 with overlap128,
SDPA, CPU offload. First attempt batch5 was intentionally stopped by exact owned
process tree only, before restarting in new directory with batch9. Other programs
were not stopped. At first complete chunk, estimated remaining ~43 minutes.

Important previous finding: old camera benchmark ended with154 instead of150 frames.
The worker rejected it: no successful receipt, no approved delivery. Prepend4 was
disabled for this new run (prepend0). Never present the old benchmark as successful.
The current full request explicitly authorizes processing, but does NOT constitute
owner visual-quality approval; receipt remains owner-review-required.

Before delivering: verify `receipt.json` and `delivery.json`, inspect comparison and
several frames/temporal transitions. Never claim completion just because process
started. `release-upscale-candidate-20260926-03` predates these parameter changes;
it must not be described as containing the frame-count fix without rebuilding.

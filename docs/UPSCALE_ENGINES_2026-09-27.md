# Independent Upscale engines — 2026-09-27

User approved cancellation of SeedVR2 for the 61.8-second portrait video, requested
a fast local option like free.upscaler.video and Topaz. Follow-up: no Topaz license;
prepare the free option only. No Topaz installation or purchase is authorized now.

## Implemented

- Default: WebSR CNN 2x Large with Real Life weights, from sb2702/websr (MIT).
- Fully local GPU inference in an isolated hidden Electron renderer. Strict CSP,
  no Node in renderer, no network, checksum-verified bundled model/library.
- Persistent GPU render target, GPU resizing, padded GPU-to-CPU readback. Avoids
  canvas swapchain clearing in hidden windows. Rejects black output from non-black input.
- Sequential bounded frame buffers, H.264 NVENC CQ18 encoding. No frame interpolation.
- Constant frame timestamps checked; HDR, 10-bit input, interlace, rotated and
  non-square pixel sources rejected explicitly. Enlargement only, maximum 2x.
- Source unchanged. Audio packet hashes, stream count and start times checked.
  Output frame count, frame rate, dimensions and full video decode verified.
- AAC-compatible audio: MP4. Unsupported MP4 audio is preserved in MOV (no silent re-encoding).
- Preview optional. Full processing always starts from frame zero.
- Progress reports actual frame counts; cross-instance lock and owned-process cancellation.
- SeedVR2 retained as explicitly slow optional engine; no new SeedVR2 jobs started.
- Topaz disabled with license/install label. No fake integration or silent fallback.
- Packaged build: release-upscale-candidate-20260927-05/win-unpacked.
  All 17 required packaged files verified; model/library hashes verified from app.asar
  in the actual Electron runtime. Desktop shortcut update follows verification.

## Validation

- First preview failed visual QA (black canvas readback); receipt marked rejected.
- Corrected preview: 150 frames, 30 fps, 1440x2560, 71 seconds total; preserved audio,
  full decode passed and still comparison visually inspected.
- Subsequent optimization keeps final resize on GPU and eliminates repeated frame
  concatenation. Full run completed successfully: 1854 frames, 30 fps, 1440x2560,
  275 seconds elapsed for the 61.8-second source. MP4 output; audio packet hashes
  match and full decode passed. Frame-30-second comparison visually inspected.
  Output: proof/websr-20260927/Upscale/1790520898133-656ba5c6/upscaled.mp4.
  The accompanying receipt.json records technical checks, not owner quality approval.
- Actual cancellation test passed, released lock and produced no final receipt.
- Unit tests: validate_media, model checksums, engine allowlist, full without preview,
  missing input, busy state and lock exclusion. Existing navigation and desktop bridge pass.

Quality remains owner-review-required. WebSR is a fast restoration option, not a
claim of equal quality to SeedVR2 or Topaz. Do not start Upscale from YouTube editing.

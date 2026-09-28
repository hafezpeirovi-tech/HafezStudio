# Topaz integration

Topaz Proteus Auto is now selectable in the independent Upscale page. WebSR remains the default. No YouTube editing hooks changed.

- Detect installed Topaz Video executable, FFmpeg, FFprobe and prob-4 model definition at the user's supplied installation.
- Local GPU execution, progress/ETA, exclusive job lock, owned-child cancellation, separate job directory.
- Full processing does not require a preview. Preview is optional, five seconds.
- Conservative supported input: 8-bit SDR, square-pixel progressive CFR, same media safeguards as WebSR. HDR/10-bit and variable timestamp sources rejected. Enhancement at source size or enlargement up to 4x.
- Current output uses H264 NVENC CQ18; source audio copied and hashes/timing checked. MP4 for compatible audio; MOV for PCM/other audio (including lossless preview excerpts).
- Full frame count/dimensions/fps and video decode checked before publishing final filename; original size/mtime checked unchanged.
- Installation detection is not a license entitlement check. Topaz performs license validation when executing; failure is explicit, no fallback.

Validation: direct full Proteus test previously completed 1854 frames in 329.90 seconds. Integrated manager preview completed 150 frames in 55 seconds with audio hashes and decode checks passing. Integrated cancellation released the lock without publishing a final receipt. Existing input, direct-full UI and navigation tests passed.

Build: release-upscale-candidate-20260928-01/win-unpacked. Backup: backups/topaz-integration-20260928-01. Desktop link updated using the backed-up shortcut script after package checks.

No Topaz binaries or license files are bundled or modified. Quality remains subject to owner review.

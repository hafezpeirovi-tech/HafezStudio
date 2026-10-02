# Hafez Studio

Hafez Studio is a local-first desktop product for AI-assisted, non-destructive YouTube editing. It analyzes two-camera footage, preserves camera-1 microphone audio, generates Premiere-compatible XML, builds captions and YouTube packages, and prepares animated Motion Graphics through an Adobe Premiere CEP Finisher and an original After Effects MOGRT pack.

The desktop shell exposes YouTube, an experimental Reels workspace, and a planned
Podcast workspace. Reels outputs are review drafts, not publication approvals.

## Reels preview

Run `npm run reels` to open the workspace. Select a saved `.prproj`, enter the
exact final sequence name, and keep the installed Hafez Studio Finisher CEP panel
open in Premiere. The saved project is copied before analysis. Premiere exports
audio for local transcription; the worker proposes up to six source-bound clips,
then the Finisher creates vertical sequences with nested original layers,
editable MOGRT text and native caption tracks in a separate `Hafez-Reels.prproj`.
Original color/effects remain inside the nested source. Portrait framing is a
center crop and needs review when a subject is off-center.

The offline selector uses explicit topic openings, chapter boundaries and speech
endings. It may return fewer clips and does not certify semantic quality. Gemini
selection is optional: `GEMINI_API_KEY` and `HAFEZ_REELS_GEMINI_MODEL` must be set
locally. Only the transcript is sent; no key is stored in the repository or shown
in logs. A matching SRT can replace ASR. Every output still requires checking
Persian words, clip endings, framing, source graphics and fonts.

Local orchestration uses the same manager as the app:

```powershell
node scripts/run_reels.js path/to/request.json
node scripts/preview_reels.js path/to/reels-plan.json reel-01 0 6
```

A request contains `project`, `sequence`, optional `outputRoot`, `selector`
(`local` or `gemini`), `count`, `min_duration`, `max_duration`, and `style`
(`editorial` or `editorial-3d`, a layered pause card). For finished-video input,
replace `project`/`sequence` with `video`. Preview rendering requires the native
project to have been saved and writes a new file under its `preview` folder.
The default Adobe preset produces H.264 QuickTime for review; captions in the
project do not automatically imply burned captions in that preset.

Jobs use an exclusive local lock and consumed Adobe requests are never retried
automatically. Preserve receipts when diagnosing a timeout; do not delete a
request ledger to force another native mutation. n8n can call the CLI through an
appropriately configured local runner; no n8n trading workflow is changed.

For this development checkout, double-click `Start Reels.cmd` to open the new
workspace. This launcher uses software rendering for the app interface; it does
not disable GPU processing in Premiere or the speech engine. Existing installed
releases are not automatically updated by changing this checkout.

Motion sources are in `motion-pack/reels/source`. The build/refine scripts run
only in an empty After Effects instance and verify actual exported files.
Use the normal After Effects `-r` script mode; `-noui` did not reliably export
MOGRT assets in the tested installation. The shipped v2 templates are reusable.
After changing templates or native JSX, update the installed CEP bridge and
create a new output job. Development checks:

```powershell
node --test electron/reels.test.js
python -m unittest discover -s engine/tests -p test_reels.py
```

## Preview and typography workflow

- Motion Design contains a live 16:9 Preview Lab for Signal OS, Neural Glass,
  Luxury Tech, all six Hafez motion systems, and the smart camera/zoom rhythm.
- Title/display and body/statement fonts are selected independently per video.
  Variable-font weights are applied by the Python renderer when supported.
- Transparent PNG graphics preserve the exact selected font without requiring
  a source-video render. Editable MOGRT Source Text is also included; install
  the selected font on the Adobe workstation when Premiere font editing is
  required.
- The title/body paths, family names, weights, and usage roles are written into
  the professional edit manifest so a project can be transferred or audited.

## Product boundaries

- The desktop application and video engine work without n8n.
- n8n/Telegram remain optional adapters for the owner's personal automation.
- No API key, Telegram token, owner ID, machine username, or absolute installation path is stored in source code.
- Source video is never re-rendered by the edit engine. Only lightweight graphic assets or motion templates may be generated.

## Development

```powershell
npm install
npm run check
npm start
```

Run the portable engine doctor:

```powershell
python engine/src/hermes_video/studio_cli.py doctor --json
```

## Build order

1. `scripts/build_engine.ps1`
2. `scripts/build_motion_pack.ps1`
3. Package the editable Premiere CEP Finisher as a signed `.zxp` and keep the experimental UXP plugin available separately.
4. `scripts/package_portable.ps1` for the verified offline folder build.
5. `scripts/package_windows.ps1` after code signing and large-installer testing.

See [Architecture](docs/ARCHITECTURE.md), [Portability](docs/PORTABILITY.md) and
[Release status](docs/RELEASE_STATUS.md).

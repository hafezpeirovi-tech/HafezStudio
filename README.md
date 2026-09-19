# Hafez Studio

Hafez Studio is a local-first desktop product for AI-assisted, non-destructive YouTube editing. It analyzes two-camera footage, preserves camera-1 microphone audio, generates Premiere-compatible XML, builds captions and YouTube packages, and prepares animated Motion Graphics through an Adobe Premiere CEP Finisher and an original After Effects MOGRT pack.

The desktop shell exposes three production workspaces: YouTube (active), Reels
(phase 2) and Podcast (phase 3). Product development stays focused on finishing
and approving YouTube before the later engines are enabled.

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

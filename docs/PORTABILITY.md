# Portability and transfer

## Machine-independent rules

- Paths are discovered from environment variables and Windows standard folders.
- `HERMES_RUNTIME_ROOT`, `HERMES_OUTPUT_DIR`, `HERMES_MOGRT_ROOT`,
  `HERMES_FACE_MODEL`, `HERMES_PERSIAN_MODEL`, `HERMES_TITLE_FONT_PATH`,
  `HERMES_BODY_FONT_PATH` and `HERMES_STUDIO_CONFIG` override discovery.
- The renderer selects a compatible static Persian display/body pair from the
  workstation and falls back to Windows Tahoma when no preferred font exists.
  Estedad Variable remains bundled for UI/Adobe use but is not used by the
  compact PNG renderer without RAQM. Custom TTF/OTF files remain external user
  assets; copy/install them on the destination Adobe workstation for editable
  MOGRT typography. PNG fallback output stays exact.
- Project bundles never include source footage or credentials unless the owner explicitly requests media collection.
- Brand packs are data-driven and can be copied independently of the application.

## End-user locations

- Application: the complete `release/win-unpacked` folder in the current build.
- Settings: `%APPDATA%/Hafez Studio/settings.json` through Electron `userData`.
- Offline model/tools: `resources/runtime` beside the packaged application.
- Cache: `%LOCALAPPDATA%/Hafez Studio`.
- Default outputs: `%USERPROFILE%/Videos/Hafez Studio Outputs`.

## Moving to another Windows PC

1. Copy the complete `release/win-unpacked` folder to the destination PC.
2. Install Adobe Premiere Pro. After Effects is needed only to rebuild or redesign the Motion Pack.
3. Run `Hafez Studio.exe` and verify that the in-app Doctor reports Ready.
4. Import the generated XML directly in Premiere. Install the bundled Hafez CEP
   Finisher and MOGRT pack when editable motion-graphics placement is required.
5. Reconnect the optional Telegram/n8n adapter locally; credentials are never
   embedded in or exported with the desktop package.

## Commercial hardening backlog

- Code-sign the Windows installer.
- Reserve production UXP IDs and package the plugin as `.ccx`.
- Add signed application updates.
- Test on a clean Windows 11 VM and a second NVIDIA/CPU-only machine.
- Add a license provider behind a replaceable interface; the core must remain usable offline.

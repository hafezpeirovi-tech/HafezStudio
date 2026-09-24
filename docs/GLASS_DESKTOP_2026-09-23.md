# Semantic Glass desktop checkpoint

Later update: owner authorized native testing; the separate project now exists.
See `GLASS_NATIVE_TEST_2026-09-23.md` for actual MOGRT insertion, visual checks and
the remaining caption timing failure. Earlier engine-only restrictions below
describe the packaging checkpoint, not the later authorized test.

## What changed

- Packaged the tested semantic engine revision 02 with the current Electron
  orchestration and Finisher into an isolated desktop candidate:
  `release-semantic-candidate-20260923-01/win-unpacked/Hafez Studio.exe`.
- Settings version 8 defaults to Glass. Loading pre-v8 settings migrates the
  old hidden `signal-os` default to `glass`, without writing the settings file.
  Other styles and explicit v8 choices remain unchanged. No UI redesign.
- This fixes a confirmed routing hazard, not a proven diagnosis of every earlier
  failed user run. The original installed executable/shortcut remains unchanged.
- Build checks the engine source manifest and expected binary hash before packaging.

## Verification performed

- 73 Glass unittest tests passed; four Node bridge/desktop/Finisher/panel suites passed.
- Migration tests cover fresh config, legacy config, other styles and v8 choices.
- Read-only packaged acceptance passed:
  `proof/semantic-desktop-verification-20260923-02/candidate-verification.json`.
- All 11 app source files match the ASAR, CEP resources match source, no mutable
  CEP runtime queue was shipped, and 114 vendor MOGRT assets across 7 packages
  passed hash checks. Packaged engine hash matches semantic engine revision 02.
- Packaged executable ran glass-status, doctor, and validated the latest real-video
  six-composite plan against packaged asset paths. No native commands dispatched.
- Attempt 01 failed because sandbox access to the Adobe templates directory was
  denied. Attempt 02 ran the same check outside sandbox and passed. Both evidence
  directories are retained. A pytest invocation could not run because pytest is
  not installed; the repository's unittest suite was used instead.

## Still not release approval

No app window was launched, no fresh ASR was run in this checkpoint, and no Premiere
project was opened, changed, saved or exported. Installed app and desktop shortcut
were not replaced. Native typography, animation phases, compositing and final
editorial acceptance remain pending. Current owner scope is engine only.

For later authorized native testing, open this exact candidate rather than the old
shortcut, verify the current Glass CEP panel is connected, and test into a new
review project. The app requires native receipt before reporting completion; XML
alone is not the MOGRT result. Do not apply the September 22 source plan over the
owner's newer live edit. No final movie export is needed.

Earlier engine details and unsupported chart/table/subscribe roles remain documented
in `GLASS_ENGINE_2026-09-23.md`. Backup: `backups/semantic-desktop-20260923-01`.

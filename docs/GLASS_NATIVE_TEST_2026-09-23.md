# Native Premiere test — actual project created

Owner explicitly authorized a new Premiere project for testing this turn.

## Result

Project: `proof/automatic-semantic-glass-20260923-05/frozen-package/Hafez-Glass-Review.prproj`

Sequence: `Hafez Glass — Automatic Timeline Review`

The same desktop Finisher broker was dispatched once through
`scripts/test_semantic_native.cjs dispatch`, using the real compiled-engine package.
This was NOT manual placement and NOT a fresh desktop/ASR run. Native receipt
confirms new project saved, 12 actual MOGRTs imported, 6 text updates, 0 failed,
0 disabled, 0 safety failures, and a caption track created. No movie exported.
Existing owner projects were not overwritten.

## Native observations

- At 00:00:03:00 the intro renders Persian text over the green gradient with glow.
- At 00:00:10:00 the first semantic title renders `بهترین استراتژی`.
- Properties exposes text, Abar High FaNum / ExtraBold, size 170, line spacing,
  position and scale. Live MGT readback confirms the expected ABAR font IDs and
  text values; palette values also match the plan.
- Changed that title's font size 170 -> 130 in Properties; visibly smaller text
  rendered. Undo restored 170. No hand-authored replacement graphic was used.
- Short playback from the title continued into source footage/captions. This is
  not full real-time animation or audio-quality acceptance.
- Import showed a missing Poppins-SemiBold warning from the vendor template.
  Exposed populated text slots read back ABAR and the inspected Properties font
  was ABAR; hidden/internal dependency cleanup remains unverified.

## Saved-file verification

`saved-native-verification.json` confirms all 147 edit entries on each of V1/V2/A1/A2
match the engine XML clocks, 12 graphic instances match plan clocks, six SFX match
frame ranges, and all 142 caption texts are byte-exact to the supplied SRT.

The verifier intentionally returns failure: caption 142's END differs by
0.0335666667 seconds (1.005994 frames), just beyond its strict one-frame threshold.
Other checked caption boundaries are within tolerance. This issue is recorded,
not repaired or silently waived. The source ASR text itself still needs editorial
review; byte equality does not mean the words are accurate.

Evidence in the same package: `native-dispatch.json`, `native-receipt.json`,
`inspect-request.json`, `inspect-receipt.json`, `saved-native-verification.json`.
Do not resend the dispatch or overwrite this proof. PublicationReady remains false.

## Remaining

Full animation-phase QA for all six composites; internal font warning; subtitle
wording/typography and final boundary; chart/table/subscribe roles; normal desktop
fresh-input E2E and final owner visual approval. The old app shortcut is unchanged.
Computer Use skill was used for native visual/Properties verification.

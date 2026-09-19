# Hafez Studio architecture

## Layers

1. **Desktop shell** — Electron UI, settings, file picking, progress and job control.
2. **Hafez Video Engine** — Python analysis, synchronization, subtitles, director decisions, audio mastering, graphics and XML generation.
3. **Hafez Motion Pack** — original After Effects compositions exported as editable MOGRTs.
4. **Premiere Finisher** — UXP panel that reads the versioned Premiere plan and places/configures MOGRTs.
5. **Adapters** — optional n8n and Telegram integration. They are not imported by the core engine.

## Production workspaces

- **YouTube** is the active production engine and current quality gate.
- **Reels** is visible as phase 2 but remains inactive until YouTube approval.
- **Podcast** is visible as phase 3 and will be designed after Reels.

The desktop interface ships with persisted dark/light themes, adaptive Hafez
monograms and a bundled Estedad variable UI font.

## Stable contracts

- `hermes-professional-edit-v1`: Premiere plan consumed by the UXP plugin.
- `hermes-ai-tasks-v1`: chunked AI review contract.
- `settings.json` version 1: portable user preferences with no credentials.
- Job stdout emits `HERMES_PROGRESS <0..100>`, `HERMES_ERROR`, and final JSON.

## Security

- The renderer has no Node.js access. Electron uses an isolated preload bridge.
- API and Telegram credentials are intentionally excluded from settings and project bundles.
- Personal Telegram traffic stays behind the existing owner gate.
- Trading, MetaTrader and Postgres are outside this product boundary.

## Audio invariant

Camera 1 is the sole dialogue source. Camera 2 audio is always disabled. The Voice Master is built only from camera 1 and placed as the active Premiere audio track.

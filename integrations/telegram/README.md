# Personal Telegram integration

The first release reuses the existing n8n Telegram owner gate so no token is copied or exposed. Future standalone Telegram support will use an OS credential-store adapter and an explicit allowlist configured during first-run setup.

Telegram is an input/output surface; it is not part of the core editing engine.

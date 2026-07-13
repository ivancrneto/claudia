# Companion Portal

The web/phone companion for Claudia. It keeps API credentials **off the kiosk tablet**.

Responsibilities:

1. **Sign in** to Claudia.
2. **Connect an assistant** — add a provider **API key** or run **OAuth** (Anthropic,
   OpenAI, Gemini, or any OpenAI-compatible endpoint / OpenRouter).
   > Consumer ChatGPT Plus / Claude Pro subscriptions are **not** usable here — only
   > provider **API** accounts are (see `ARCHITECTURE.md` §6).
3. **Pair a device** — show a QR / short code; the tablet scans it and the server links
   `device_id → user_id` (see `services/accounts/pairing.py`). The key stays server-side,
   KMS-encrypted (see `services/accounts/vault.py`).
4. **Usage & budgets** — per-user quotas and spend, since it's the user's own key.

> Placeholder — implemented in Phase 3.5. Framework TBD (Next.js recommended).

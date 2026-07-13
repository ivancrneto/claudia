# Roadmap

Incremental build phases. Each phase is independently demoable.

## Phase 0 — Skeleton (this scaffold)
- FastAPI gateway with a `/dev/handle` text endpoint (no audio yet).
- Skills SDK: base class, manifest loader, dispatcher.
- Stub skills: `timer`, `weather`, `futebol` (with team resolution).
- Brain provider abstraction with a working `OpenAICompatAdapter` + `LocalAdapter`.
- Kiosk native-module stubs (Android + iOS).
- `docker-compose` for the self-hosted stack.

## Phase 1 — Core voice pipeline
- faster-whisper STT + Piper TTS wired into the gateway over WebSocket.
- Hybrid NLU router (fast intent grammar → LLM fallback).
- Skills: music, weather, YouTube (device actions).

## Phase 2 — Futebol
- Team resolver (Série A/B + nicknames + fuzzy match, disambiguation).
- `FootballProvider` (API-Football) + scheduled fixture ingestion worker.

## Phase 2.5 — Kiosk hardening
- Android Device Owner + Lock Task Mode; iOS Single App Mode + ASAM.
- Companion provisioning flows (QR / Configurator / MDM).

## Phase 3 — Voice UX
- openWakeWord ("Ei Claudia"), streaming partials, barge-in, multi-turn.

## Phase 3.5 — Bring Your Own Assistant
- Ship `LocalAdapter` + `OpenAICompatAdapter` first (local + OpenRouter/most providers).
- Add Anthropic / OpenAI / Gemini adapters + OAuth flows.
- Account Vault (KMS) + companion portal + QR device pairing.
- Skill→tool bridge (MCP + function-calling).

## Phase 4 — Personalization
- Favorite team, per-user profiles (voice-match / PIN), budgets/quotas.
- Analytics: `intent_used` events to measure the most-used asks.

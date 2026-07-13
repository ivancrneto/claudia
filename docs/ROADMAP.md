# Roadmap

Incremental build phases. Each phase is independently demoable.

## Phase 0 — Skeleton (this scaffold)
- FastAPI gateway with a `/dev/handle` text endpoint (no audio yet).
- Skills SDK: base class, manifest loader, dispatcher.
- Stub skills: `timer`, `weather`, `futebol` (with team resolution).
- Brain provider abstraction with a working `OpenAICompatAdapter` + `LocalAdapter`.
- Kiosk native-module stubs (Android + iOS).
- `docker-compose` for the self-hosted stack.

## Phase 1 — Core voice pipeline ✅ (in progress)
- ✅ `VoicePipeline` turn orchestrator: audio → STT → hybrid NLU → skills/brain → TTS →
  audio + device actions. Adapters injected, so it's fully testable offline.
- ✅ STT adapters: `FasterWhisperSTT` (model call stubbed at the boundary) + offline
  `EchoTextSTT`/`FixedSTT`. TTS adapters: `PiperTTS` (stubbed) + offline `StubTTS`.
- ✅ `HybridRouter`: fast grammar first, optional LLM classifier on a miss, else brain Q&A.
- ✅ Gateway endpoints: `POST /dev/turn` (base64 audio) and `WS /ws/voice` (binary frames).
- ⏳ Follow-ups: real faster-whisper/Piper decode, Open-Meteo weather, YouTube device action.

## Phase 2 — Futebol ✅ (in progress)
- ✅ Team resolver: Série A roster + nicknames + article-stripping + fuzzy match, with
  multi-club disambiguation (Tricolor / Leão / Alvinegro) resolved by favorite team.
- ✅ `FootballProvider` interface with `APIFootballProvider` (API-Football; team-id
  resolved by name and cached — no hardcoded third-party ids) and an offline `StubProvider`.
- ✅ Fixture cache + `FixtureIngestionWorker`; gateway primes it at startup (cache-first).
- ✅ PT-BR kickoff humanization ("hoje às 18h30", "amanhã", "no próximo sábado").
- ⏳ Follow-ups: Redis-backed cache + cron schedule, per-club timezones, Série B + cups.

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

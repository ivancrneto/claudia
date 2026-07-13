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

## Phase 3 — Voice UX ✅ (in progress)
- ✅ Wake word: `WakeWord` protocol, `OpenWakeWord` (inference stubbed at the boundary) +
  offline `KeywordWakeWord`.
- ✅ Streaming STT: `StreamingSTT` protocol emitting growing `Partial`s + a final; offline
  `EchoStreamingSTT`.
- ✅ `VoiceSession` state machine (IDLE→LISTENING→THINKING→SPEAKING) with **barge-in** that
  cancels TTS playback mid-reply and yields the floor back to LISTENING.
- ⏳ Follow-ups: real openWakeWord + faster-whisper streaming decode, VAD endpointing,
  early-intent on a stable prefix, and a streaming `WS /ws/voice` that emits partials.

## Phase 3.5 — Bring Your Own Assistant ✅ (in progress)
- ✅ Native adapters: `AnthropicAdapter`, `OpenAIAdapter`, `GeminiAdapter`, plus
  `OpenAICompatAdapter` (OpenRouter/Groq/Together/Ollama). Shared SSE transport (injected,
  so streaming is unit-tested offline); streaming text + tool-call parsing per provider.
- ✅ Skill→tool bridge translation: neutral schema → Anthropic / OpenAI / Gemini formats.
- ✅ Brain router selects the adapter by `kind`, falling back to the local brain.
- ✅ Account Vault with a pluggable `Cipher` (`FernetCipher` in prod, lazy-imported);
  credentials encrypted at rest, decrypted server-side into a brain config.
- ⏳ Follow-ups: provider OAuth flows, KMS-backed key + Postgres store, companion portal
  UI, single-use/expiring pairing codes, streaming tool-call argument assembly.

## Phase 4 — Personalization
- Favorite team, per-user profiles (voice-match / PIN), budgets/quotas.
- Analytics: `intent_used` events to measure the most-used asks.

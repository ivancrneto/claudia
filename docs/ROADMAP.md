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
- ⏳ Follow-ups: real faster-whisper/Piper decode.

## Core skills — the common asks ✅
- ✅ **Weather**: real Open-Meteo (free, no key), WMO code → PT-BR, forecast spoken from the
  device's location; injectable HTTP so it's tested offline.
- ✅ **YouTube**: `OPEN_YOUTUBE` → `open_youtube` device action (with/without a search query).
- ✅ **Music**: `PLAY_MUSIC` → `play_music` device action.
- ✅ NLU routes them deterministically (YouTube before the generic "toca …" music rule);
  timer + futebol round out the four most-common asks.

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

## Deployment — public-repo posture ✅ (in progress)
- ✅ Central `services/config.py` (12-factor): all config from env, no secrets in code,
  prod fails fast on missing required secrets, `__repr__` redacts secret values.
- ✅ `.env.example` (keys only), `.gitignore` hardened (real `.env`, keys, model weights),
  `SECURITY.md`, and `docs/DEPLOYMENT.md` (external secret manager + VPS/Compose).
- ✅ `infra/docker-compose.prod.yml` + `Caddyfile`: secrets from an env file mounted OUTSIDE
  the repo (`CLAUDIA_ENV_FILE`); Caddy terminates TLS in front of the gateway.
- ✅ CI `secret-scan` gate (gitleaks) so no secret can land in the public repo; test job
  needs no credentials (all stubs).
- ⏳ Follow-ups: cloud secret-manager fetch script, GitHub Actions deploy via OIDC.

## Android build & release ✅ (in progress)
- ✅ Gradle build config with `kiosk` (APK, MDM/sideload) and `consumer` (AAB, Play) flavors;
  manifest wires the Device Owner admin, boot receiver, and a11y fallback + reuses the kiosk
  native modules.
- ✅ Release signing from the environment only (Play App Signing + upload key from CI
  secrets); nothing sensitive in the repo.
- ✅ **Buildkite** signed-release pipeline (modeled on izap's `.buildkite/`): block gate →
  containerized SDK build in `eclipse-temurin` → both flavors → artifacts + optional Play
  upload. Cluster secrets use izap's names. (Replaces the earlier GitHub Actions release;
  PR CI stays on Actions.) `tools/android_version.py` unit-tested.
- ✅ `docs/ANDROID_RELEASE.md`, `.gitignore` hardened for keystores/Play creds/build outputs.
- ⏳ Follow-ups: the React Native / voice UI mounted in `MainActivity`, screenshots/metadata
  for Play, and a full Gradle build in CI (needs the Android SDK).

## Phase 4 — Personalization ✅ (in progress)
- ✅ Per-user `Profile` (favorite team, locale, city, coords) merged into the turn context;
  request values override the stored profile. Powers futebol favorite-team disambiguation
  and weather location. `POST /profile` upserts.
- ✅ Analytics: pipeline emits an **anonymized** `intent_used` event per turn (intent /
  source / locale only — no transcript, no PII). Sinks: `MemoryAnalytics`, `PostHogAnalytics`
  (HTTP injected, errors swallowed), `NullAnalytics`. `GET /dev/stats` shows the most-used
  asks — the assistant measuring itself.
- ⏳ Follow-ups: voice-match / spoken-PIN identification, per-user budgets/quotas, Postgres
  profile store.

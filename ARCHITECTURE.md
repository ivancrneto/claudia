# Claudia — Architecture

A self-hosted, voice-first assistant (an open alternative to Alexa), PT-BR first, that
covers the most common voice asks and adds custom skills — starting with Brazilian
football fixtures. Users can connect their own AI assistant (Claude, ChatGPT, Gemini, or
a local model) as the reasoning brain, and the whole thing can be locked onto a tablet in
kiosk mode.

## 1. Design principles

1. **Thin client, smart backend.** The phone/tablet captures audio, runs only the wake
   word locally, and executes *device-native* actions (open YouTube, OS timer, launch a
   music app). Everything cognitive runs on the backend.
2. **80/20 skills.** ~5 built-in skills cover the bulk of real usage (music, timers,
   weather, YouTube, general Q&A). The **futebol** skill is the first *custom* skill and
   proves the extensibility model.
3. **Alexa-style Skills Kit.** Every capability is a pluggable skill: a manifest (intents +
   sample utterances + slots) plus a handler. Adding a skill is dropping a folder in
   `skills/`.
4. **Bring Your Own Assistant.** The reasoning brain is pluggable. A local PT-BR model is
   the default/guest brain; users can connect their own provider account.
5. **Latency budget < 1.5s** perceived: stream wake → STT partials → early intent →
   streaming TTS, with barge-in.

## 2. High-level flow

```
MOBILE APP (iOS/Android)
  Mic → [openWakeWord "Ei Claudia" · on-device] → stream audio (Opus)
  Plays TTS audio · executes DEVICE ACTIONS: open_youtube / set_os_timer / play_music
        │ audio in                                   ▲ audio out + action JSON
        ▼                                            │
VOICE GATEWAY (FastAPI, async) — session · streaming I/O · barge-in
   ├─▶ STT (faster-whisper, PT-BR)
   ├─▶ NLU / ROUTER (hybrid: fast intent grammar → LLM fallback)
   ├─▶ SKILL DISPATCHER ─▶ [music][timer][weather][youtube][futebol][qa]
   ├─▶ BRAIN ROUTER ─▶ Local / Anthropic / OpenAI / Gemini / OpenAI-compatible
   └─▶ TTS (Piper, pt_BR)
   shared: Postgres (users/prefs/teams) · Redis (session/fixture cache)
```

## 3. Component choices (self-hosted OSS)

| Layer | Pick | Why |
|---|---|---|
| Wake word | **openWakeWord** (on-device) | Fully OSS; custom "Ei Claudia" model; avoids 24/7 streaming |
| STT | **faster-whisper** (`large-v3` GPU / `medium` for speed) | Best OSS PT-BR accuracy; streaming partials |
| NLU / router | **Hybrid**: fast intent grammar (Rhasspy/Snips-style) → local LLM fallback | Deterministic + fast for commands, LLM for open-ended |
| LLM serving | **Ollama / vLLM** (Qwen2.5-7B / Llama-3.1-8B, or PT-BR tune) | Intent, slots, general Q&A, phrasing |
| TTS | **Piper** (`pt_BR` voice) | Fast on CPU, streamable; upgrade to Coqui XTTS for fidelity |
| Orchestrator | **Python + FastAPI**, async, WebSocket | Session + dialog state |
| State/data | **Postgres** + **Redis** | Users/prefs/teams; session + fixture cache |
| Infra | **Docker Compose** → k8s; one GPU node | STT + LLM |

## 4. Skills Kit

A skill = **manifest + handler**, mirroring Alexa's model.

```yaml
# skills/futebol/manifest.yaml
name: futebol
locale: pt-BR
intents:
  - name: PROXIMO_JOGO
    utterances:
      - "quando o {time} joga"
      - "quando é o próximo jogo do {time}"
    slots:
      time: { type: BR_FOOTBALL_TEAM }
```

```python
class FutebolSkill(Skill):
    def can_handle(self, req): return req.intent == "PROXIMO_JOGO"
    async def handle(self, req):
        team = resolve_team(req.slot("time"))
        fx = await provider.next_fixture(team)
        return Response.speak(f"O {team.name} joga {fx.human_pt}, contra o {fx.opponent}.")
```

The dispatcher asks each registered skill `can_handle(intent)` and routes to the first match.

## 5. The ⚽ futebol skill (the interesting custom one)

- **Team resolution** — the hard part. "Bahia", "Esquadrão", "Tricolor de Aço" → EC Bahia.
  A `BR_FOOTBALL_TEAM` slot type: curated dictionary of Série A/B teams + nicknames + fuzzy
  match. Disambiguate collisions (e.g. "Tricolor") via a follow-up or the user's favorite team.
- **Data source** — pluggable `FootballProvider`. Default: API-Football (Brasileirão A/B,
  Copa do Brasil, Libertadores); alternative Football-Data.org.
- **Ingestion, not live calls** — a scheduled worker pulls fixtures for followed teams into
  Postgres/Redis, so answers are instant and rate limits aren't hit per request.
- **Timezone** — normalize to `America/Bahia` / `America/Sao_Paulo`; speak local kickoff.

## 6. Bring Your Own Assistant (BYOA)

> **Subscriptions vs API:** consumer ChatGPT Plus / Claude Pro are *not* programmatically
> accessible. The connection unit is a provider **API credential** (API key, or OAuth where
> offered). Reusing consumer logins violates ToS and is unsupported.

**Provider abstraction** — one interface, many backends:

- `LocalAdapter` — self-hosted PT-BR model (default/guest brain).
- `AnthropicAdapter` — Claude (Messages API + tool use / MCP).
- `OpenAIAdapter` — ChatGPT models (Responses / Chat Completions + function calling).
- `GeminiAdapter` — Google.
- `OpenAICompatAdapter` — OpenRouter, Groq, Together, Ollama, LM Studio, local — one
  integration covers dozens of providers.

**Account Vault** — credentials never live on the kiosk. A companion web/phone portal does
sign-in / OAuth / key entry and issues a **QR pairing code**; the tablet scans it and the
server links the device to server-side, KMS-encrypted, per-user credentials.

**Tool bridge** — skills are exposed to the connected brain as callable tools (Anthropic
tool use / MCP, OpenAI function calling, Gemini function declarations), defined once
internally. So the user's Claude/GPT can actually set a timer or answer "quando o Bahia
joga" by calling a skill — modeled as an **MCP server** so new skills need no per-provider work.

**Brain routing** — direct commands ("põe um timer de 10 minutos") stay **local** and
instant; open Q&A / reasoning routes to the **connected brain** (which may call skills back
through the bridge); with no account connected, it falls back to the **local** PT-BR model,
so Claudia always works.

**Shared-tablet identity** — device-default account plus optional per-user profiles
(voice-match / spoken PIN), per-user budgets/quotas, and explicit consent when a request
leaves the device.

## 7. Kiosk / locked-tablet mode

Client-side only; the backend is unchanged.

### Android — Device Owner + Lock Task Mode (primary)
Provision as **Device Owner** on a factory-reset tablet, then `startLockTask()` pins the
app; `DevicePolicyManager` (COSU) hides the status bar/keyguard, blocks uninstall/factory
reset/Safe Mode, makes Claudia the Home launcher, and auto-starts on boot.
`AccessibilityService` is a **fallback only** (Play-policy risk — sideload/MDM, not Store).
Provision via ADB, Headwind MDM, or the Android Management API.

### iOS — Single App Mode + ASAM (primary)
No `AccessibilityService` equivalent — MDM + **Supervision** is mandatory. **Single App
Mode** (MDM payload) hard-locks to Claudia; **Autonomous Single App Mode** lets the app
lock/unlock itself via `UIAccessibility.requestGuidedAccessSession(enabled:)` (admin PIN to
release). **Guided Access** is the manual, no-MDM option (demo only). Provision via Apple
Configurator, ABM + Automated Device Enrollment, or MicroMDM.

### Genuine accessibility (worth building anyway)
Full voice-only operation, TalkBack/VoiceOver support, large targets, high-contrast/large
text, spoken confirmations.

| Capability | Android | iOS |
|---|---|---|
| Manual, no infra | Screen pinning | Guided Access |
| Robust kiosk lock | Device Owner + Lock Task | Single App Mode (MDM, supervised) |
| App locks itself | `startLockTask()` | ASAM |
| Policeman fallback | AccessibilityService (policy risk) | none — MDM mandatory |

## 8. Cross-cutting

- **Privacy:** wake word on-device, audio not persisted by default, TLS everywhere,
  local-only mode available.
- **Latency:** Whisper partials → early intent → streaming Piper → barge-in.
- **Analytics:** emit anonymized `intent_used` events (e.g. to PostHog) — this is how you
  measure your own "most used asks" over time.
- **Security:** credentials KMS-encrypted, OAuth over raw keys where possible, never log
  prompts alongside credentials.

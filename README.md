# Claudia

An open, self-hosted, voice-first assistant — a "bring your own brain" alternative to
Alexa. Designed around the asks people actually make (music, timers, weather, opening
YouTube, general questions) plus custom skills — starting with **Brazilian football
fixtures** ("quando o Bahia joga?").

- 🎙️ **Voice-first, PT-BR first** — on-device wake word, self-hosted STT/TTS.
- 🧩 **Alexa-style Skills Kit** — every capability is a pluggable skill (manifest + handler).
- 🧠 **Bring Your Own Assistant (BYOA)** — connect your own Claude, ChatGPT, Gemini,
  or a local model as the reasoning brain.
- 🔒 **Kiosk mode** — lock a tablet to Claudia (Android Device Owner / iOS Single App Mode)
  so it can't be closed.

> **Status:** Phase 0 scaffold. See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full design
> and [`docs/ROADMAP.md`](./docs/ROADMAP.md) for the build phases.

## Repository layout

```
services/
├── gateway/     FastAPI orchestrator (session, audio in/out, routing)
├── brain/       BYOA provider abstraction + brain router + skill→tool bridge
└── accounts/    encrypted credential vault + device pairing
skills/
├── _sdk/        Skill base class, manifest loader, dispatcher
├── timer/  weather/   built-in skills
└── futebol/     Brazilian football fixtures (custom skill)
apps/
├── mobile/      thin client + kiosk native modules (Android/iOS)
└── companion-web/  connect-your-assistant portal + device pairing
infra/           docker-compose for the self-hosted stack
```

## Quickstart (Phase 0)

```bash
cd services/gateway
pip install -r requirements.txt
uvicorn app:app --reload
# POST a transcript to exercise the skill dispatcher without the voice pipeline:
curl -s localhost:8000/dev/handle -H 'content-type: application/json' \
  -d '{"text": "quando o Bahia joga?"}'
```

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the voice pipeline, kiosk, and BYOA design.

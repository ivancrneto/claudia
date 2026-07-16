"""Claudia gateway.

Runs the full voice turn pipeline (audio → STT → hybrid NLU → skills/brain → TTS) behind:
- `POST /dev/handle` — text in, structured out (no audio); quickest way to exercise routing.
- `POST /dev/turn`   — base64 audio in, transcript + base64 reply audio out.
- `WS   /ws/voice`   — binary audio frames in, JSON result + reply audio out.

STT/TTS default to offline stubs so everything runs without models; set STT_BACKEND=whisper
/ TTS_BACKEND=piper to use the real self-hosted adapters in deployment.

Futebol runs cache-first: an ingestion sweep at startup fills a fixtures cache for the
followed teams. With API_FOOTBALL_KEY set it uses the live provider; else the offline stub.
"""

from __future__ import annotations

import base64
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make the repo root importable (skills/, services/ are top-level packages).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from services.analytics import MemoryAnalytics, PostHogAnalytics  # noqa: E402
from services.config import Settings  # noqa: E402
from services.gateway.pipeline import VoicePipeline  # noqa: E402
from services.profiles import InMemoryProfileStore, Profile  # noqa: E402
from services.stt import EchoTextSTT, FasterWhisperSTT  # noqa: E402
from services.tts import PiperTTS, StubTTS  # noqa: E402
from skills._sdk import Dispatcher  # noqa: E402
from skills.futebol.handler import FutebolSkill  # noqa: E402
from skills.futebol.ingestion import FixtureIngestionWorker, InMemoryFixtureCache  # noqa: E402
from skills.futebol.provider import APIFootballProvider, StubProvider  # noqa: E402
from skills.futebol.teams import TEAMS  # noqa: E402
from skills.music.handler import MusicSkill  # noqa: E402
from skills.timer.handler import TimerSkill  # noqa: E402
from skills.weather.handler import WeatherSkill  # noqa: E402
from skills.youtube.handler import YouTubeSkill  # noqa: E402

settings = Settings.from_env()
_FUTEBOL_CACHE = InMemoryFixtureCache()


def _football_provider():
    if settings.api_football_key:
        return APIFootballProvider(
            api_key=settings.api_football_key, season=settings.football_season
        )
    return StubProvider()


def _make_stt():
    return FasterWhisperSTT() if settings.stt_backend == "whisper" else EchoTextSTT()


def _make_tts():
    return PiperTTS() if settings.tts_backend == "piper" else StubTTS()


def _make_analytics():
    # PostHog when a capture key is set; otherwise the in-memory sink (powers /dev/stats).
    if settings.posthog_api_key:
        return PostHogAnalytics(settings.posthog_api_key, host=settings.posthog_host)
    return MemoryAnalytics()


_football = _football_provider()
profiles = InMemoryProfileStore()
analytics = _make_analytics()
dispatcher = Dispatcher(
    [
        TimerSkill(),
        WeatherSkill(),
        YouTubeSkill(),
        MusicSkill(),
        FutebolSkill(provider=_football, cache=_FUTEBOL_CACHE),
    ]
)
pipeline = VoicePipeline(dispatcher, stt=_make_stt(), tts=_make_tts(), analytics=analytics)


def _resolve_context(body_user: dict) -> dict:
    """Merge a stored profile (by user_id) under the request-provided context."""
    ctx: dict = {}
    user_id = body_user.get("user_id")
    if user_id:
        profile = profiles.get(user_id)
        if profile:
            ctx.update(profile.to_context())
    ctx.update(body_user)  # request values override the stored profile
    return ctx


async def _prime_fixtures() -> None:
    # Followed teams default to the full roster; production scopes this to users' follows.
    worker = FixtureIngestionWorker(_football, _FUTEBOL_CACHE, TEAMS)
    await worker.run_once()


@asynccontextmanager
async def _lifespan(_app: "FastAPI"):
    settings.validate()  # fail fast in prod if a required secret is missing
    await _prime_fixtures()
    yield


app = FastAPI(title="Claudia Gateway", version="0.5.2", lifespan=_lifespan)


class HandleIn(BaseModel):
    text: str
    user: dict = {}


class HandleOut(BaseModel):
    transcript: str
    intent: str
    speech: str
    actions: list = []
    source: str  # "skill" | "brain"


class TurnIn(BaseModel):
    audio_b64: str
    user: dict = {}


class TurnOut(HandleOut):
    audio_b64: str


class ProfileIn(BaseModel):
    user_id: str
    locale: str = "pt-BR"
    favorite_team_id: int | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None


_INDEX_HTML = """<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Claudia</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:system-ui,-apple-system,sans-serif; background:#0f1115; color:#e8eaed;
         display:flex; flex-direction:column; height:100dvh; }
  header { padding:14px 16px; font-weight:600; border-bottom:1px solid #23262d; }
  #log { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:10px; }
  .msg { max-width:82%; padding:10px 13px; border-radius:14px; line-height:1.35; white-space:pre-wrap; }
  .me { align-self:flex-end; background:#2b6cff; color:#fff; border-bottom-right-radius:4px; }
  .bot { align-self:flex-start; background:#1b1e25; border:1px solid #23262d; border-bottom-left-radius:4px; }
  .act { align-self:flex-start; font-size:12px; color:#9aa4b2; padding:2px 4px; }
  .ghost { align-self:flex-end; opacity:.55; font-style:italic; }
  #status { text-align:center; font-size:13px; color:#9aa4b2; min-height:18px; padding:4px 0; }
  form { display:flex; gap:8px; align-items:center; padding:12px; border-top:1px solid #23262d; }
  input { flex:1; padding:12px 14px; border-radius:12px; border:1px solid #2a2e37; background:#151821; color:#e8eaed; font-size:16px; }
  button { padding:12px 16px; border:0; border-radius:12px; background:#2b6cff; color:#fff; font-size:16px; }
  /* Mic button: a round tap-to-talk control that reflects the voice state. */
  #mic { width:52px; height:52px; padding:0; border-radius:50%; background:#1b1e25; border:1px solid #2a2e37;
         font-size:22px; line-height:1; flex:0 0 auto; transition:background .15s, box-shadow .15s; }
  #mic.listening { background:#c0392b; box-shadow:0 0 0 0 rgba(192,57,43,.6); animation:pulse 1.2s infinite; }
  #mic.speaking  { background:#2b6cff; }
  #mic.thinking  { background:#7a5cff; }
  #mic.wake      { background:#1f7a4d; box-shadow:0 0 0 0 rgba(31,122,77,.5); animation:pulse-wake 2.4s infinite; }
  @keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(192,57,43,.55)} 70%{box-shadow:0 0 0 16px rgba(192,57,43,0)} 100%{box-shadow:0 0 0 0 rgba(192,57,43,0)} }
  @keyframes pulse-wake { 0%{box-shadow:0 0 0 0 rgba(31,122,77,.5)} 70%{box-shadow:0 0 0 12px rgba(31,122,77,0)} 100%{box-shadow:0 0 0 0 rgba(31,122,77,0)} }
</style></head><body>
<header>Claudia</header>
<div id="log"><div class="msg bot">Oi, eu sou a Claudia! 👋 Toque no 🎙️ para ativar o modo "Claudia" e fale sem tocar — "Claudia, quando o Bahia joga", "Claudia, toca Bruno Mars", "como está o tempo"… ou digite.</div></div>
<div id="status"></div>
<form id="f">
  <button id="mic" type="button" aria-label="Falar" title="Falar">🎙️</button>
  <input id="t" autocomplete="off" placeholder="Fale com a Claudia…">
  <button type="submit">Enviar</button>
</form>
<script>
  const log = document.getElementById('log'), f = document.getElementById('f'),
        t = document.getElementById('t'), mic = document.getElementById('mic'),
        statusEl = document.getElementById('status');
  const native = window.AndroidVoice;   // present inside the app's WebView
  const canWake = !!(native && native.startWake);   // always-listening wake word (app only)
  const WAKE_HINT = 'Diga "Claudia"…';

  const add = (text, cls) => { const d = document.createElement('div'); d.className = 'msg ' + cls; d.textContent = text; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; };
  const setStatus = (s) => { statusEl.textContent = s || ''; };

  // --- partial (interim) transcript preview -------------------------------
  let ghost = null;
  const showPartial = (txt) => { if (!ghost) ghost = add('', 'msg ghost'); ghost.textContent = txt; log.scrollTop = log.scrollHeight; };
  const clearPartial = () => { if (ghost) { ghost.remove(); ghost = null; } };

  // --- voice state machine -------------------------------------------------
  let handsFree = false;   // tap-to-talk conversation mode: keep listening after each reply
  let wakeMode = false;    // always-listening wake word ("Claudia") is armed
  let silence = 0;         // consecutive empty/no-match results, to avoid an endless mic loop
  const STATES = { idle:'', listening:'listening', thinking:'thinking', speaking:'speaking' };
  let state = 'idle';
  const LABEL = { idle:'', listening:'Ouvindo…', thinking:'Pensando…', speaking:'Falando…' };
  function setState(s) {
    state = s;
    mic.className = (s === 'idle' && wakeMode) ? 'wake' : (STATES[s] || '');
    mic.textContent = (s !== 'idle') ? (s === 'speaking' ? '🔊' : '⏹️') : (wakeMode ? '👂' : '🎙️');
    // In wake mode the idle state is "still listening for the wake word", not blank.
    setStatus((s === 'idle' && wakeMode) ? WAKE_HINT : LABEL[s]);
  }

  // --- speak / listen, native bridge with a Web Speech API fallback --------
  let webRec = null;
  function speak(text) {
    if (native) { native.speak(text); return; }
    if (window.speechSynthesis) {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = 'pt-BR';
      const v = (speechSynthesis.getVoices() || []).find(v => /pt(-|_)?BR/i.test(v.lang));
      if (v) u.voice = v;
      u.onstart = () => ClaudiaVoice.onSpeakStart();
      u.onend = () => ClaudiaVoice.onSpeakDone();
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    } else { ClaudiaVoice.onSpeakDone(); }
  }
  function listen() {
    if (native) { native.listen(); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setStatus('Voz não suportada neste navegador — digite abaixo.'); handsFree = false; setState('idle'); return; }
    webRec = new SR();
    webRec.lang = 'pt-BR'; webRec.interimResults = true; webRec.maxAlternatives = 1;
    webRec.onstart = () => ClaudiaVoice.onListenStart();
    webRec.onerror = (e) => ClaudiaVoice.onError('web-' + e.error);
    webRec.onresult = (e) => {
      let interim = '', finalT = '';
      for (const r of e.results) { if (r.isFinal) finalT += r[0].transcript; else interim += r[0].transcript; }
      if (interim) ClaudiaVoice.onPartial(interim);
      if (finalT) ClaudiaVoice.onResult(finalT);
    };
    try { webRec.start(); } catch (_) {}
  }
  function stopListen() { if (native) native.stopListening(); else if (webRec) { try { webRec.stop(); } catch (_) {} } }
  function cancelAll() { handsFree = false; stopListen(); if (native) native.cancel(); else if (window.speechSynthesis) speechSynthesis.cancel(); setState('idle'); }

  // --- callbacks invoked by the native bridge (and reused by the web path) -
  window.ClaudiaVoice = {
    onListenStart() { silence = 0; setState('listening'); },
    onPartial(txt) { showPartial(txt); },
    onListenEnd() { if (state === 'listening') setState('thinking'); },
    // Wake word heard. The native loop passes any trailing command ("Claudia, que horas são");
    // if it's empty we actively capture the follow-up utterance.
    onWake(command) {
      clearPartial();
      command = (command || '').trim();
      if (command) { setState('thinking'); add(command, 'me'); ask(command); }
      else { setState('listening'); listen(); }
    },
    onResult(txt) {
      clearPartial();
      txt = (txt || '').trim();
      if (!txt) {
        // Nothing heard. In wake mode the native side keeps the loop alive; just show the hint.
        if (wakeMode) { setState('idle'); return; }
        if (handsFree && silence++ < 2) { setState('idle'); listen(); } else { handsFree = false; setState('idle'); }
        return;
      }
      add(txt, 'me'); ask(txt);
    },
    onError(code) {
      clearPartial();
      // In wake mode the native loop recovers on its own — stay armed.
      if (wakeMode) { setState('idle'); return; }
      const soft = /(-6|-7|no-speech|no-match|aborted|speech-timeout)/i.test(code || '');
      if (handsFree && soft && silence++ < 2) { setState('idle'); listen(); return; }
      if (/mic-permission|not-allowed|denied/i.test(code)) setStatus('Permita o microfone para usar voz.');
      else if (/no-recognizer|not-supported|service-not-allowed/i.test(code)) setStatus('Reconhecimento de voz indisponível.');
      handsFree = false; silence = 0; setState('idle');
    },
    onSpeakStart() { setState('speaking'); },
    // After speaking: wake mode resumes on the native side (don't double-listen); tap-to-talk
    // re-listens here.
    onSpeakDone() { if (wakeMode) setState('idle'); else if (handsFree) { setState('idle'); listen(); } else setState('idle'); },
    onMicGranted() { if (wakeMode) native.startWake(); else if (handsFree) listen(); },
    onMicDenied() { handsFree = false; wakeMode = false; setState('idle'); setStatus('Permita o microfone para usar voz.'); },
  };

  // --- the brain turn: text in -> gateway -> spoken reply ------------------
  async function ask(text) {
    silence = 0; setState('thinking');
    try {
      const r = await fetch('/dev/handle', { method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({ text, user: { user_id: 'device' } }) });
      const data = await r.json();
      const speech = data.speech || '(sem resposta)';
      add(speech, 'bot');
      (data.actions || []).forEach(a => add('⚙ ' + a.type + (a.params && a.params.query ? ': ' + a.params.query : ''), 'act'));
      speak(speech);   // onSpeakDone re-listens when handsFree
    } catch (err) { add('Erro ao falar com o servidor: ' + err, 'bot'); handsFree = false; setState('idle'); }
  }

  // Mic button:
  //  - in the app (wake word available): arm/disarm always-listening. Then just say "Claudia".
  //  - in the browser: tap-to-talk hands-free conversation.
  mic.addEventListener('click', () => {
    if (canWake) {
      if (wakeMode || state !== 'idle') {
        wakeMode = false; native.stopWake(); native.cancel && native.cancel();
        setState('idle'); setStatus('');
      } else {
        wakeMode = true; silence = 0; setState('idle'); native.startWake();
      }
      return;
    }
    if (handsFree || state !== 'idle') { cancelAll(); return; }
    handsFree = true; silence = 0; listen();
  });

  // Typing is always available and runs a single turn (without disarming the wake word).
  f.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = t.value.trim(); if (!text) return;
    handsFree = false; t.value = '';
    add(text, 'me'); ask(text);
  });

  // Auto-arm the wake word on load so the app is hands-free from the start — no tap, just say
  // "Claudia" (Alexa-style). Native STT/TTS run with the app's mic permission, so no browser
  // gesture is needed. In a plain browser (no bridge) autoplay/mic policies block this, so we
  // leave tap-to-talk there. Tapping the mic still disarms/re-arms.
  if (canWake) {
    wakeMode = true;
    const greet = document.querySelector('.msg.bot');
    if (greet) greet.textContent = 'Oi! Já estou ouvindo 👂 — é só dizer "Claudia" (ex.: "Claudia, quando o Bahia joga"). Também dá pra digitar.';
    setState('idle');        // shows the 👂 "Diga Claudia…" armed state
    native.startWake();      // if the mic isn't granted yet, onMicGranted re-arms
  }
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Minimal web client — usable from a phone browser or the app's WebView."""
    return _INDEX_HTML


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "skills": [s.name for s in dispatcher.skills],
        "stt": pipeline._stt.name,
        "tts": pipeline._tts.name,
    }


@app.post("/dev/handle", response_model=HandleOut)
async def dev_handle(body: HandleIn) -> HandleOut:
    r = await pipeline.run_text(body.text, _resolve_context(body.user))
    return HandleOut(
        transcript=r.transcript,
        intent=r.intent,
        speech=r.speech,
        actions=r.actions,
        source=r.source,
    )


@app.post("/dev/turn", response_model=TurnOut)
async def dev_turn(body: TurnIn) -> TurnOut:
    audio = base64.b64decode(body.audio_b64)
    r = await pipeline.run_audio(audio, _resolve_context(body.user))
    return TurnOut(
        transcript=r.transcript,
        intent=r.intent,
        speech=r.speech,
        actions=r.actions,
        source=r.source,
        audio_b64=base64.b64encode(r.audio).decode("ascii"),
    )


@app.post("/profile")
async def upsert_profile(body: ProfileIn) -> dict:
    profile = profiles.save(
        Profile(
            user_id=body.user_id,
            locale=body.locale,
            favorite_team_id=body.favorite_team_id,
            city=body.city,
            latitude=body.latitude,
            longitude=body.longitude,
        )
    )
    return {"status": "ok", "context": profile.to_context()}


@app.get("/dev/stats")
async def dev_stats(n: int = 10) -> dict:
    """The most-used asks so far (in-memory analytics only)."""
    if isinstance(analytics, MemoryAnalytics):
        return {"top_intents": analytics.top_intents(n), "total": len(analytics.events)}
    return {"detail": "stats available only with the in-memory analytics sink"}


@app.websocket("/ws/voice")
async def ws_voice(ws: WebSocket) -> None:
    """Accumulate binary audio frames until a text "end" message, then run one turn.

    Reply is a JSON result message followed by a binary frame carrying the TTS audio.
    """
    await ws.accept()
    buffer = bytearray()
    try:
        while True:
            msg = await ws.receive()
            if msg.get("bytes") is not None:
                buffer.extend(msg["bytes"])
            elif msg.get("text") == "end":
                r = await pipeline.run_audio(bytes(buffer), user={})
                buffer.clear()
                await ws.send_json(
                    {
                        "type": "result",
                        "transcript": r.transcript,
                        "intent": r.intent,
                        "speech": r.speech,
                        "actions": r.actions,
                        "source": r.source,
                    }
                )
                await ws.send_bytes(r.audio)
            elif msg.get("text") == "close":
                break
    except WebSocketDisconnect:
        return

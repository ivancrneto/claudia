# Deploy Claudia to a real Android device

**What you get today:** a working **text** client — all skills (music, timer, weather,
YouTube, futebol) and the bring-your-own-AI brain, driven from your phone. The **voice**
UI (wake word, mic, speaker) is the next milestone; the app currently loads the gateway's
web client in a WebView.

Claudia is two parts: the **backend gateway** (all the brains) and a **thin client** on the
phone. So "deploy to a device" = run the backend somewhere the phone can reach, then point
the phone at it.

---

## Path A — no app build (fastest, ~2 minutes)

Great for trying it right now.

1. **Run the backend** on your computer:
   ```bash
   cd services/gateway
   pip install -r requirements.txt
   cd ../.. && python -m uvicorn services.gateway.app:app --host 0.0.0.0 --port 8000
   ```
   `--host 0.0.0.0` makes it reachable from other devices on your network.

2. **Find your computer's LAN IP** (same Wi-Fi as the phone):
   - macOS: `ipconfig getifaddr en0`  ·  Linux: `hostname -I | awk '{print $1}'`  ·  Windows: `ipconfig`

3. **On the phone's browser**, open `http://<computer-ip>:8000/` — you get the Claudia chat.
   Try "quando o Bahia joga", "toca Bruno Mars", "como está o tempo".

> Phone and computer must be on the same network, and your firewall must allow port 8000.

---

## Path B — install the app (WebView client)

Puts an installable **Claudia** app on the device. `MainActivity` loads the same web client
in a WebView; the backend URL is baked in at build time.

**Prerequisites:** Android Studio (or the Android SDK + a Gradle install), USB debugging
enabled on the phone (Settings → Developer options → USB debugging).

1. Run the backend and note your computer's IP (Path A, steps 1–2).

2. **Build a debug APK** pointed at your backend. Debug builds are auto-signed with the
   local debug key — no secrets needed.

   - **Android Studio (easiest):** open `apps/mobile/android/`, let it sync (it provisions
     the SDK + Gradle wrapper), then Run ▶ onto your connected device. Set the URL by adding
     `-PclaudiaUrl=http://<computer-ip>:8000/` under Settings → Build → Compiler command-line
     options, or edit the `claudiaUrl` default in `app/build.gradle`.

   - **Command line** (needs Gradle installed to create the wrapper the first time):
     ```bash
     cd apps/mobile/android
     gradle wrapper                 # once, generates ./gradlew
     ./gradlew :app:assembleConsumerDebug -PclaudiaUrl=http://<computer-ip>:8000/
     ```
     The APK lands in `app/build/outputs/apk/consumer/debug/`.

3. **Install onto the device** over USB:
   ```bash
   adb install -r app/build/outputs/apk/consumer/debug/app-consumer-debug.apk
   ```
   Open **Claudia** — it loads the chat from your backend.

> The app allows plain HTTP for dev (`usesCleartextTraffic`) so it can reach your LAN
> backend. Production points at `https://<your-domain>/` via Caddy (see `DEPLOYMENT.md`).

---

## Path C — lock it to a tablet (kiosk / Device Owner)

Only for a **dedicated, factory-reset tablet with no Google account** (Device Owner can't be
set otherwise). This makes Claudia un-closable (see `ARCHITECTURE.md` §7).

1. Build & install the **kiosk** flavor:
   ```bash
   ./gradlew :app:assembleKioskDebug -PclaudiaUrl=http://<computer-ip>:8000/
   adb install -r app/build/outputs/apk/kiosk/debug/app-kiosk-debug.apk
   ```
2. Make Claudia the Device Owner (no accounts on the device):
   ```bash
   adb shell dpm set-device-owner dev.gogix.claudia.kiosk/dev.gogix.claudia.kiosk.ClaudiaDeviceAdminReceiver
   ```
3. Launch it — `MainActivity` calls `startLockTask()` and the tablet is pinned to Claudia.
   To undo during testing: `adb shell dpm remove-active-admin dev.gogix.claudia.kiosk/...` then
   factory reset.

---

## Troubleshooting

- **App shows "Erro ao falar com o servidor"** → phone can't reach the backend: same Wi-Fi?
  correct IP? backend started with `--host 0.0.0.0`? firewall open on 8000?
- **Blank screen** → wrong `claudiaUrl` baked in; rebuild with the right `-PclaudiaUrl`.
- **`adb: no devices`** → enable USB debugging and accept the RSA prompt on the phone.
- **Real forecast needs coordinates** → the web client sends `user_id=device`; set a profile
  with location via `POST /profile` (or it will ask you to enable location).

## What's next (not yet built)

Native mic capture + wake word + streaming STT/TTS on-device (the `services/voice` pipeline
exists server-side; the client half is the follow-up), and the React Native UI replacing the
WebView.

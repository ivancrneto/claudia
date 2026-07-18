package dev.gogix.claudia

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import dev.gogix.claudia.kiosk.LockTaskController
import java.text.Normalizer
import java.util.Locale

/**
 * Launcher activity. Loads the Claudia web client (served by the gateway) in a WebView and
 * gives it a *voice* — an Alexa-style hands-free assistant implemented on-device:
 *
 *  - STT: Android [SpeechRecognizer] (pt-BR), streamed back to the page as events.
 *  - TTS: Android [TextToSpeech] (pt-BR) speaks the gateway's reply.
 *  - Wake word: a continuous recognition loop that fires when it hears "Claudia", so the
 *    user never has to tap — say "Claudia, que horas são" and it answers.
 *
 * A small state machine keeps the single recognizer straight:
 *   WAKE    — passively listening for the wake word (self-restarting loop)
 *   COMMAND — actively capturing one utterance after a wake / mic tap
 *   IDLE    — nothing listening
 * While TTS speaks, recognition is paused; when it finishes the WAKE loop resumes if the
 * user left wake mode on.
 *
 * The page drives everything through the `AndroidVoice` JS bridge (listen / speak / cancel /
 * startWake / stopWake) and receives results via `window.ClaudiaVoice.*` callbacks. Speech
 * recognition is not available inside a WebView on its own, so this native bridge is what
 * makes voice work in the installed app.
 *
 * The backend URL comes from BuildConfig.CLAUDIA_URL (set with -PclaudiaUrl=... at build
 * time; default is the emulator's host loopback). On the kiosk flavor it also enters Lock
 * Task Mode via the Device Owner.
 *
 * NOTE: the wake loop is built on [SpeechRecognizer], which is a pragmatic MVP — it is not a
 * true low-power hotword engine and can emit a device beep / hold the mic while active. A
 * dedicated on-device wake engine (openWakeWord / Vosk / Porcupine) in a foreground service
 * is the production follow-up (see docs/ROADMAP.md).
 */
class MainActivity : Activity() {

    private enum class Mode { IDLE, WAKE, COMMAND }

    private lateinit var web: WebView
    private val main = Handler(Looper.getMainLooper())
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var recognizer: SpeechRecognizer? = null

    private var mode = Mode.IDLE
    private var wakeEnabled = false   // user has turned always-listening on

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            // Let the page start audio (TTS) without a tap — the mic button is the gesture.
            settings.mediaPlaybackRequiresUserGesture = false
            addJavascriptInterface(VoiceBridge(), "AndroidVoice")
        }
        setContentView(web)
        web.loadUrl(BuildConfig.CLAUDIA_URL)

        initTts()
        ensureMicPermission()

        LockTaskController(this).takeIf { it.isDeviceOwner }?.lock(this)
    }

    private fun initTts() {
        tts = TextToSpeech(this) { status ->
            if (status != TextToSpeech.SUCCESS) return@TextToSpeech
            tts?.language = Locale("pt", "BR")
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) = emit("onSpeakStart")
                override fun onDone(utteranceId: String?) = onSpeakFinished()
                @Deprecated("legacy API")
                override fun onError(utteranceId: String?) = onSpeakFinished()
            })
            ttsReady = true
        }
    }

    private fun onSpeakFinished() {
        emit("onSpeakDone")
        // After speaking, hand the floor back to the wake loop if it's still on.
        if (wakeEnabled) scheduleWakeRestart()
    }

    private fun ensureMicPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC)
        }
    }

    private fun hasMic() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    /** Fire a `window.ClaudiaVoice.<event>(<arg?>)` callback into the page, on the UI thread. */
    private fun emit(event: String, arg: String? = null) {
        val js = if (arg == null) {
            "window.ClaudiaVoice&&ClaudiaVoice.$event&&ClaudiaVoice.$event()"
        } else {
            val quoted = "\"" + arg.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n") + "\""
            "window.ClaudiaVoice&&ClaudiaVoice.$event&&ClaudiaVoice.$event($quoted)"
        }
        main.post { web.evaluateJavascript(js, null) }
    }

    /** Bridge exposed to the page as `window.AndroidVoice`. Methods hop to the UI thread. */
    inner class VoiceBridge {
        /** Actively capture a single command utterance (after a wake or a mic tap). */
        @JavascriptInterface
        fun listen() {
            main.post { startCommandRecognition() }
        }

        @JavascriptInterface
        fun stopListening() {
            main.post { recognizer?.stopListening() }
        }

        /** Turn on the always-listening wake-word loop. */
        @JavascriptInterface
        fun startWake() {
            main.post {
                wakeEnabled = true
                if (mode != Mode.COMMAND) startWakeRecognition()
            }
        }

        /** Turn off the wake-word loop. */
        @JavascriptInterface
        fun stopWake() {
            main.post {
                wakeEnabled = false
                mode = Mode.IDLE
                recognizer?.cancel()
            }
        }

        @JavascriptInterface
        fun speak(text: String) {
            main.post {
                // Free the mic so TTS doesn't fight the recognizer, then speak.
                recognizer?.cancel()
                if (ttsReady && text.isNotBlank()) {
                    tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "claudia")
                } else {
                    onSpeakFinished()
                }
            }
        }

        @JavascriptInterface
        fun cancel() {
            main.post {
                wakeEnabled = false
                mode = Mode.IDLE
                tts?.stop()
                recognizer?.cancel()
            }
        }
    }

    // --- command capture (one utterance) ------------------------------------
    private fun startCommandRecognition() {
        if (!guardRecognition()) return
        mode = Mode.COMMAND
        newRecognizer(forWake = false)
        recognizer?.startListening(recognizerIntent(partial = true, offline = false))
    }

    // --- wake-word loop (self-restarting) -----------------------------------
    private fun startWakeRecognition() {
        if (!wakeEnabled) return
        if (!guardRecognition()) { wakeEnabled = false; return }
        mode = Mode.WAKE
        newRecognizer(forWake = true)
        // Use online recognition: most devices lack a downloaded pt-BR *offline* model, and
        // EXTRA_PREFER_OFFLINE then makes the recognizer fail immediately (LANGUAGE_UNAVAILABLE)
        // so the wake loop never actually listens. Online reliably supports pt-BR.
        recognizer?.startListening(recognizerIntent(partial = false, offline = false))
    }

    private fun scheduleWakeRestart() {
        if (!wakeEnabled) return
        mode = Mode.WAKE
        // A small delay avoids ERROR_RECOGNIZER_BUSY from restarting too eagerly.
        main.postDelayed({ if (wakeEnabled && mode == Mode.WAKE) startWakeRecognition() }, WAKE_RESTART_MS)
    }

    private fun guardRecognition(): Boolean {
        if (!hasMic()) {
            ensureMicPermission()
            emit("onError", "mic-permission")
            return false
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            emit("onError", "no-recognizer")
            return false
        }
        return true
    }

    private fun newRecognizer(forWake: Boolean) {
        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(makeListener(forWake))
        }
    }

    private fun recognizerIntent(partial: Boolean, offline: Boolean) =
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, partial)
            if (offline) putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
        }

    private fun makeListener(forWake: Boolean) = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) { if (!forWake) emit("onListenStart") }
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() { if (!forWake) emit("onListenEnd") }
        override fun onEvent(eventType: Int, params: Bundle?) {}

        override fun onError(error: Int) {
            if (forWake) {
                scheduleWakeRestart()   // no speech / timeout / busy — just keep listening
            } else {
                emit("onError", "recognizer-$error")
                if (wakeEnabled) scheduleWakeRestart()
            }
        }

        override fun onPartialResults(partial: Bundle?) {
            if (!forWake) firstMatch(partial)?.takeIf { it.isNotBlank() }?.let { emit("onPartial", it) }
        }

        override fun onResults(results: Bundle?) {
            val text = firstMatch(results).orEmpty()
            if (forWake) {
                val command = wakeCommand(text)
                if (command != null) {
                    // Heard the wake word. Hand the (possibly empty) trailing command to the page.
                    mode = Mode.COMMAND
                    emit("onWake", command)
                } else {
                    scheduleWakeRestart()
                }
            } else {
                emit("onResult", text)
            }
        }
    }

    /**
     * If [text] contains the wake word, return the command that follows it (may be empty);
     * otherwise null. Accent/case-insensitive so "Cláudia" / "claudia" both match.
     */
    private fun wakeCommand(text: String): String? {
        val norm = normalize(text)
        for (w in WAKE_WORDS) {
            val i = norm.indexOf(w)
            if (i >= 0) {
                // Map the match end back onto the original string to preserve the real command text.
                val after = text.drop(i + w.length)
                return after.trimStart(' ', ',', '.', '!', '?', ';', ':').trim()
            }
        }
        return null
    }

    private fun normalize(s: String): String =
        Normalizer.normalize(s, Normalizer.Form.NFD)
            .replace(DIACRITICS, "")
            .lowercase(Locale.ROOT)

    private fun firstMatch(bundle: Bundle?): String? =
        bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_MIC) {
            val granted = grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
            emit(if (granted) "onMicGranted" else "onMicDenied")
        }
    }

    override fun onDestroy() {
        recognizer?.destroy()
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }

    private companion object {
        const val REQ_MIC = 1
        const val WAKE_RESTART_MS = 350L
        val WAKE_WORDS = listOf("claudia")
        val DIACRITICS = "\\p{Mn}".toRegex()
    }
}

package dev.gogix.claudia

import android.Manifest
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
import android.app.Activity
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import dev.gogix.claudia.kiosk.LockTaskController
import java.util.Locale

/**
 * Launcher activity. Loads the Claudia web client (served by the gateway) in a WebView and
 * gives it a *voice* — an Alexa-style hands-free loop implemented on-device:
 *
 *  - STT: Android [SpeechRecognizer] (pt-BR), streamed back to the page as events.
 *  - TTS: Android [TextToSpeech] (pt-BR) speaks the gateway's reply.
 *
 * The page drives everything through the `AndroidVoice` JS bridge (listen / speak / cancel)
 * and receives results via `window.ClaudiaVoice.*` callbacks. Speech recognition is not
 * available inside a WebView on its own, so this native bridge is what makes voice work.
 *
 * The backend URL comes from BuildConfig.CLAUDIA_URL (set with -PclaudiaUrl=... at build
 * time; default is the emulator's host loopback). On the kiosk flavor it also enters Lock
 * Task Mode via the Device Owner.
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private val main = Handler(Looper.getMainLooper())
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var recognizer: SpeechRecognizer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            // Let the page start audio (TTS/beeps) without a tap — the mic button is the gesture.
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
                override fun onDone(utteranceId: String?) = emit("onSpeakDone")
                @Deprecated("legacy API")
                override fun onError(utteranceId: String?) = emit("onSpeakDone")
            })
            ttsReady = true
        }
    }

    private fun ensureMicPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC)
        }
    }

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
        @JavascriptInterface
        fun listen() {
            main.post { startRecognition() }
        }

        @JavascriptInterface
        fun stopListening() {
            main.post { recognizer?.stopListening() }
        }

        @JavascriptInterface
        fun speak(text: String) {
            main.post {
                if (ttsReady && text.isNotBlank()) {
                    tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "claudia")
                } else {
                    emit("onSpeakDone")
                }
            }
        }

        @JavascriptInterface
        fun cancel() {
            main.post {
                tts?.stop()
                recognizer?.cancel()
            }
        }
    }

    private fun startRecognition() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ensureMicPermission()
            emit("onError", "mic-permission")
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            emit("onError", "no-recognizer")
            return
        }
        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) = emit("onListenStart")
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() = emit("onListenEnd")
                override fun onError(error: Int) = emit("onError", "recognizer-$error")
                override fun onEvent(eventType: Int, params: Bundle?) {}

                override fun onPartialResults(partial: Bundle?) {
                    firstMatch(partial)?.takeIf { it.isNotBlank() }?.let { emit("onPartial", it) }
                }

                override fun onResults(results: Bundle?) {
                    emit("onResult", firstMatch(results).orEmpty())
                }
            })
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        }
        recognizer?.startListening(intent)
    }

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
    }
}

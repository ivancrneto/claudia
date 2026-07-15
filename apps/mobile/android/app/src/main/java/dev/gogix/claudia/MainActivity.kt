package dev.gogix.claudia

import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import dev.gogix.claudia.kiosk.LockTaskController

/**
 * Launcher activity. Loads the Claudia web client (served by the gateway) in a WebView so
 * the device has a working text UI today; the native React Native / voice UI replaces this
 * in a follow-up. On the kiosk flavor it also enters Lock Task Mode via the Device Owner.
 *
 * The backend URL comes from BuildConfig.CLAUDIA_URL (set with -PclaudiaUrl=... at build
 * time; default is the emulator's host loopback).
 */
class MainActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        setContentView(web)
        web.loadUrl(BuildConfig.CLAUDIA_URL)

        LockTaskController(this).takeIf { it.isDeviceOwner }?.lock(this)
    }
}

package com.claudia

import android.app.Activity
import android.os.Bundle
import com.claudia.kiosk.LockTaskController

/**
 * Launcher activity. On the kiosk flavor it enters Lock Task Mode via the Device Owner
 * controller so the tablet can't be closed.
 *
 * The React Native / voice UI is mounted here in a follow-up; this shell wires the native
 * kiosk lifecycle and gives the build config a real entry point.
 */
class MainActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        LockTaskController(this).takeIf { it.isDeviceOwner }?.lock(this)
    }
}

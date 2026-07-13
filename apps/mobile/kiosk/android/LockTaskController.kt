package com.claudia.kiosk

import android.app.Activity
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context

/**
 * Android kiosk lock via Device Owner + Lock Task Mode (COSU).
 *
 * Primary, policy-clean way to make the tablet un-closable — no AccessibilityService hack.
 * Requires the app to be provisioned as Device Owner (ADB `dpm set-device-owner`, Headwind
 * MDM, or the Android Management API) on a factory-reset device.
 *
 * Exposed to React Native as Kiosk.lock() / Kiosk.unlock().
 */
class LockTaskController(private val context: Context) {

    private val dpm =
        context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val admin = ComponentName(context, ClaudiaDeviceAdminReceiver::class.java)

    val isDeviceOwner: Boolean
        get() = dpm.isDeviceOwnerApp(context.packageName)

    /** Whitelist and enter lock task; hide status bar / keyguard / global actions. */
    fun lock(activity: Activity) {
        if (isDeviceOwner) {
            dpm.setLockTaskPackages(admin, arrayOf(context.packageName))
            dpm.setLockTaskFeatures(admin, 0) // no system UI while pinned
            // TODO: make Claudia the Home launcher (addPersistentPreferredActivity),
            //       block uninstall/factory-reset/Safe Mode, start on BOOT_COMPLETED.
        }
        activity.startLockTask()
    }

    /** Release the lock (admin PIN gate lives in the RN layer). */
    fun unlock(activity: Activity) {
        activity.stopLockTask()
    }
}

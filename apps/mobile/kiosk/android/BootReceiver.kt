package com.claudia.kiosk

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Auto-launch Claudia on boot so a kiosk tablet comes up straight into the app.
 * Registered for android.intent.action.BOOT_COMPLETED.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val launch = context.packageManager
                .getLaunchIntentForPackage(context.packageName)
                ?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            launch?.let { context.startActivity(it) }
        }
    }
}

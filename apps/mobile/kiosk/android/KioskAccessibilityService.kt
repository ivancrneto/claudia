package dev.gogix.claudia.kiosk

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.view.accessibility.AccessibilityEvent

/**
 * FALLBACK ONLY — use when Device Owner can't be provisioned.
 *
 * Watches foreground-app changes and re-launches Claudia if the user leaves. This is NOT
 * the primary lock: it can be disabled in Settings, and Google Play restricts
 * AccessibilityService to genuine accessibility use — ship this build via sideload/MDM,
 * not the Play Store. Prefer LockTaskController (Device Owner).
 */
class KioskAccessibilityService : AccessibilityService() {

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val pkg = event.packageName?.toString() ?: return
            if (pkg != packageName && !isSystemWhitelisted(pkg)) {
                packageManager.getLaunchIntentForPackage(packageName)
                    ?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    ?.let { startActivity(it) }
            }
        }
    }

    override fun onInterrupt() {}

    private fun isSystemWhitelisted(pkg: String): Boolean = pkg.startsWith("com.android.systemui")
}

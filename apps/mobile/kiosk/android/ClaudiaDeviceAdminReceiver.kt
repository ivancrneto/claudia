package dev.gogix.claudia.kiosk

import android.app.admin.DeviceAdminReceiver

/**
 * Device Owner admin receiver. Registered in AndroidManifest with a device_admin policy XML
 * and bound via `adb shell dpm set-device-owner \
 * dev.gogix.claudia.kiosk/dev.gogix.claudia.kiosk.ClaudiaDeviceAdminReceiver`
 * on a factory-reset (account-less) device.
 */
class ClaudiaDeviceAdminReceiver : DeviceAdminReceiver()

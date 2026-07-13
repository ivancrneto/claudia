import UIKit

/// iOS kiosk lock. No AccessibilityService equivalent exists — MDM + Supervision is
/// mandatory for a real lock.
///
/// - Single App Mode (MDM payload) hard-locks the device to Claudia.
/// - Autonomous Single App Mode (ASAM), used here, lets the app lock/unlock *itself*
///   (admin PIN to release) once the bundle id is whitelisted for ASAM in the MDM profile.
/// - Guided Access is the manual, no-MDM fallback (demo only).
///
/// Exposed to React Native as Kiosk.lock() / Kiosk.unlock(pin).
@objc(KioskManager)
final class KioskManager: NSObject {

    /// Enter Autonomous Single App Mode.
    @objc func lock(_ resolve: @escaping RCTPromiseResolveBlock,
                    rejecter reject: @escaping RCTPromiseRejectBlock) {
        UIAccessibility.requestGuidedAccessSession(enabled: true) { success in
            success ? resolve(true) : reject("asam_failed", "Not whitelisted for ASAM", nil)
        }
    }

    /// Exit ASAM (the admin-PIN gate lives in the RN layer before calling this).
    @objc func unlock(_ resolve: @escaping RCTPromiseResolveBlock,
                      rejecter reject: @escaping RCTPromiseRejectBlock) {
        UIAccessibility.requestGuidedAccessSession(enabled: false) { success in
            resolve(success)
        }
    }
}

// RCT* typealiases so this file reads without the React headers present in the scaffold.
typealias RCTPromiseResolveBlock = (Any?) -> Void
typealias RCTPromiseRejectBlock = (String?, String?, Error?) -> Void

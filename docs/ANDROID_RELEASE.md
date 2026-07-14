# Android build & release

Same public-repo posture as the backend: **build config is public, signing and Play
credentials live only in CI secrets / a secret manager — never in git.**

## Two distributions, one codebase

Product flavors in [`apps/mobile/android/app/build.gradle`](../apps/mobile/android/app/build.gradle):

| Flavor | Output | Channel | Why |
|---|---|---|---|
| `kiosk` | signed **APK** | MDM / sideload (Headwind, Apple-Configurator-equiv, ADB) | Device Owner + Lock Task, and the `AccessibilityService` fallback is Play-policy-risky |
| `consumer` | signed **AAB** | Google Play (internal → production) via fastlane | Standard store distribution |

## Signing — Play App Signing + upload key

Google holds the real **app signing key**; CI signs with an **upload key**. Losing the
upload key is recoverable (reset in Play Console), so this is the low-risk choice.

The upload keystore is **base64 in a GitHub secret**, decoded at build time to a path
outside the repo. `app/build.gradle` reads every signing value from the environment — there
are no passwords in the repo.

Generate an upload key once (keep the `.keystore` out of git — it's git-ignored):

```bash
keytool -genkeypair -v -keystore upload.keystore -alias claudia-upload \
  -keyalg RSA -keysize 2048 -validity 10000
base64 -w0 upload.keystore   # paste into the UPLOAD_KEYSTORE_BASE64 secret
```

## Release runs on GitHub Actions

The signed Android release runs on **GitHub Actions**
([`.github/workflows/android-release.yml`](../.github/workflows/android-release.yml)),
alongside the PR CI (tests + secret-scan).

## Required GitHub Actions secrets (names only)

| Secret | Purpose |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | base64 of the upload keystore |
| `ANDROID_KEYSTORE_PASSWORD` | keystore store password |
| `ANDROID_KEY_ALIAS` | upload key alias |
| `ANDROID_KEY_PASSWORD` | upload key password |
| `PLAY_SERVICE_ACCOUNT_JSON_B64` | *(optional)* base64 Play service-account JSON — enables the Play upload |

None of these are in the repo; the `secret-scan` CI gate keeps it that way. `CLAUDIA_URL`
(the WebView backend baked into the app) is a non-secret **repo variable** (`vars.CLAUDIA_URL`).

## Versioning

`versionName` / `versionCode` are derived from the release **tag** by
[`tools/android_version.py`](../tools/android_version.py) — never hand-edited.
`vMAJOR.MINOR.PATCH` → code `MAJOR*10000 + MINOR*100 + PATCH` (monotonic across bumps),
passed to Gradle as `-PversionName` / `-PversionCode`.

## Releasing

1. Tag the release: `git tag v1.4.2 && git push --tags` (or run the workflow manually with a
   `tag` input).
2. The workflow then:
   - derives the version from the tag,
   - provisions the Android SDK + Gradle 8.9,
   - decodes the upload keystore from the secret,
   - builds `assembleKioskRelease` (APK) + `bundleConsumerRelease` (AAB), signed via the
     `CLAUDIA_UPLOAD_*` env the Gradle `signingConfig` reads,
   - uploads both as a workflow artifact, attaches the **kiosk APK** to the GitHub Release,
   - uploads the **consumer AAB** to the Play **internal** track via fastlane (when
     `PLAY_SERVICE_ACCOUNT_JSON_B64` is set).
3. Promote to production when ready: run the `promote` fastlane lane (staged rollout).

## Kiosk distribution

The kiosk APK is **not** shipped through Play (AccessibilityService policy). Push it to
tablets via your MDM (Headwind / Android Management API) or ADB sideload onto a
Device-Owner-provisioned device — see [`ARCHITECTURE.md`](ARCHITECTURE.md) §7.

## Note

A full Gradle build needs the Android SDK and isn't run in the backend `test` CI or this
environment — only `tools/android_version.py` is unit-tested. The real APK/AAB build runs on
the GitHub-hosted runner in the release workflow.

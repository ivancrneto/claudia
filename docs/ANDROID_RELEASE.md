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

## Release runs on Buildkite

The signed Android release runs on **Buildkite** (modeled on izap's `.buildkite/`), because
its agents do the containerized SDK build. See [`.buildkite/README.md`](../.buildkite/README.md).
PR CI (tests + secret-scan) stays on GitHub Actions.

## Required Buildkite CLUSTER secrets (names only — same as izap)

| Secret | Purpose |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | base64 of the upload keystore |
| `ANDROID_KEYSTORE_PASSWORD` | keystore store password |
| `ANDROID_KEY_ALIAS` | upload key alias |
| `ANDROID_KEY_PASSWORD` | upload key password |
| `PLAY_SERVICE_ACCOUNT_JSON_B64` | *(optional)* base64 Play service-account JSON — enables the Play upload |

Store them as **cluster** secrets in the same cluster as the agents on the pipeline's queue
(`buildkite-agent secret get` can't see pipeline/env vars or other clusters). Nothing
sensitive is in the repo. `CLAUDIA_URL` (the WebView backend) is a non-secret build env.

> izap uploads to Play **keylessly** via Workload Identity Federation (no SA key). This
> pipeline uses the simpler service-account-JSON path Claudia's fastlane already supports; to
> adopt keyless WIF, port the OIDC block from izap's `steps/builds/build_dash_apk`.

## Versioning

`versionName` comes from the release **tag** (`vMAJOR.MINOR.PATCH`); `versionCode` is the
monotonic `BUILDKITE_BUILD_NUMBER` (izap idiom). Both are passed to Gradle as
`-PversionName` / `-PversionCode`. (`tools/android_version.py` still derives a code from a
tag for local/other use and is unit-tested.)

## Releasing

1. Tag the release: `git tag v1.4.2 && git push --tags` (or start a build with `BUILD_ANDROID=true`).
2. [`.buildkite/pipeline.yml`](../.buildkite/pipeline.yml) uploads the release pipeline, which:
   - shows a **block** step to approve the release,
   - runs [`steps/builds/build_android`](../.buildkite/steps/builds/build_android) inside an
     `eclipse-temurin:21` container (installs the Android SDK + Gradle, `docker cp`'s the
     checkout in),
   - builds `assembleKioskRelease` (APK) + `bundleConsumerRelease` (AAB), signed with the
     upload key from the cluster secrets,
   - attaches both to the Buildkite build via `artifact_paths`,
   - uploads the **consumer AAB** to the Play **internal** track via fastlane (when
     `PLAY_SERVICE_ACCOUNT_JSON_B64` is set).
3. Promote to production when ready: run the `promote` fastlane lane (staged rollout).

## Kiosk distribution

The kiosk APK is **not** shipped through Play (AccessibilityService policy). Push it to
tablets via your MDM (Headwind / Android Management API) or ADB sideload onto a
Device-Owner-provisioned device — see [`ARCHITECTURE.md`](ARCHITECTURE.md) §7.

## Note

A full Gradle build needs the Android SDK and isn't run in the backend CI or this
environment. The `.buildkite/` YAML and shell are syntax-checked here; the real APK/AAB build
runs on a Buildkite agent with Docker.

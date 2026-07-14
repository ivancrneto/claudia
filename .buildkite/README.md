# Buildkite

Claudia's **signed Android release** runs on Buildkite (modeled on izap's `.buildkite/`).
PR CI — tests + secret-scan — stays on GitHub Actions (`.github/workflows/ci.yml`).

```
.buildkite/
├── pipeline.yml                     # entrypoint: uploads the release pipeline on v* tag / BUILD_ANDROID=true
├── pipelines/android-release.yml    # block gate → build & sign → optional Play upload
└── steps/builds/build_android       # the containerized build (JDK+SDK in eclipse-temurin)
```

**Why a container:** agents have Docker but no JDK/Android SDK, so the build runs inside
`eclipse-temurin:21` — the checkout is `docker cp`'d in and artifacts copied back (agents are
containerized, so bind mounts don't work). Same approach as izap's `build_dash_apk`.

**Secrets** (Buildkite CLUSTER secret store, same names as izap):
`ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`,
`ANDROID_KEY_PASSWORD`, and optional `PLAY_SERVICE_ACCOUNT_JSON_B64` (enables the Play
upload). Nothing sensitive is in the repo. Full setup: [`docs/ANDROID_RELEASE.md`](../docs/ANDROID_RELEASE.md).

**Trigger:** push a `v*` tag, or start a build with `BUILD_ANDROID=true`. A `block` step gates
the release (auto-skips only when `NATIVE_RELEASE_PREAPPROVED=true` — pin that to a trusted
creator for a real gate, as izap does).

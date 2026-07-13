# Deployment

Claudia's repo is **public**, so the deployment model is: **public code, external secrets,
config strictly via environment.** Nothing sensitive ever lives in git.

## What is public vs. private

| Public (in this repo) | Private (never committed) |
|---|---|
| All application code | Provider API keys (Anthropic/OpenAI/Gemini) |
| `.env.example` (keys only, no values) | `VAULT_KEY` (Account-Vault Fernet key) |
| Compose files & `Caddyfile` | `API_FOOTBALL_KEY` |
| Dockerfiles, docs | TLS material, user data, model weights |

## Configuration (12-factor)

Every setting is read from the environment via [`services/config.py`](../services/config.py).
There are **no secrets in code or in the repo**. In `CLAUDIA_ENV=prod` the gateway calls
`Settings.validate()` at startup and **fails fast** if a required secret
(`VAULT_KEY`) is missing. `Settings.__repr__` redacts secret values, so logs never leak them.

See [`.env.example`](../.env.example) for the full list of variables.

## Secrets strategy — external secret manager

Secrets are injected **at runtime**, from outside the repo. Pick whichever your host offers;
the app only cares that the variables are present in its environment:

- **Env file outside the repo (default for a VPS):** keep secrets in
  `/etc/claudia/claudia.env` (`chmod 600`, owned by the deploy user). The prod compose file
  references it via `CLAUDIA_ENV_FILE` — it is never copied into the image or the repo.
- **Docker secrets / Swarm:** mount secrets and export them into the container env.
- **Cloud secret manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault):**
  fetch at boot and export to the process environment before starting the gateway.

Generate the vault key once and store it in the manager (rotating it re-encrypts stored
credentials):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Deploy (self-hosted VPS + Docker Compose)

```bash
# On the VPS, secrets live outside the repo:
sudoedit /etc/claudia/claudia.env         # fill VAULT_KEY, API_FOOTBALL_KEY, etc. (chmod 600)
export CLAUDIA_ENV_FILE=/etc/claudia/claudia.env
export CLAUDIA_DOMAIN=claudia.example.com  # Caddy provisions TLS for this host

docker compose -f infra/docker-compose.prod.yml up -d --build
```

`Caddy` terminates TLS (automatic Let's Encrypt certs) and reverse-proxies to the gateway,
which is only exposed on the internal network.

## CI/CD posture

- **CI needs no secrets.** Tests run entirely on offline stubs (STT/TTS/providers/football),
  so the public-PR test job never requires credentials.
- **Secret-scan gate.** A `secret-scan` job runs gitleaks on every push/PR — if a real
  secret is ever staged, CI goes red before it can be published.
- **Deploy separately from CI.** Run the compose deploy from the VPS (pull + `up -d`) or a
  self-hosted runner. If you later add a GitHub Actions deploy, use **OIDC / GitHub
  Environments** for short-lived credentials — never long-lived secrets in the workflow.

## Model artifacts

faster-whisper / Piper / openWakeWord weights are **not** committed. Pull them at deploy
time (release asset, object store, or the model's own downloader) into a mounted volume.

## Rules of thumb

1. If it's a secret, it comes from the environment — never from git.
2. `.env` (real) is git-ignored; only `.env.example` (keys only) is committed.
3. Never log a secret value; `Settings` redacts them by design.
4. Rotate `VAULT_KEY` and provider keys through the secret manager, not the repo.

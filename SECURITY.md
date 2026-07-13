# Security

This repository is **public**. Treat everything in it as world-readable.

## Secrets never go in the repo

- No API keys, tokens, `VAULT_KEY`, TLS material, or user data in git — ever.
- All secrets are injected at runtime from an external secret manager. See
  [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
- Only `.env.example` (variable **names**, no values) is committed; real `.env` files are
  git-ignored.
- A `secret-scan` CI job (gitleaks) runs on every push and PR and fails if a secret is
  detected in the diff.

## If a secret is exposed

1. **Rotate it immediately** in the provider / secret manager (the git history keeps the
   old value forever — rotation is the only real fix).
2. Rotate `VAULT_KEY` if it leaked (this re-encrypts stored credentials).
3. Purge from history only after rotating, if warranted.

## Reporting

Report suspected vulnerabilities privately to the maintainer rather than opening a public
issue.

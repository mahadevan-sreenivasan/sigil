# Admin token via environment variable over API-key-based admin auth

Admin endpoints (`/admin/*` — create, list, revoke API keys) are authenticated with a pre-shared token set via the `SIGIL_ADMIN_TOKEN` environment variable, checked as `Authorization: Bearer <token>`. This is a separate privilege tier from publishable and secret API keys.

We chose an env-var token over two alternatives because it cleanly separates operator credentials (whoever deploys the server) from integrator credentials (the application that uses Sigil). If a secret key leaks, the attacker can read data but cannot mint new keys or revoke existing ones. The env-var approach also avoids a bootstrap problem: you need admin auth *before* any API keys exist, so the credential cannot itself be an API key.

`SIGIL_ADMIN_TOKEN` is required — the server refuses to start without it. This eliminates the risk of a forgotten env var silently leaving the admin surface unauthenticated in production. The cost to local development and tests is negligible (one extra env var alongside `DATABASE_URL`).

## Considered Options

- **Secret keys grant admin access**: Simpler (no new credential), but conflates two privilege tiers. A leaked secret key would allow an attacker to revoke all keys or mint their own, escalating a data-read compromise to full control. Rejected.
- **Separate admin key type stored in the database**: Avoids the env-var, but creates a bootstrap problem — you need an admin key to create the first admin key. Also adds schema complexity (a third `key_type`) for a credential that only one or two operators will ever use. Rejected.

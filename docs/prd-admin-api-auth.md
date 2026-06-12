# PRD: Admin API Authentication & Key Management

## Problem Statement

The integration guide documents an admin API (`POST /admin/api-keys`) that requires an admin token (`Authorization: Bearer <admin-token>`), but the implementation exempts this endpoint from all authentication. Anyone who can reach the server can generate unlimited publishable and secret API key pairs. There is also no way to list or revoke existing keys, despite the database schema supporting revocation (`revoked_at` column). This is a security gap — a network-reachable attacker can mint their own secret keys, gaining full read access to visitor, account, and geolocation data.

## Solution

Introduce an Admin Token (`SIGIL_ADMIN_TOKEN` environment variable) that protects a `/admin/*` endpoint namespace. Add list and revoke endpoints alongside the existing create endpoint. Store unique key prefixes at creation time so operators can identify and target individual keys for revocation. Update the integration guide to document the complete admin API.

## User Stories

1. As a server operator, I want the server to refuse to start without `SIGIL_ADMIN_TOKEN` set, so that I cannot accidentally deploy with an unauthenticated admin surface.
2. As a server operator, I want the server to reject admin tokens shorter than 32 characters at startup, so that I cannot deploy with a trivially guessable token.
3. As a server operator, I want to create a publishable + secret key pair by calling `POST /admin/api-keys` with my admin token, so that I can onboard new integrators.
4. As a server operator, I want to list all existing API keys (showing prefix, type, creation date, revocation status, and allowed origins) by calling `GET /admin/api-keys`, so that I have operational visibility into which keys exist.
5. As a server operator, I want to revoke a specific API key by its unique prefix by calling `DELETE /admin/api-keys/{keyPrefix}`, so that I can respond to a key leak without affecting other keys.
6. As a server operator, I want to revoke a secret key independently of its publishable key (and vice versa), so that I can rotate a compromised secret key while keeping the frontend running.
7. As a server operator, I want requests to `/admin/*` without a valid admin token to receive a 401, so that unauthorized callers cannot manage API keys.
8. As a server operator, I want requests to `/admin/*` with a secret or publishable API key (not the admin token) to receive a 401, so that a leaked integrator credential cannot escalate to admin access.
9. As an integrator reading the integration guide, I want the admin API section to document all three endpoints (create, list, revoke) with request/response examples, so that I can manage keys without reading source code.
10. As an integrator reading the integration guide, I want the admin API section to clearly state that admin endpoints require the admin token (not an API key), so that I don't confuse the two credential types.
11. As a server operator, I want the `SIGIL_ADMIN_TOKEN` to be compared using constant-time comparison, so that timing attacks cannot be used to guess the token.
12. As a server operator, I want created keys to have a unique prefix (e.g. `pk_live_a7Bx3k`) stored at creation time, so that I can identify keys in the list output and target them for revocation without ever seeing the full key again.
13. As a server operator, I want the configuration reference in the integration guide to include `SIGIL_ADMIN_TOKEN`, so that I know it exists and that it's required.

## Implementation Decisions

- **Three-tier privilege model**: publishable (identify only) < secret (all data endpoints) < admin token (key management). These tiers are enforced in the `AuthMiddleware`.
- **Admin token is an environment variable, not a database record.** This avoids a bootstrap problem (you need admin auth before any API keys exist) and cleanly separates operator credentials from integrator credentials. See ADR-0002.
- **`SIGIL_ADMIN_TOKEN` is required at startup.** `validate_env()` in the startup module checks for its presence and enforces a minimum length of 32 characters. The server raises `RuntimeError` if the check fails, same pattern as the existing `DATABASE_URL` check.
- **Admin token comparison uses `hmac.compare_digest`** (constant-time) to prevent timing side-channels.
- **`/admin/*` paths are no longer in `_AUTH_EXEMPT_PATHS`.** The `AuthMiddleware` checks whether the path starts with `/admin/` and, if so, validates the bearer token against `SIGIL_ADMIN_TOKEN` before proceeding. If the path is `/admin/*` and the token doesn't match, return 401 — never fall through to the API key lookup.
- **Unique key prefix**: `_generate_raw_key` produces keys like `pk_live_<random>`. The `key_prefix` column stores the first 14 characters (e.g. `pk_live_a7Bx3k`), which is enough to be unique and recognizable. No schema migration needed — the `key_prefix` column already exists and just needs a longer value stored.
- **Revoke endpoint** sets `revoked_at = NOW()` on the row matching the given `key_prefix`. The existing `AuthMiddleware` already checks `revoked_at IS NOT NULL` and rejects revoked keys.
- **List endpoint** returns an array of `{ keyPrefix, keyType, allowedOrigins, createdAt, revokedAt }`. Never exposes the full key or the hash.
- **Keys are independently revocable.** There is no pairing mechanism linking a publishable key to its secret key. Revoking one does not affect the other.
- **Integration guide updates**: The existing "Generate API Keys" section in Quick Start is corrected to show the admin token. A new "Admin API" section is added under "Identification Server API" documenting all three endpoints. The configuration reference table gains a `SIGIL_ADMIN_TOKEN` row. The API Quick Reference table gains the three admin endpoints.

## Testing Decisions

- Tests should exercise external HTTP behavior through the existing `AsyncClient` fixture — assert on status codes and response bodies, not on internal middleware state. This matches the pattern established in `test_api_keys.py`.
- Startup validation tests should call `validate_env()` directly and assert on `RuntimeError`, matching the pattern in `test_startup.py`.
- **Admin auth (AuthMiddleware seam, in `test_api_keys.py`)**:
  - `POST /admin/api-keys` without auth header → 401
  - `POST /admin/api-keys` with wrong admin token → 401
  - `POST /admin/api-keys` with a secret API key instead of admin token → 401
  - `POST /admin/api-keys` with correct admin token → 200
  - Same pattern for `GET /admin/api-keys` and `DELETE /admin/api-keys/{prefix}`
- **Create key pair (AuthMiddleware seam, in `test_api_keys.py`)**:
  - Response contains `publishableKey` and `secretKey` with correct prefixes
  - `key_prefix` stored in DB is the unique prefix (not just `pk_live_`)
- **List keys (AuthMiddleware seam, in `test_api_keys.py`)**:
  - Returns all keys with prefix, type, origins, timestamps
  - Never exposes full key or hash
- **Revoke key (AuthMiddleware seam, in `test_api_keys.py`)**:
  - Revoked key returns `revokedAt` in response
  - Subsequent requests using the revoked key get 401
  - Revoking a publishable key does not affect the secret key created alongside it
  - Revoking a non-existent prefix returns 404
- **Startup validation (`validate_env()` seam, in `test_startup.py`)**:
  - Missing `SIGIL_ADMIN_TOKEN` → `RuntimeError`
  - `SIGIL_ADMIN_TOKEN` shorter than 32 chars → `RuntimeError`
  - `SIGIL_ADMIN_TOKEN` of 32+ chars → passes
- The existing `conftest.py` `client` fixture and `api_keys` fixture will need to set `SIGIL_ADMIN_TOKEN` in the environment and pass the admin token when calling `/admin/api-keys`.

## Out of Scope

- **Key rotation endpoint** (create new pair + revoke old in one call) — can be done with two separate calls.
- **Admin token rotation** — requires a server restart with a new env var; no hot-reload mechanism.
- **Audit logging** of admin actions — valuable but a separate concern.
- **Rate limiting on admin endpoints** — low priority given the token is a high-entropy secret.
- **Multiple admin tokens / role-based admin access** — unnecessary for a single-operator self-hosted server.
- **Schema migration for `key_prefix`** — the column already exists and accepts longer values; this is a code-only change.

## Further Notes

- The `_AUTH_EXEMPT_PATHS` set will shrink from `{"/admin/api-keys", "/docs", "/openapi.json", "/health"}` to `{"/docs", "/openapi.json", "/health"}`.
- The admin token check should happen early in `AuthMiddleware.dispatch`, before the database lookup for API keys, to avoid unnecessary DB queries on admin requests.
- ADR-0002 (`docs/adr/0002-admin-token-env-var-over-api-key-auth.md`) records the rationale for choosing an env-var token over secret-key-based admin access or a separate admin key type.
- The `CONTEXT.md` glossary has been updated with the "Admin Token" term.

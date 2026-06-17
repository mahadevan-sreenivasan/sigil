# Sigil — Integration Guide

Sigil is a browser fingerprint SDK for fraud detection. It ships three components:

- **Collector** — A TypeScript library (npm package) that runs in the browser and gathers device/session signals.
- **Identification Server** — A Python/FastAPI service (Docker image) that stores signal history, computes similarity scores, detects impossible travel, and tracks velocity.
- **Dashboard** — A React SPA for investigating visitors, accounts, and devices.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Integrator's Frontend                                   │
│                                                          │
│   ┌─────────────────────┐                                │
│   │  Collector           │                               │
│   │  @sigil/collector    │── HTTP (publishable key) ─┐   │
│   └─────────────────────┘                            │   │
└──────────────────────────────────────────────────────┼───┘
                                                       │
                                                       ▼
                                             ┌──────────────────┐
                                             │  Identification  │
                                             │  Server          │
                                             │  sigil-server    │
                                             └──────────────────┘
                                                       ▲
                                                       │
┌──────────────────────────────────────────────────────┼───┐
│  Integrator's Backend ── HTTP (secret key) ──────────┘   │
└──────────────────────────────────────────────────────────┘
                                                       ▲
                                                       │
┌──────────────────────────────────────────────────────┼───┐
│  Dashboard (React SPA) ── HTTP (secret key) ─────────┘   │
└──────────────────────────────────────────────────────────┘
```

The Collector and the integrator's backend both communicate with the Identification Server over HTTP. The Collector uses a **publishable key** (safe to embed in frontend code). The integrator's backend and the Dashboard use a **secret key** (never exposed to browsers).

---

## Quick Start

### 1. Start the Identification Server

```bash
docker run -d \
  --name sigil-server \
  -p 8080:8080 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/sigil \
  -e IP_API_PRO_KEY=your-ip-api-pro-key \
  sigil-server:latest
```

The server requires:
- A PostgreSQL database (14+)
- An ip-api Pro key for geolocation enrichment (https://ip-api.com)

### 2. Generate API Keys

```bash
# Generate a publishable + secret key pair
curl -X POST http://localhost:8080/admin/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"allowedOrigins": ["https://www.mystore.com"]}'
```

Response:
```json
{
  "publishableKey": "pk_live_abc123...",
  "secretKey": "sk_live_xyz789..."
}
```

### 3. Install the Collector

```bash
npm install @sigil/collector
```

### 4. Use the Collector

```javascript
import { SigilCollector } from '@sigil/collector';

const collector = new SigilCollector({
  apiKey: 'pk_live_abc123...',
  serverUrl: 'https://fp.mystore.com',
  timeout: 5000  // optional, defaults to 5000ms
});

// On login / checkout — collect signals and identify
const result = await collector.identify({
  accountId: 'cust_12345'  // optional, include after login
});
```

---

## Collector API

### `new SigilCollector(options)`

Creates a new Collector instance. Does **not** collect any signals until `identify()` is called.

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `apiKey` | `string` | Yes | — | Publishable key (`pk_live_...`) |
| `serverUrl` | `string` | Yes | — | URL of the Identification Server |
| `timeout` | `number` | No | `5000` | Timeout in milliseconds for the server call |

### `collector.identify(options?)`

Collects device and session signals, sends them to the Identification Server, and returns the identification result.

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `accountId` | `string` | No | The end user's account identifier in your system. Include this after the user has logged in. |

Returns a `Promise<IdentificationResult>`.

**Signals collected:**

| Signal | Type | Category | Entropy | Stability |
|--------|------|----------|---------|-----------|
| Canvas hash | Device | High | High | High |
| WebGL renderer & vendor | Device | High | High | High |
| Audio context hash | Device | Medium | High | High |
| Installed fonts (via CSS/canvas measurement) | Device | High | High | Medium |
| Screen resolution & color depth | Device | Medium | High | High |
| Platform / OS | Session | Medium | High | High |
| Hardware concurrency (CPU cores) | Device | Low-Med | High | High |
| Device memory | Device | Low-Med | High | High |
| Touch support / max touch points | Device | Low-Med | High | High |
| Timezone | Session | Medium | Medium | Medium |
| User-agent string | Session | Medium | Low | Low |

**Degraded mode:** If the Identification Server is unreachable, `identify()` returns a result with `serverReachable: false` and locally computed signals. The `visitorId`, `similarVisitors`, `velocity`, and geolocation fields will be `null`.

---

## Identification Server API

### Authentication

All requests must include an API key:

```
Authorization: Bearer <key>
```

- **Publishable key** (`pk_live_...`) — Only valid for `POST /identify`. Validated against registered allowed origins via CORS.
- **Secret key** (`sk_live_...`) — Valid for all endpoints.

### Rate Limiting

The server enforces a default rate limit of **20 requests/second** per publishable key on the `POST /identify` endpoint. This is configurable via environment variable `SIGIL_RATE_LIMIT_RPS`.

---

### `POST /identify`

Submit signals for identification. This is the primary endpoint called by the Collector.

> **You don't call this endpoint directly.** The Collector constructs and sends this request automatically when you call `collector.identify()`. The raw request format is documented here for transparency and for advanced use cases (e.g. server-side replay, debugging, or calling the API without the Collector).

**Request:**

```json
{
  "signals": {
    "canvas": "a3f8e2...",
    "webglRenderer": "ANGLE (NVIDIA GeForce GTX 1080)",
    "webglVendor": "Google Inc. (NVIDIA)",
    "audioHash": "b7c2d1...",
    "fonts": "d4e5f6...",
    "screenResolution": "1920x1080",
    "colorDepth": 24,
    "platform": "Win32",
    "hardwareConcurrency": 8,
    "deviceMemory": 16,
    "touchSupport": false,
    "maxTouchPoints": 0,
    "timezone": "Asia/Kolkata",
    "userAgent": "Mozilla/5.0 ..."
  },
  "visitorId": "vis_a1b2c3d4",
  "accountId": "cust_12345"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `signals` | `object` | Yes | Device and session signals collected by the Collector |
| `visitorId` | `string` | No | Previously assigned Visitor ID (from localStorage/cookie). Omit on first visit. |
| `accountId` | `string` | No | The integrator's identifier for the end user. Include after login. |

**Response (publishable key):**

```json
{
  "visitorId": "vis_a1b2c3d4",
  "fingerprintId": "fp_e5f6g7h8",
  "isNewVisitor": false,
  "signalValidation": "match",
  "serverReachable": true,

  "geolocation": {
    "ip": "203.0.113.45",
    "country": "IN",
    "city": "Mumbai",
    "latitude": 19.076,
    "longitude": 72.8777
  },

  "impossibleTravel": {
    "detected": false,
    "previousLocation": null,
    "previousSeenAt": null,
    "distanceKm": null
  },

  "similarVisitors": [
    {
      "visitorId": "vis_x9y8z7",
      "similarityScore": 0.87,
      "lastSeenAt": "2026-06-01T14:30:00Z",
      "matchingSignals": ["canvas", "webgl", "audio"],
      "mismatchedSignals": ["timezone", "screen"]
    }
  ],

  "velocity": {
    "visitorRequestsLast10Min": 3,
    "accountDistinctVisitorsLast1Hr": 1,
    "ipDistinctAccountsLast1Hr": 1
  }
}
```

**Response (secret key) — additional fields:**

```json
{
  "...same as above...",

  "similarVisitors": [
    {
      "visitorId": "vis_x9y8z7",
      "similarityScore": 0.87,
      "lastSeenAt": "2026-06-01T14:30:00Z",
      "matchingSignals": ["canvas", "webgl", "audio"],
      "mismatchedSignals": ["timezone", "screen"],
      "accountIds": ["cust_456", "cust_789"]
    }
  ],

  "accountHistory": {
    "knownVisitorCount": 3,
    "isKnownVisitorForAccount": false
  }
}
```

**`signalValidation` values:**

| Value | Meaning |
|-------|---------|
| `new` | No Visitor ID was provided (first visit or cookies cleared) |
| `match` | Visitor ID was provided and incoming signals match stored history |
| `mismatch` | Visitor ID was provided but incoming signals do NOT match stored history (possible spoofing) |

**`impossibleTravel` — only computed when `accountId` is provided:**

| Field | Description |
|-------|-------------|
| `detected` | `true` if the distance between current and previous geolocation is physically unreachable in the elapsed time (assuming max 900 km/h) |
| `previousLocation` | The previous geolocation `{ country, city, latitude, longitude }` |
| `previousSeenAt` | Timestamp of the previous identification for this account |
| `distanceKm` | Distance in kilometers between current and previous location |

---

### `GET /visitors/{visitorId}`

Retrieve a visitor's full signal history and account bindings.

**Auth:** Secret key only.

**Response:**

```json
{
  "visitorId": "vis_a1b2c3d4",
  "firstSeenAt": "2026-01-15T10:00:00Z",
  "lastSeenAt": "2026-06-10T14:30:00Z",
  "accountBindings": [
    {
      "accountId": "cust_12345",
      "status": "verified",
      "firstSeenAt": "2026-01-15T10:00:00Z",
      "lastSeenAt": "2026-06-10T14:30:00Z"
    }
  ],
  "recentSignalSets": [
    {
      "capturedAt": "2026-06-10T14:30:00Z",
      "signals": { "canvas": "a3f8...", "..." : "..." },
      "geolocation": { "ip": "203.0.113.45", "country": "IN", "city": "Mumbai" }
    }
  ]
}
```

---

### `GET /accounts/{accountId}/visitors`

List all visitors (devices) associated with an account.

**Auth:** Secret key only.

**Response:**

```json
{
  "accountId": "cust_12345",
  "visitors": [
    {
      "visitorId": "vis_a1b2c3d4",
      "bindingStatus": "verified",
      "firstSeenAt": "2026-01-15T10:00:00Z",
      "lastSeenAt": "2026-06-10T14:30:00Z",
      "lastGeolocation": { "country": "IN", "city": "Mumbai" }
    },
    {
      "visitorId": "vis_m3n4o5",
      "bindingStatus": "observed",
      "firstSeenAt": "2026-06-09T22:00:00Z",
      "lastSeenAt": "2026-06-09T22:00:00Z",
      "lastGeolocation": { "country": "NG", "city": "Lagos" }
    }
  ]
}
```

---

### `GET /accounts/{accountId}/geolocations`

Get geolocation history for an account.

**Auth:** Secret key only.

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | `integer` | `30` | Number of days of history to return |

**Response:**

```json
{
  "accountId": "cust_12345",
  "geolocations": [
    {
      "visitorId": "vis_a1b2c3d4",
      "ip": "203.0.113.45",
      "country": "IN",
      "city": "Mumbai",
      "latitude": 19.076,
      "longitude": 72.8777,
      "capturedAt": "2026-06-10T14:30:00Z"
    }
  ]
}
```

---

### `GET /ip/{ipAddress}/visitors`

List all visitors that have used a given IP address.

**Auth:** Secret key only.

**Response:**

```json
{
  "ip": "203.0.113.45",
  "visitors": [
    {
      "visitorId": "vis_a1b2c3d4",
      "accountIds": ["cust_12345"],
      "firstSeenFromIp": "2026-03-01T10:00:00Z",
      "lastSeenFromIp": "2026-06-10T14:30:00Z",
      "requestCount": 47
    }
  ]
}
```

---

### `POST /accounts/{accountId}/visitors/{visitorId}/verify`

Promote an observed binding to verified. Call this after the end user has completed a successful authentication challenge or transaction.

**Auth:** Secret key only.

**Request:** No body required.

**Response:**

```json
{
  "accountId": "cust_12345",
  "visitorId": "vis_a1b2c3d4",
  "bindingStatus": "verified",
  "verifiedAt": "2026-06-10T15:00:00Z"
}
```

---

### `DELETE /accounts/{accountId}/visitors/{visitorId}/verify`

Revoke a verified binding (demote back to observed). Use for incident response when a device is suspected of being compromised.

**Auth:** Secret key only.

**Response:**

```json
{
  "accountId": "cust_12345",
  "visitorId": "vis_a1b2c3d4",
  "bindingStatus": "observed",
  "revokedAt": "2026-06-10T16:00:00Z"
}
```

---

### `DELETE /visitors/{visitorId}`

Delete all data for a visitor. Use for GDPR right-to-erasure compliance.

**Auth:** Secret key only.

**Response:**

```json
{
  "visitorId": "vis_a1b2c3d4",
  "deleted": true,
  "recordsRemoved": {
    "signalSets": 142,
    "accountBindings": 2,
    "geolocations": 142
  }
}
```

---

## Proxied Setup

If the Collector cannot reach the Identification Server directly (e.g. the server is behind a firewall), route requests through your backend. Your backend acts as a transparent pass-through — forwarding the Collector's payload and injecting the real client IP.

### Collector Configuration

Point the Collector at your backend instead of the Identification Server:

```javascript
const collector = new SigilCollector({
  apiKey: 'pk_live_abc123...',
  serverUrl: 'https://www.mystore.com/api/fingerprint',  // your backend
});

const result = await collector.identify({ accountId: 'cust_12345' });
```

### Backend Proxy Endpoint

```python
@app.post("/api/fingerprint/identify")
async def proxy_identify(request: Request):
    client_ip = request.client.host

    response = await httpx.post(
        "https://sigil-server.internal/identify",
        headers={
            "Authorization": f"Bearer {SIGIL_SECRET_KEY}",
            "X-Forwarded-For": client_ip,
        },
        content=await request.body(),
    )
    return response.json()
```

The Identification Server reads the client IP from the `X-Forwarded-For` header (configurable via `SIGIL_TRUSTED_IP_HEADER`). In this setup, use a **secret key** for the backend-to-server call since the publishable key's CORS validation doesn't apply to server-to-server requests.

### Security Consideration

The Identification Server should only trust `X-Forwarded-For` from known sources. In the proxied setup, restrict network access to the server so that only your backend can reach it. This prevents an attacker from calling the server directly with a spoofed `X-Forwarded-For` header.

---

## Similarity Scoring

Sigil uses **weighted similarity scoring** to compare incoming signals against stored signal history. This is not a hash comparison — it tolerates partial changes (browser updates, screen changes) and returns a score between 0 and 1.

### How It Works

1. **Candidate filtering** — The server queries stored signal sets using indexed lookups on the highest-entropy signals (canvas hash, WebGL renderer, audio hash, font hash). This reduces millions of records to a small candidate set (~50-500 rows).

2. **Weighted scoring** — Each signal is compared (match = 1, no match = 0) and multiplied by its weight. The sum produces the similarity score.

3. **Ranking** — Candidates are sorted by score, filtered by a minimum threshold, and the top results are returned.

### Default Signal Weights

| Signal | Default Weight | Rationale |
|--------|---------------|-----------|
| Canvas hash | 0.20 | High entropy, high stability |
| WebGL renderer | 0.15 | High entropy, high stability |
| Audio hash | 0.15 | Medium entropy, high stability |
| Font hash | 0.15 | High entropy, medium stability |
| Screen resolution | 0.08 | Medium entropy, high stability |
| Platform / OS | 0.07 | Medium entropy, high stability |
| Timezone | 0.07 | Medium entropy, medium stability |
| Hardware concurrency | 0.05 | Low-med entropy, high stability |
| Device memory | 0.04 | Low-med entropy, high stability |
| Touch support | 0.02 | Low-med entropy, high stability |
| User-agent | 0.02 | Medium entropy, low stability |

### Overriding Weights

Configure custom weights via environment variables or a config file:

```yaml
# sigil-config.yaml
weights:
  canvas: 0.25
  webglRenderer: 0.20
  audioHash: 0.10
  fontHash: 0.15
  screenResolution: 0.08
  platform: 0.07
  timezone: 0.05
  hardwareConcurrency: 0.04
  deviceMemory: 0.03
  touchSupport: 0.02
  userAgent: 0.01
```

Weights must sum to 1.0. The server validates this on startup.

---

## Fraud Detection Patterns

Sigil provides data — the integrator makes decisions. Here are common patterns and which Sigil fields to use.

### Account Takeover (ATO)

An attacker logs in with stolen credentials from their own device.

**Signals to check:**
- `isKnownVisitorForAccount: false` — device has never been verified for this account
- `signalValidation: "new"` — no prior Visitor ID (first visit from this browser)
- `impossibleTravel.detected: true` — if the real user was active recently from a different location
- `similarVisitors[].accountIds` — if this device has been seen on other accounts (credential stuffing across accounts)

**Recommended action:** Trigger step-up authentication (OTP, email verification).

### Card Testing

A bot uses a single device to test many stolen card numbers at checkout.

**Signals to check:**
- `velocity.visitorRequestsLast10Min` — abnormally high request count from one device
- `velocity.ipDistinctAccountsLast1Hr` — one IP hitting many accounts

**Recommended action:** Block or CAPTCHA challenge after threshold is exceeded.

### New Account Fraud

An attacker creates many fake accounts to exploit promotions or launder funds.

**Signals to check:**
- `velocity.ipDistinctAccountsLast1Hr` — many new accounts from one IP
- `similarVisitors` with high similarity scores across many different accounts — same device creating accounts
- `GET /ip/{ipAddress}/visitors` — historical view of how many accounts this IP has spawned

**Recommended action:** Flag account for manual review, require phone verification.

### Promo Abuse

One person creates multiple accounts to reuse a first-time discount.

**Signals to check:**
- `similarVisitors` — high similarity to a visitor already linked to another account that redeemed the promo
- `velocity.ipDistinctAccountsLast1Hr` — multiple signups from same location

**Recommended action:** Deny promo, flag for review.

---

## Configuration Reference

The Identification Server is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string (required) |
| `IP_API_PRO_KEY` | — | API key for `pro.ip-api.com` geolocation lookups (optional, enables geolocation enrichment) |
| `SIGIL_RATE_LIMIT_RPS` | `20` | Max requests/second per publishable key |
| `SIGIL_RETENTION_DAYS` | `180` | Days to retain signal sets and geolocation history |
| `SIGIL_SIMILARITY_THRESHOLD` | `0.4` | Minimum similarity score to include in results |
| `SIGIL_SIMILARITY_MAX_RESULTS` | `10` | Maximum similar visitors to return |
| `SIGIL_IMPOSSIBLE_TRAVEL_MAX_SPEED_KMH` | `900` | Maximum plausible travel speed (km/h) for impossible travel detection |
| `SIGIL_TRUSTED_IP_HEADER` | `X-Forwarded-For` | HTTP header to read the client IP from |
| `SIGIL_CONFIG_PATH` | `sigil-config.yaml` | Path to config file for weight overrides |

---

## Data Retention

| Data | Retention | Rationale |
|------|-----------|-----------|
| Signal sets | 180 days (configurable) | Signals become stale as browsers and devices change |
| Geolocation history | 180 days (configurable) | Follows signal set lifecycle |
| Account bindings | Indefinite | Long-term device-account mapping is valuable even after signal details expire |
| Visitors | Kept while related data exists | Cleaned up when all signal sets and bindings are removed |

A scheduled job runs daily to prune expired records.

---

## Privacy

Sigil collects device fingerprints. Depending on your jurisdiction (GDPR, ePrivacy Directive, CCPA, etc.), you may need user consent before calling `collector.identify()`.

**Sigil's guarantees:**
- The Collector **never** collects signals automatically. Collection only happens when your code explicitly calls `identify()`.
- The Collector does not set cookies or write to localStorage on its own — the Visitor ID storage mechanism is controlled by the integrator.
- All data is stored in the integrator's own PostgreSQL database. Sigil has no hosted service and does not transmit data to third parties.
- The `DELETE /visitors/{visitorId}` endpoint supports right-to-erasure requests.

**The integrator is responsible for:**
- Obtaining user consent where required by applicable law
- Including fingerprint collection in their privacy policy
- Responding to data subject access and deletion requests (using Sigil's API)

---

## Database Schema

```sql
CREATE TABLE visitors (
    visitor_id    TEXT PRIMARY KEY,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE signal_sets (
    id              BIGSERIAL PRIMARY KEY,
    visitor_id      TEXT NOT NULL REFERENCES visitors(visitor_id) ON DELETE CASCADE,
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    canvas_hash     TEXT,
    webgl_renderer  TEXT,
    audio_hash      TEXT,
    font_hash       TEXT,
    signals_extra   JSONB NOT NULL DEFAULT '{}',

    CONSTRAINT fk_visitor FOREIGN KEY (visitor_id) REFERENCES visitors(visitor_id)
);

CREATE INDEX idx_signal_sets_visitor    ON signal_sets(visitor_id);
CREATE INDEX idx_signal_sets_canvas     ON signal_sets(canvas_hash);
CREATE INDEX idx_signal_sets_webgl      ON signal_sets(webgl_renderer);
CREATE INDEX idx_signal_sets_audio      ON signal_sets(audio_hash);
CREATE INDEX idx_signal_sets_font       ON signal_sets(font_hash);
CREATE INDEX idx_signal_sets_captured   ON signal_sets(captured_at);

CREATE TABLE account_bindings (
    visitor_id    TEXT NOT NULL,
    account_id    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'observed' CHECK (status IN ('observed', 'verified')),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at   TIMESTAMPTZ,
    PRIMARY KEY (visitor_id, account_id)
);

CREATE INDEX idx_bindings_account ON account_bindings(account_id);

CREATE TABLE geolocation_history (
    id          BIGSERIAL PRIMARY KEY,
    visitor_id  TEXT NOT NULL,
    account_id  TEXT,
    ip_address  INET NOT NULL,
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    country     TEXT,
    city        TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_geo_visitor    ON geolocation_history(visitor_id);
CREATE INDEX idx_geo_account    ON geolocation_history(account_id);
CREATE INDEX idx_geo_ip         ON geolocation_history(ip_address);
CREATE INDEX idx_geo_captured   ON geolocation_history(captured_at);

CREATE TABLE api_keys (
    id              BIGSERIAL PRIMARY KEY,
    key_type        TEXT NOT NULL CHECK (key_type IN ('publishable', 'secret')),
    key_hash        TEXT NOT NULL UNIQUE,
    key_prefix      TEXT NOT NULL,
    allowed_origins TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ
);
```

---

## API Quick Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/identify` | POST | Publishable or Secret | Submit signals, get identification result |
| `/visitors/{visitorId}` | GET | Secret | Get visitor detail with signal history |
| `/accounts/{accountId}/visitors` | GET | Secret | List all devices for an account |
| `/accounts/{accountId}/geolocations` | GET | Secret | Get geolocation history for an account |
| `/accounts/{accountId}/visitors/{visitorId}/verify` | POST | Secret | Mark a device as verified for an account |
| `/accounts/{accountId}/visitors/{visitorId}/verify` | DELETE | Secret | Revoke a verified device binding |
| `/ip/{ipAddress}/visitors` | GET | Secret | List all visitors from an IP address |
| `/visitors/{visitorId}` | DELETE | Secret | Delete all data for a visitor (GDPR) |

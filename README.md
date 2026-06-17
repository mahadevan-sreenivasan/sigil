# Sigil

A self-hosted browser fingerprint SDK for e-commerce fraud detection. Collects device signals, stores signal history, and provides similarity-ranked results so integrators can make informed fraud decisions.

## Packages

| Package | Path | Description |
|---------|------|-------------|
| `@sigil/collector` | `collector/` | TypeScript library that runs in the browser, gathers device signals, and sends them to the Identification Server |
| `sigil-server` | `server/` | Python/FastAPI service that receives signals, stores them in PostgreSQL, and returns identification results |
| `@sigil/dashboard` | `dashboard/` | React SPA for investigating visitors, accounts, and devices |

## Quick Start

### Docker Compose (recommended)

The fastest way to run a complete Sigil instance locally:

```bash
# 1. Set your ip-api Pro key for geolocation enrichment:
#    https://ip-api.com/docs/api:json
export IP_API_PRO_KEY=your-ip-api-pro-key

# 2. Start the server and PostgreSQL
docker compose up -d

# 3. Verify it's running
curl http://localhost:8080/health
# → {"status": "healthy"}
```

The server will be available at `http://localhost:8080`.

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://sigil:sigil@postgres:5432/sigil` | PostgreSQL connection string (required) |
| `IP_API_PRO_KEY` | — | API key for `pro.ip-api.com` geolocation lookups |
| `SIGIL_CONFIG_PATH` | `sigil-config.yaml` | Path to signal weights config file |
| `SIGIL_RATE_LIMIT_RPS` | `20` | Requests per second per API key |

#### Geolocation Provider Setup

Sigil resolves geolocation via `pro.ip-api.com` when `IP_API_PRO_KEY` is configured.

1. Provision an ip-api Pro key from https://ip-api.com
2. Set `IP_API_PRO_KEY` in your runtime environment (or `.env`)
3. Restart the server if you updated environment variables

> **Note:** The server starts without `IP_API_PRO_KEY` (a warning is logged), but geolocation enrichment will be unavailable.

### Collector

```bash
cd collector
npm install
npm run build    # Build the library
npm test         # Run tests (Vitest)
```

### Identification Server

```bash
cd server
python -m venv .venv
# Windows: .venv\Scripts\pip install -e ".[dev]"
# Unix:    .venv/bin/pip install -e ".[dev]"

# Run tests
.venv/bin/pytest          # Unix
.venv\Scripts\pytest      # Windows

# Run the server (requires DATABASE_URL)
DATABASE_URL=postgresql://user:pass@localhost:5432/sigil .venv/bin/uvicorn sigil_server.main:app
```

### Dashboard

```bash
cd dashboard
npm install
npm run build    # Build the SPA
npm run dev      # Dev server
```

## Monorepo Scripts

From the root:

```bash
npm install          # Install collector + dashboard dependencies
npm run build        # Build collector and dashboard
npm test             # Run collector tests
```

## Documentation

- [Integration Guide](docs/integration-guide.md) — API reference, setup instructions, fraud detection patterns
- [Domain Glossary](CONTEXT.md) — Canonical vocabulary used across the project
- [ADRs](docs/adr/) — Architecture decision records

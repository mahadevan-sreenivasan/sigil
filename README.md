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
# 1. Obtain the MaxMind GeoLite2-City database (free, requires registration):
#    https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
#    Place the .mmdb file at: data/GeoLite2-City.mmdb
mkdir -p data

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
| `MAXMIND_DB_PATH` | `/data/GeoLite2-City.mmdb` | Path to MaxMind GeoLite2-City database |
| `SIGIL_CONFIG_PATH` | `sigil-config.yaml` | Path to signal weights config file |
| `SIGIL_RATE_LIMIT_RPS` | `20` | Requests per second per API key |

#### MaxMind GeoLite2-City Database

The geolocation feature requires a MaxMind GeoLite2-City database file:

1. Create a free account at https://www.maxmind.com/en/geolite2/signup
2. Download the GeoLite2-City database (`.mmdb` format)
3. Place the file at `data/GeoLite2-City.mmdb` in the repo root

> **Note:** The server starts without this file (a warning is logged), but geolocation features will be unavailable.

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

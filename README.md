# Sigil

A self-hosted browser fingerprint SDK for e-commerce fraud detection. Collects device signals, stores signal history, and provides similarity-ranked results so integrators can make informed fraud decisions.

## Packages

| Package | Path | Description |
|---------|------|-------------|
| `@sigil/collector` | `collector/` | TypeScript library that runs in the browser, gathers device signals, and sends them to the Identification Server |
| `sigil-server` | `server/` | Python/FastAPI service that receives signals, stores them in PostgreSQL, and returns identification results |
| `@sigil/dashboard` | `dashboard/` | React SPA for investigating visitors, accounts, and devices |

## Quick Start

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

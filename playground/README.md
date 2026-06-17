# Sigil Playground

`@sigil/playground` is a local developer harness for running `@sigil/collector` in a browser and verifying `/identify` responses from the Sigil server.

## Local setup

1. Install workspace dependencies from repo root:

   ```bash
   npm install
   ```

2. Start the Playground from repo root:

   ```bash
   npm run dev:playground
   ```

3. Open `http://localhost:5174`.

4. Configure:
   - **Server URL** (default: `http://localhost:8080`)
   - **Publishable Key** (`pk_...`)

## CORS / allowed origins

The publishable key must include the Playground dev origin in `allowedOrigins` or browser CORS checks will block `POST /identify`.

Example key creation against a local server:

```bash
curl -X POST http://localhost:8080/admin/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"allowedOrigins": ["http://localhost:5174"]}'
```

Use the returned `publishableKey` value in the Playground settings panel.

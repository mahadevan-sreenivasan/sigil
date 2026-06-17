## Parent

#18

## What to build

First tracer bullet for the Playground developer harness: a new `@sigil/playground` monorepo workspace (Vite + React + TypeScript, dev server on port 5174) that depends on the workspace `@sigil/collector` package.

Deliver a clean, simple UI shell with a settings panel and server-connected identification as the default mode. Settings persist `serverUrl` (default `http://localhost:8080`) and publishable API key in localStorage across reloads. A single **Identify** action instantiates `SigilCollector` and calls `/identify`. After each run, display all 15 Device Signals and Session Signals in a readable table, plus a basic Identification Server summary (Visitor ID, Fingerprint ID, `signalValidation`, `isNewVisitor`).

Status banners: green when server-connected and `serverReachable: true`; red when the Collector returns a degraded result (`serverReachable: false`) — still show collected signals. Show validation feedback when the publishable key is missing on a server-connected attempt.

Wire the package into root npm workspaces with a `dev:playground` script. Add a Playground README covering local setup, including creating a publishable key with the Playground dev origin in `allowedOrigins` so CORS does not block `/identify`.

Unit tests via React Testing Library with `SigilCollector` mocked at the module boundary — settings persistence, identify flow, success/unreachable banners, missing-key validation.

## Acceptance criteria

- [ ] `@sigil/playground` workspace exists and runs on port 5174 without conflicting with the Dashboard dev server
- [ ] Settings panel persists server URL and publishable key in localStorage with documented defaults
- [ ] Identify calls the Collector against the configured Identification Server and renders all 15 signals in a table
- [ ] Basic server response summary is visible on success (Visitor ID, Fingerprint ID, signal validation, isNewVisitor)
- [ ] Green banner on successful server-connected identify; red banner with signals visible when server is unreachable
- [ ] User sees clear feedback when identify is attempted without a publishable key configured
- [ ] Root monorepo includes playground workspace and dev script
- [ ] Playground README documents CORS / allowed-origins setup for local development
- [ ] RTL tests cover settings persistence, identify action, and banner behavior with mocked Collector

## Blocked by

None — can start immediately

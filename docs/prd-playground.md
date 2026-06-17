# PRD: Playground — Developer Harness for Fingerprint Capabilities

## Problem Statement

Sigil ships a Collector (browser signal gathering), an Identification Server (fingerprint computation, similarity scoring, velocity, geolocation, impossible travel, account bindings), and a Dashboard (read-only fraud investigation). There is no dedicated tool for developers building or modifying Sigil to exercise the full identification pipeline in a real browser.

Unit tests mock HTTP and browser APIs — they cannot validate that canvas, WebGL, audio, and font Device Signals behave correctly across Chrome, Firefox, and Safari. The Dashboard is aimed at fraud analysts investigating stored visitors, not at live signal debugging during development. Developers currently lack a quick way to confirm that all fingerprint capabilities work end-to-end after a change.

## Solution

Add a **Playground**: a browser-based developer harness packaged as a new monorepo workspace. It runs the Collector in a real browser, calls the Identification Server by default, displays all collected Device Signals and Server-Captured Signal results, and maintains a run history for cross-browser comparison. It supports an explicit signals-only mode for Collector iteration without a running server, with clear status banners for each mode.

## User Stories

1. As a Sigil developer, I want a dedicated Playground application separate from the Dashboard, so that I can debug live identification without mixing dev tooling with fraud investigation workflows.

2. As a Sigil developer, I want the Playground to live in its own monorepo workspace package, so that the Collector remains a publishable library and the Dashboard remains focused on investigation.

3. As a Sigil developer, I want to configure the Identification Server URL and publishable API key in a settings panel, so that I can point the Playground at my local Docker Compose stack or any other environment.

4. As a Sigil developer, I want settings persisted in localStorage across page reloads, so that I do not re-enter credentials every time I restart the dev server.

5. As a Sigil developer, I want sensible defaults (Identification Server at `http://localhost:8080`, empty key until configured), so that local setup requires minimal configuration.

6. As a Sigil developer, I want server-connected identification to be the default mode, so that I exercise the full round-trip (Collector → Identification Server → response) on every run unless I opt out.

7. As a Sigil developer, I want an explicit "Signals only" action that skips the network call, so that I can iterate on Device Signal collection without PostgreSQL or the Identification Server running.

8. As a Sigil developer, I want automatic fallback when the Identification Server is unreachable, so that I still see collected Device Signals with a clear "server unreachable" banner instead of a blank error.

9. As a Sigil developer, I want color-coded status banners distinguishing server-connected success, signals-only mode, and server-unreachable fallback, so that I always know which mode produced the current result.

10. As a Sigil developer, I want a single "Identify" action that invokes the Collector and posts to `/identify`, so that I can trigger a full identification with one click.

11. As a Sigil developer, I want to see all 15 Collector Device Signals and Session Signals in a readable table after each run, so that I can verify canvas, WebGL, audio, fonts, screen, platform, memory, touch, timezone, and user-agent values.

12. As a Sigil developer, I want to see the full Identification Server response after each run, so that I can verify Visitor ID, Fingerprint ID, signal validation, similar visitors, velocity, geolocation, impossible travel, and account history.

13. As a Sigil developer, I want the Playground to surface response fields not yet present on the Collector's typed result interface (e.g. account history), so that no server capability is hidden due to Collector type gaps.

14. As a Sigil developer, I want the Playground to automatically persist the returned Visitor ID in localStorage and send it on subsequent identify calls, so that return-visit behavior (`signalValidation: match`) mirrors integrator production usage.

15. As a Sigil developer, I want a "Reset visitor" control that clears the stored Visitor ID, so that I can simulate a first visit or switch to a fresh visitor session.

16. As a Sigil developer, I want an optional Account ID field per request, so that I can exercise Observed Bindings, account history, velocity per account, and Impossible Travel detection.

17. As a Sigil developer, I want a scrollable run history log of past identifications, so that I can compare results across browsers or before/after code changes without re-running immediately.

18. As a Sigil developer, I want each history entry to include a timestamp and key summary fields (Visitor ID, Fingerprint ID, signal validation, server reachability), so that I can scan the log quickly.

19. As a Sigil developer, I want each history entry to retain full Device Signals and server response detail on expand or in the entry body, so that I can drill into any past run.

20. As a Sigil developer, I want a clean, simple UI with structured layout (settings, actions, latest result, history), so that the tool is usable without Dashboard-level polish.

21. As a Sigil developer, I want readable signal tables rather than raw JSON only, so that cross-browser comparison is practical.

22. As a Sigil developer, I want the Playground dev server on a distinct port from the Dashboard dev server, so that I can run both simultaneously without conflict.

23. As a Sigil developer, I want root monorepo scripts to build and run the Playground, so that it follows the same workflow as the Collector and Dashboard packages.

24. As a Sigil developer, I want brief setup documentation explaining API key creation with the Playground origin in allowed origins, so that CORS does not block `/identify` calls during local development.

25. As a Sigil developer, I want the Playground to depend on the workspace Collector package, so that changes to the Collector are immediately exercisable without publishing.

26. As a Sigil developer, I want signals-only mode to use the same signal collection path as server-connected mode, so that signal output is identical regardless of mode.

27. As a Sigil developer, I want the latest result panel to update on each identify while preserving prior runs in history, so that I always see the most recent outcome prominently.

28. As a Sigil developer, I want validation feedback when the publishable key is missing during a server-connected identify attempt, so that I understand why the call cannot proceed.

29. As a Sigil developer, I want to see Similarity Score and matching/mismatched signal lists for similar visitors in the response display, so that I can verify structured similarity scoring behavior.

30. As a Sigil developer, I want to see velocity counts in the response display, so that I can verify rate-based detection fields.

31. As a Sigil developer, I want to see geolocation and Impossible Travel fields in the response display, so that I can verify Server-Captured Signal and geo anomaly behavior when ip-api is configured.

32. As a Sigil developer, I want the Playground excluded from production deployment artifacts, so that it remains a local development tool only.

## Implementation Decisions

- **New package**: Add `@sigil/playground` as a third npm workspace alongside `@sigil/collector` and `@sigil/dashboard`. Private package, not published.

- **Stack**: Vite + React + TypeScript, matching the Dashboard toolchain (Vitest + React Testing Library for unit tests).

- **Collector dependency**: Import and instantiate `SigilCollector` from the workspace `@sigil/collector` package. Build order: Collector must be buildable/resolvable by the Playground dev server (workspace link).

- **Settings model**: Two persisted fields in localStorage — `serverUrl` (default `http://localhost:8080`) and `publishableKey` (default empty). Settings panel accessible from the main layout; changes save on submit or blur.

- **Visitor ID persistence**: Separate localStorage key for `visitorId`. Updated automatically after a successful server-connected identify when the response includes a Visitor ID. Not updated in signals-only mode (no server-assigned ID). "Reset visitor" clears this key.

- **Account ID**: Ephemeral text input per session (not persisted to localStorage unless useful for dev convenience — default: do not persist Account ID).

- **Identification modes**:
  - **Server-connected (default)**: Calls `SigilCollector.identify({ visitorId?, accountId? })`. Requires publishable key.
  - **Signals only**: Calls signal collectors directly OR invokes Collector internals without posting — preferred approach: extract/display via a dedicated signals-only code path that reuses the same collection logic as `identify()` but skips `fetch`. May duplicate the collection block from Collector or add a public `collectSignals()` method on Collector if that is cleaner (agent's choice — prefer extending Collector with a `collectSignals()` export over copy-paste).
  - **Automatic fallback**: When `identify()` returns `serverReachable: false`, display signals and degraded result with a red/unreachable banner.

- **Status banners**:
  - Green/success: server-connected, `serverReachable: true`
  - Yellow/info: explicit signals-only mode
  - Red/warning: server-connected attempt failed (`serverReachable: false`)

- **Results layout**:
  - **Latest result**: Device Signals table + structured server response sections (identification summary, similar visitors list, velocity, geolocation, impossible travel, account history).
  - **Run history**: Append-only list (newest first or oldest first — agent choice; recommend newest first). Each entry: timestamp, mode banner, summary fields, expandable detail.

- **UI styling**: Clean and simple — light CSS, no shared Dashboard design system. Structured panels, monospace for IDs/hashes, color-coded banners. Not barebones unstyled HTML.

- **Dev server port**: Use a port distinct from Dashboard default (5173) — recommend 5174.

- **Root workspace scripts**: Add `playground` to npm workspaces array. Add `dev:playground`, include in documentation. Optional: add to root `build` script or keep playground dev-only (recommend dev-only build script, not required in CI build chain initially).

- **Collector type gap**: `IdentificationResult` does not include `accountHistory`. Playground should render the raw `/identify` JSON for complete server fields. Optionally extend `IdentificationResult` and Collector parsing to include `accountHistory` — recommended as a small Collector enhancement if trivial, but not blocking Playground v1.

- **No Identification Server changes**: Playground is client-only. No new API endpoints, schema changes, or server modifications required.

- **No Dashboard changes**: Playground is independent; no deep links or shared routes in v1.

- **CORS prerequisite**: Document that the publishable key used must include the Playground dev origin (e.g. `http://localhost:5174`) in `allowedOrigins` when created via Admin Token.

- **Domain vocabulary**: Use terms from CONTEXT.md — Playground, Collector, Identification Server, Device Signal, Session Signal, Visitor ID, Fingerprint ID, Similarity Score, Account ID, Observed Binding, Impossible Travel, Velocity, Server-Captured Signal.

## Testing Decisions

**Principle**: Test external UI behavior through React Testing Library — assert on rendered output and user interactions, not internal state shape or CSS class names. Mock `SigilCollector` at the module boundary (same seam as `collector/tests/identify.test.ts` mocks signal modules and `fetch`).

**Seams** (highest first):

1. **Playground UI + mocked Collector** (primary): Render the app with `SigilCollector` mocked. Verify settings persistence, identify button behavior, banner text for each mode, history append, visitor reset, account ID passed through. Prior art: `dashboard/src/components/Login.test.tsx` (storage + form submit), `collector/tests/identify.test.ts` (mocked fetch/collector boundary).

2. **Settings persistence seam**: Test localStorage read/write for server URL and publishable key on load and save. Prior art: Dashboard Login sessionStorage tests.

3. **Visitor ID persistence seam**: Test that a successful mocked identify stores Visitor ID and subsequent calls include it; test reset clears it.

4. **Signals-only seam**: Test that signals-only action does not invoke `identify()` (or invokes only `collectSignals()`), renders yellow banner, and displays signal table.

5. **Do not test** real canvas/WebGL/audio/font collection in Playground unit tests — that requires a real browser (manual QA). Do not duplicate Collector's signal collection tests.

6. **Do not test** Identification Server HTTP behavior from Playground tests — covered by `server/tests/test_identify.py`, `test_signal_validation.py`, etc.

**Manual QA checklist** (document in Playground README, not automated):

- Server-connected identify against local Docker Compose
- Signals-only with server stopped
- Return visit (Visitor ID match) after reload
- Account ID binding and velocity fields
- Cross-browser signal comparison via history log

## Out of Scope

- **Admin Token bootstrap UI** — creating publishable keys from the Playground via `/admin/api-keys`. Developers create keys via curl/CLI and paste into settings.

- **Signal tampering controls** — editing Device Signals before send to force `signalValidation: mismatch`. Manual testing via different browser profiles is sufficient for v1.

- **Dashboard deep links** — navigating from Playground to Dashboard visitor detail pages.

- **Automated pass/fail assertions** — CI regression suite for capabilities. That belongs in Collector/Server test suites, not the Playground.

- **Integrator demo polish** — onboarding flows, branding, or production deployment of the Playground.

- **Multi-tab synchronization or WebSocket live updates**.

- **Proxy mode documentation UI** — backend pass-through setup is documented in the integration guide, not replicated in Playground.

- **Secret key authentication** — Playground uses publishable keys only (same as production Collector integration).

## Further Notes

- CONTEXT.md already defines **Playground** in the domain glossary.
- ADR-0001 (structured similarity scoring) is relevant context for displaying similar visitors — the Playground verifies the scoring output, not the algorithm.
- Recommended local workflow: `docker compose up -d` → create publishable key with Playground origin in allowed origins → `npm run dev` in Playground workspace → paste key in settings → identify.
- The Collector currently collects 15 signals (4 async Device Signals + 11 Session/simple signals). PRD references "15 signals" consistently.
- If adding `collectSignals()` to Collector, add a focused unit test in the Collector package — not in Playground.

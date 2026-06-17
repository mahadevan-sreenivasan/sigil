# Sigil

A browser fingerprint SDK that collects device and session signals to help e-commerce platforms detect fraud (account takeover, new account fraud, card testing). Ships as a client-side Collector (npm package), a self-hosted Identification Server (Docker image), and an investigation Dashboard (React SPA).

## Language

**Fingerprint**:
A composite identifier derived from device and session signals, used to recognize a browser environment across visits.
_Avoid_: Token, tracking ID, device ID

**Device Signal**:
A hardware or software attribute of the browser environment that is stable across sessions (e.g. canvas hash, WebGL renderer, installed fonts).
_Avoid_: Device fingerprint (when referring to individual signals)

**Session Signal**:
A transient attribute of the current browsing session that may change between visits (e.g. IP address, timezone, language, user-agent).
_Avoid_: Request metadata, context signal

**Collector**:
The client-side JavaScript library that runs in the browser, gathers device and session signals, and sends them to the Identification Server.
_Avoid_: Agent, tracker, pixel, SDK (when referring specifically to the client)

**Identification Server**:
The self-hosted server that receives raw signals from the Collector, computes fingerprints, stores signal history, and returns ranked similar fingerprints with similarity scores.
_Avoid_: Backend, fingerprint service, SaaS

**Similarity Score**:
A value between 0 and 1 representing how closely two signal sets match, computed as a weighted sum of per-signal comparisons.
_Avoid_: Match score, confidence, risk score

**Signal Weight**:
A numeric value reflecting how much a given signal contributes to the Similarity Score, based on its entropy and stability.
_Avoid_: Priority, importance

**Visitor ID**:
A server-generated opaque identifier stored in the browser (cookie/localStorage) used as a lookup key to find a visitor's signal history. Never trusted on its own — incoming signals are always validated against stored signals for that Visitor ID.
_Avoid_: Session ID, device ID, tracking ID

**Fingerprint ID**:
A content-derived hash of the top stable signals, used for similarity search when no Visitor ID is present or when the Visitor ID's signals don't match.
_Avoid_: Hash, device hash

**Account ID**:
An opaque string identifier provided by the integrator that represents an end user in their system. Used to bind visitors to accounts so the server can answer "what devices has this account used?" and "what other accounts has this device visited?"
_Avoid_: User ID, customer ID, tenant (when referring to an end user)

**Observed Binding**:
An account-to-visitor association created automatically when an identification request includes an Account ID. Records that the device was *seen* with this account, but does not imply trust.
_Avoid_: Linked, associated

**Verified Binding**:
An account-to-visitor association explicitly promoted by the integrator after a successful authentication or transaction. Only verified bindings cause `isKnownVisitorForAccount` to return true.
_Avoid_: Trusted, approved, whitelisted

**Server-Captured Signal**:
A signal derived by the Identification Server from the HTTP request itself, not from the Collector. IP address is the primary example — it cannot be forged by the client.
_Avoid_: Server signal, request signal

**Impossible Travel**:
A detection where two requests for the same Account ID originate from geolocations that are physically unreachable within the elapsed time between them.
_Avoid_: Geo anomaly (when specifically referring to time-distance violations)

**Dashboard**:
A React SPA used by the integrator's fraud or security team to investigate visitors, accounts, devices, and geolocation history. Read-only, authenticated with a secret key.
_Avoid_: Admin panel, console, portal

**Velocity**:
The rate of identification requests for a given entity (visitor, account, or IP) within a time window. High velocity is a strong indicator of automated attacks such as card testing or credential stuffing.
_Avoid_: Rate, frequency, throughput

**Playground**:
A browser-based developer harness for exercising the Collector and Identification Server during local development. Displays raw signals and full identification results, with controls to trigger edge-case scenarios. Not for production fraud investigation — that is the Dashboard's job.
_Avoid_: Demo app, sandbox, test UI
**Admin Token**:
A pre-shared secret set via the `SIGIL_ADMIN_TOKEN` environment variable, used to authenticate operator-level actions on the `/admin/*` endpoints (creating, listing, and revoking API keys). Distinct from API keys — the admin token is an operator credential (for whoever deploys the server), not an integrator credential (for the application that uses Sigil).
_Avoid_: Admin key, master key, root key

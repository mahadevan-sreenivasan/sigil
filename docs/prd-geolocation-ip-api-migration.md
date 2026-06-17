# PRD: Identification Server Geolocation Migration to ip-api Pro

## Problem Statement

Sigil's Identification Server geolocation path currently relies on MaxMind database operational setup. That creates unnecessary deployment overhead and diverges from the target provider strategy. The team needs to migrate geolocation enrichment to `pro.ip-api.com` while preserving existing `identify` behavior and response contract stability.

## Solution

Replace MaxMind-based geolocation enrichment in the Identification Server with explicit-IP lookups to `pro.ip-api.com`, authenticated via environment variable. Preserve fail-open behavior so geolocation enrichment can degrade independently without affecting the rest of identification processing.

## User Stories

1. As a Sigil integrator, I want geolocation enrichment to use `pro.ip-api.com`, so that I no longer manage MaxMind database files.
2. As a Sigil integrator, I want `/identify` to continue succeeding when geo provider calls fail, so that fraud and authentication flows are not blocked by provider outages.
3. As a Sigil developer, I want geolocation lookup to query explicit client IPs, so that proxied deployments resolve the end-user location rather than server egress location.
4. As a Sigil developer, I want fast-fail geolocation requests, so that `/identify` latency remains predictable.
5. As a Sigil developer, I want no retry behavior on geolocation lookups, so that tail latency is bounded under provider degradation.
6. As a Sigil integrator, I want the existing geolocation response contract unchanged, so that downstream Collector/Dashboard/Playground consumers remain compatible.
7. As a Sigil maintainer, I want provider logic isolated behind a resolver abstraction, so that provider integration remains testable and replaceable.
8. As a Sigil operator, I want one explicit environment variable for provider authentication, so that deployment configuration is clear.
9. As a Sigil operator, I want startup to warn when the key is missing (without hard failure), so that non-geo environments can still run safely.
10. As a Sigil maintainer, I want deterministic mocked tests for provider integration, so that CI does not depend on external network calls.
11. As a Sigil maintainer, I want all MaxMind references removed from setup docs, so that onboarding instructions are consistent with runtime behavior.
12. As a fraud analyst using Sigil outputs, I want Impossible Travel and velocity behavior unchanged from a contract perspective, so that investigation workflows remain stable.
13. As a Sigil developer, I want manual live-provider smoke checks deferred, so that this migration can ship based on stable automated tests first.
14. As a Sigil maintainer, I want this migration scoped to backend provider replacement only, so that schema/UI expansion does not delay delivery.

## Implementation Decisions

- Use `https://pro.ip-api.com` as the geolocation provider for Identification Server enrichment.
- Query explicit client IPs in path format (`/json/{client_ip}?key=...`).
- Use `IP_API_PRO_KEY` for provider authentication.
- If `IP_API_PRO_KEY` is missing, startup logs warning and geolocation enrichment is disabled.
- Geolocation enrichment is fail-open: if provider call fails, `/identify` returns normally with geolocation enrichment omitted.
- Use fast-fail timeout policy with no retries.
- Keep response geolocation fields unchanged: `ip`, `country`, `city`, `latitude`, `longitude`.
- Ignore extra provider fields (`regionName`, `timezone`, `isp`, `as`, etc.) in this scope.
- Preserve resolver abstraction and implement provider-specific behavior behind it.
- Prefer app-scoped shared HTTP client for connection reuse and stable performance.
- Include docs/config cleanup replacing MaxMind setup with ip-api configuration.

## Testing Decisions

- Good tests validate external behavior and contract outcomes, not internal implementation details.
- Primary seam: resolver boundary tested with mocked HTTP transport to verify explicit-IP URL construction, key usage, success mapping, and failure handling.
- Integration seam: `/identify` flow tested with mocked geolocation outcomes to verify fail-open behavior and non-geo fields unaffected.
- Config seam: startup behavior tested for key-present and key-missing paths.
- Acceptance scope for this phase: mocked automated tests only; manual live-provider smoke test deferred.

## Out of Scope

- Adding new geolocation fields to server response contracts.
- Dashboard, Collector, or Playground feature/UI expansion for additional geo attributes.
- Retry/backoff/circuit-breaker logic for provider calls.
- Multi-provider routing or provider failover strategy.
- Mandatory live provider integration tests in CI.

## Further Notes

- This is a provider migration, not a product-surface expansion.
- Geolocation remains a Server-Captured Signal enrichment with graceful degradation.
- A follow-up can explicitly propose response-contract expansion if extra ip-api attributes become required.

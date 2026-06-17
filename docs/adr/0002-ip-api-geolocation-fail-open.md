# Migrate geolocation enrichment to ip-api Pro with fail-open explicit-IP lookups

We are replacing MaxMind database-based geolocation with `pro.ip-api.com` using explicit client IP lookups and an API key (`IP_API_PRO_KEY`). We intentionally keep geolocation as a best-effort Server-Captured Signal enrichment: when provider calls fail or the key is missing, `identify` still succeeds and only geolocation enrichment is omitted. This decision trades richer provider payload and retry complexity for low operational overhead, bounded latency, and strict backward compatibility of Sigil's current geolocation response contract.

## Considered Options

- **Keep MaxMind DB**: Rejected due to operational burden of database provisioning and updates.
- **Use ip-api caller-IP endpoint (`/json/?key=...`)**: Rejected because it can resolve server egress IP instead of extracted client IP in proxied deployments.
- **Fail-closed on geolocation errors**: Rejected because geolocation outages should not block core identification flows.
- **Include all ip-api fields in response now**: Rejected to avoid API contract expansion and downstream consumer changes in this migration scope.

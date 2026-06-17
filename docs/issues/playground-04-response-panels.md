## Parent

#18

## What to build

Expand the Playground latest-result view to surface the full Identification Server response in structured panels, and close the Collector type gap for account history.

Extend `IdentificationResult` and Collector response parsing to include `accountHistory`. Add structured UI sections for: similar visitors (Similarity Score, matching and mismatched signals), Velocity, geolocation (Server-Captured Signal), Impossible Travel, and account history. Keep the layout clean and simple — readable sections, not raw JSON only.

RTL tests verify each section renders correctly from mocked identify responses.

## Acceptance criteria

- [ ] Collector typed result includes `accountHistory` parsed from `/identify` responses
- [ ] Collector unit test covers `accountHistory` parsing
- [ ] Playground displays similar visitors with Similarity Score and matching/mismatched signal lists
- [ ] Playground displays Velocity counts when present in the response
- [ ] Playground displays geolocation fields when present
- [ ] Playground displays Impossible Travel fields when present
- [ ] Playground displays account history when present
- [ ] RTL tests render each response section from mocked data

## Blocked by

- #19

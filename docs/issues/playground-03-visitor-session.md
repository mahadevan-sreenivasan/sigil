## Parent

#18

## What to build

Add visitor session simulation to the Playground so developers can exercise return-visit and account-binding behavior against the Identification Server.

After a successful server-connected identify, automatically persist the returned Visitor ID in localStorage and include it on subsequent identify calls. Add a **Reset visitor** control that clears the stored Visitor ID to simulate a first visit. Add an optional Account ID text field (ephemeral per session — do not persist to localStorage) passed through to `SigilCollector.identify()`.

## Acceptance criteria

- [ ] Visitor ID is saved to localStorage after a successful server-connected identify
- [ ] Subsequent identify calls include the stored Visitor ID
- [ ] **Reset visitor** clears stored Visitor ID; next identify behaves as a first visit
- [ ] Optional Account ID field is passed to the Collector when provided
- [ ] Account ID is not persisted across page reloads by default
- [ ] RTL tests cover Visitor ID persist/re-send, reset, and Account ID passthrough with mocked Collector

## Blocked by

- #19

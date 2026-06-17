## Parent

#18

## What to build

Add signals-only mode end-to-end across the Collector and Playground.

Extend `SigilCollector` with a public `collectSignals()` method that runs the same signal collection path as `identify()` but skips the network call to the Identification Server. Add a focused unit test in the Collector package.

In the Playground, add a **Signals only** action that calls `collectSignals()`, displays the same 15-signal table as server-connected mode, and shows a yellow status banner. No Visitor ID is assigned or persisted in this mode.

## Acceptance criteria

- [ ] `SigilCollector.collectSignals()` is exported and returns the same signal shape used by `identify()`
- [ ] Collector unit test verifies `collectSignals()` does not call `fetch`
- [ ] Playground **Signals only** button collects and displays all 15 signals without contacting the Identification Server
- [ ] Yellow banner clearly indicates signals-only mode
- [ ] Signals-only mode does not update stored Visitor ID
- [ ] RTL test verifies signals-only path shows yellow banner and does not invoke `identify()`

## Blocked by

- #19

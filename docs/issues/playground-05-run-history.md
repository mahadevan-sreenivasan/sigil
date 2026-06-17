## Parent

#18

## What to build

Add a scrollable run history log to the Playground for cross-browser and before/after comparison during development.

Each identify or signals-only run appends an entry (newest first). Entries include timestamp, mode banner (server success / signals-only / server unreachable), summary fields (Visitor ID, Fingerprint ID, signal validation, server reachability), and expandable detail with full Device Signals and server response. The latest result panel remains prominent; prior runs stay in history.

## Acceptance criteria

- [ ] Each identify and signals-only run appends a history entry
- [ ] History is ordered newest first
- [ ] Each entry shows timestamp and mode-appropriate banner
- [ ] Each entry shows summary fields for quick scanning
- [ ] Expandable detail shows full signals and server response for any past run
- [ ] Latest result panel updates on each run without losing prior history entries
- [ ] RTL tests cover history append, ordering, and expand/collapse behavior

## Blocked by

- #19
- #20
- #21
- #22

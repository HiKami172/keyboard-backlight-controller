# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** User can visually configure and switch keyboard backlight modes without touching the terminal — and the setting persists across reboots.
**Current focus:** Phase 1 — Permissions and Hardware Foundation

## Current Position

Phase: 1 of 5 (Permissions and Hardware Foundation)
Plan: 2 of TBD in current phase
Status: In progress
Last activity: 2026-02-21 — Plan 02 complete: BacklightController implementation + 14-test unit suite

Progress: [██░░░░░░░░] 10%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 2 min
- Total execution time: 3 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-permissions-and-hardware-foundation | 2 | 3 min | 2 min |

**Recent Trend:**
- Last 5 plans: 1 min, 2 min
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: TUF F16 only, no multi-model support — simpler for personal use
- [Init]: udev rule with RUN+chgrp/chmod (NOT GROUP=/MODE= — unreliable on sysfs attribute files)
- [Init]: Full GTK4 window + AppIndicator3 tray — window for setup, tray for daily switching
- [Phase 1]: Confirm actual sysfs path with `ls /sys/class/leds/asus*` on hardware before any code
- [Phase 4]: Validate gi.repository.AppIndicator3 import path on Ubuntu 24.04 before implementing tray
- [01-01]: plugdev group used (not video) — hikami is in plugdev; video group has no members on this machine
- [01-01]: KERNEL=="asus::kbd_backlight*" wildcard handles asus::kbd_backlight_1 rename variant (Red Hat BZ #1665505)
- [01-02]: No hardcoded sysfs path in production code — SYSFS_GLOB + pathlib glob at init time
- [01-02]: persist=False default (cmd=0) — callers must opt in to firmware save; prevents accidental firmware writes during live preview
- [01-02]: strobe mode (3) included despite open hardware question — hardware test deferred to Phase 1 live verification

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 4]: GNOME Shell requires `gnome-shell-extension-appindicator` for tray icons — must detect and surface user-facing error if missing
- [Phase 4]: Confirm trayer vs. direct AppIndicator3 GObject introspection binding during Phase 4 planning
- [Phase 5]: Wayland global hotkeys (KEYS-01, KEYS-02) — XDG Desktop Portal Global Shortcuts API not fully researched; may hit implementation constraints

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 01-02-PLAN.md — BacklightController implementation + 14-test unit suite done.
Resume file: None

---
phase: 01-permissions-and-hardware-foundation
plan: 02
subsystem: infra
tags: [sysfs, pathlib, backlight, hardware-abstraction, unittest, asus-nb-wmi]

# Dependency graph
requires:
  - phase: 01-01
    provides: Python package skeleton (kbd_backlight.hardware, tests.hardware) with __init__.py stubs
provides:
  - BacklightController class with sysfs glob discovery and validated apply()
  - HardwareNotFoundError(RuntimeError) with actionable asus-nb-wmi message
  - MODES dict (static=0, breathing=1, color_cycle=2, strobe=3)
  - SYSFS_GLOB constant
  - 14-test unit suite covering all modes, persist flag, validation, error types, path property
affects:
  - 02-hardware-abstraction-layer
  - all subsequent phases (BacklightController is the sole hardware write interface)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - BacklightController(sysfs_path=None) — None triggers glob discovery; injected path enables hardware-free testing
    - payload format: "{cmd} {mode_int} {r} {g} {b} {speed}\n" written via Path.write_text()
    - persist=False default (cmd=0) — live preview; persist=True (cmd=1) — firmware save
    - PermissionError wrapping with udev install instructions surfaced to caller

key-files:
  created:
    - kbd_backlight/hardware/backlight.py
    - tests/hardware/test_backlight.py
  modified: []

key-decisions:
  - "No hardcoded sysfs path in production code — SYSFS_GLOB constant + pathlib glob at init time"
  - "persist=False default (cmd=0) — never saves to firmware unless caller explicitly opts in"
  - "strobe mode (3) included despite open hardware question — hardware verification deferred to Phase 1 live test"
  - "unittest.TestCase used (no pytest dependency) — tests runnable with stdlib only"

patterns-established:
  - "Pattern: BacklightController(sysfs_path=injected) for hardware-free unit testing of sysfs writers"
  - "Pattern: PermissionError wrapping in apply() surfaces actionable udev install instructions"

requirements-completed: [PERM-02, CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 1 Plan 02: BacklightController Implementation Summary

**BacklightController writes validated "{cmd} {mode_int} {r} {g} {b} {speed}\n" payloads to the asus::kbd_backlight sysfs attribute via pathlib glob discovery, with 14 hardware-free unit tests covering all modes, persist flag, and error paths**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T18:14:49Z
- **Completed:** 2026-02-21T18:16:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- BacklightController discovers the sysfs path via `pathlib.Path.glob("asus::kbd_backlight*/kbd_rgb_mode")` at init — no hardcoded paths in production code
- apply() validates mode/RGB(0-255)/speed(0/1/2) with descriptive ValueError messages; PermissionError wrapped with udev install instructions
- persist=False default (cmd=0) confirmed — live preview by default, explicit persist=True required to save to firmware
- 14-test unittest suite passes with stdlib only (no pytest dependency); all tests hardware-free via temp-file injection

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement BacklightController** - `d589f7a` (feat)
2. **Task 2: Implement unit test suite** - `113cc61` (test)

**Plan metadata:** (see final docs commit)

## Files Created/Modified
- `kbd_backlight/hardware/backlight.py` — BacklightController, HardwareNotFoundError, MODES, SYSFS_GLOB (100 lines)
- `tests/hardware/test_backlight.py` — 14 unit tests across 4 TestCase classes (145 lines)

## Decisions Made
- No hardcoded sysfs path in production code — SYSFS_GLOB constant, pathlib glob at init time. Matches the research-confirmed working path pattern.
- persist=False is the default (cmd=0) — callers must opt in to firmware save (persist=True). Prevents accidental writes to firmware storage on every preview call.
- strobe mode (3) included as planned — hardware behavior on this specific unit is an open question from research; hardware test deferred to Phase 1 live verification.
- unittest.TestCase used throughout instead of requiring pytest — all 14 tests runnable with `python3 -m unittest` using stdlib only.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. BacklightController works with mock sysfs paths in tests; udev rule from Plan 01 handles live hardware access.

## Next Phase Readiness
- BacklightController is the sole hardware write interface — all future phases (GTK window, tray, profiles) issue hardware writes through this class
- Import path confirmed: `from kbd_backlight.hardware.backlight import BacklightController, HardwareNotFoundError, MODES, SYSFS_GLOB`
- Payload format smoke-tested: `ctrl.apply("static", r=255, g=128, b=0, speed=1)` → `"0 0 255 128 0 1\n"` confirmed correct
- Live hardware test (with udev rule installed) deferred to Phase 1 final verification

## Self-Check: PASSED

Files confirmed present:
- kbd_backlight/hardware/backlight.py - FOUND
- tests/hardware/test_backlight.py - FOUND
- 01-02-SUMMARY.md - FOUND (this file)

Commits confirmed:
- d589f7a (Task 1: BacklightController) - FOUND
- 113cc61 (Task 2: unit test suite) - FOUND

---
*Phase: 01-permissions-and-hardware-foundation*
*Completed: 2026-02-21*

---
phase: 03-main-window-and-live-preview
plan: 01
subsystem: ui
tags: [gtk4, libadwaita, adw, gi, python, application]

# Dependency graph
requires:
  - phase: 02-profile-data-layer
    provides: ProfileManager with get_last_profile(), save_profile(), get_all_profiles()
  - phase: 01-permissions-and-hardware-foundation
    provides: BacklightController with apply(), HardwareNotFoundError
provides:
  - kbd_backlight/ui/ package with Application class (Adw.Application subclass)
  - main.py entry point with main() callable
  - show_window() hook for Phase 4 tray integration
  - Lazy BacklightController init with user-visible HardwareNotFoundError dialog
  - Last-profile restoration on startup via _restore_last_profile()
affects:
  - 03-02-main-window (imports Application, creates MainWindow)
  - 04-system-tray (uses show_window() to restore from tray)

# Tech tracking
tech-stack:
  added: [gtk4, libadwaita (Adw.Application, Adw.AlertDialog, Adw.ApplicationWindow)]
  patterns:
    - Adw.Application subclass owns all shared state (controller + manager)
    - Lazy hardware init in _on_activate prevents import-time hardware errors
    - MainWindow imported inside _on_activate to prevent circular imports
    - persist=False (cmd=0) on startup restore — never persist at activate time

key-files:
  created:
    - kbd_backlight/ui/__init__.py
    - kbd_backlight/ui/application.py
    - main.py
  modified: []

key-decisions:
  - "Application_ID = io.github.hikami.KbdBacklight (reverse-DNS, GTK convention)"
  - "Controller init deferred to _on_activate so HardwareNotFoundError shows Adw.AlertDialog, not crash"
  - "get_last_profile() returns Profile|None not a name string — _restore_last_profile uses returned Profile directly"
  - "MainWindow imported inside _on_activate (not at module level) to prevent circular import"
  - "show_window() stub exists now for Phase 4 tray hook — does nothing until window is created"

patterns-established:
  - "Application-as-service-locator: window and tray access shared state via app._controller / app._manager"
  - "Lazy GTK widget creation in _on_activate, not __init__"

requirements-completed: [WIND-01, WIND-02]

# Metrics
duration: 1min
completed: 2026-02-21
---

# Phase 3 Plan 01: GTK Application Scaffold Summary

**Adw.Application subclass wiring BacklightController, ProfileManager, and a show_window() tray hook into a minimal main.py entry point**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-21T22:03:06Z
- **Completed:** 2026-02-21T22:04:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created `kbd_backlight/ui/` package with `Application(Adw.Application)` owning shared hardware/profile state
- BacklightController initialized lazily in `_on_activate` with `Adw.AlertDialog` on `HardwareNotFoundError`
- `_restore_last_profile()` applies last-used profile with `persist=False` on every activate
- `show_window()` stub wired for Phase 4 tray integration
- `main.py` entry point at project root with `main()` callable for future packaging

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ui/ package and Application class** - `8176572` (feat)
2. **Task 2: Create main.py entry point** - `436af54` (feat)

**Plan metadata:** (docs commit pending)

## Files Created/Modified
- `kbd_backlight/ui/__init__.py` - GTK4/libadwaita package init, exports Application
- `kbd_backlight/ui/application.py` - Adw.Application subclass owning controller + manager
- `main.py` - Executable entry point with main() callable

## Decisions Made
- `APPLICATION_ID = "io.github.hikami.KbdBacklight"` — reverse-DNS following GTK convention
- Controller initialized lazily in `_on_activate` (not `__init__`) so HardwareNotFoundError surfaces with a dialog rather than a crash at import time
- `MainWindow` imported inside `_on_activate` to break potential circular import at module level
- `show_window()` stub created now even though Phase 4 needs it — avoids AttributeError if tray code runs early
- `_restore_last_profile()` uses `persist=False` (cmd=0) — never writes to firmware at startup

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _restore_last_profile() incorrect use of get_last_profile() return value**
- **Found during:** Task 1 (Create ui/ package and Application class)
- **Issue:** Plan code called `name = self._manager.get_last_profile()` then `profile = self._manager.get_profile(name)`, but `get_last_profile()` returns a `Profile | None` object, not a string name. Passing a Profile to `get_profile(name)` would cause a dict key lookup with a Profile object, returning None and silently skipping restore.
- **Fix:** Removed the intermediate `get_profile()` call; use the Profile returned directly from `get_last_profile()`.
- **Files modified:** `kbd_backlight/ui/application.py`
- **Verification:** Code logic verified against ProfileManager.get_last_profile() signature (returns Profile|None per manager.py line 156-162).
- **Committed in:** `8176572` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Fix essential for correct last-profile restore. No scope creep.

## Issues Encountered
None - plan executed cleanly after the get_last_profile() return type fix.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Application scaffold ready for Phase 3 Plan 02: MainWindow implementation
- `kbd_backlight.ui.application.Application` importable and instantiable
- `main.py` launches GTK application (hardware dialog on machines without ASUS hardware)
- `show_window()` stub ready for Phase 4 tray to call

---
*Phase: 03-main-window-and-live-preview*
*Completed: 2026-02-21*

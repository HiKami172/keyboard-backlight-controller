---
phase: 04-system-tray-and-autostart
plan: 02
subsystem: ui
tags: [gtk4, adw, gio, subprocess, ipc, tray, application]

# Dependency graph
requires:
  - phase: 04-01
    provides: tray.py GTK3 subprocess with AppIndicator3, stdin/stdout JSON IPC protocol
  - phase: 03-01
    provides: Application class with BacklightController, ProfileManager, show_window stub
  - phase: 03-02
    provides: MainWindow with _do_save, _on_delete_response, _refresh_profile_list, _load_profile_into_controls
provides:
  - Application._start_tray(): launches tray.py via Gio.SubprocessLauncher with piped stdin/stdout
  - Application._on_tray_message(): async IPC line reader dispatching select_profile/show/quit
  - Application._apply_profile_by_name(): applies named profile to hardware and syncs window UI
  - Application.notify_tray_refresh(): sends REFRESH to tray subprocess after profile mutations
  - Application._shutdown_tray(): gracefully terminates tray subprocess on quit
  - Application.hold()/release(): keeps app alive when window is hidden (TRAY-05)
  - MainWindow.load_profile_from_tray(): syncs UI controls from tray-selected profile
  - MainWindow notifies tray refresh after save and delete operations
affects: [04-03-autostart, testing]

# Tech tracking
tech-stack:
  added: [Gio.SubprocessLauncher, Gio.DataInputStream, GLib.PRIORITY_DEFAULT]
  patterns: [async-read-line-requeue, hold-release-lifecycle, tray-only-startup-flag]

key-files:
  created: []
  modified:
    - kbd_backlight/ui/application.py
    - kbd_backlight/ui/window.py

key-decisions:
  - "self.hold() called exactly once on first activate — prevents GLib main loop exit when window hides"
  - "_activated_once guard distinguishes first-run (apply tray-only logic) from re-activation (always show window)"
  - "_tray_only flag suppresses window on first activate only — re-activation ignores it"
  - "read_line_async requeued at end of _on_tray_message — caller must requeue or IPC stops after first message"
  - "release() called before quit() in quit action handler — balances the hold() from first activate"

patterns-established:
  - "Async IPC pattern: read_line_async with callback that requeues itself after handling message"
  - "Tray-only startup: --tray-only argv flag suppresses window presentation on first activate"
  - "_loading guard extended to load_profile_from_tray to prevent live preview on tray-driven profile switch"

requirements-completed: [TRAY-02, TRAY-05]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 4 Plan 02: Application Tray IPC Wiring Summary

**Gio.SubprocessLauncher async IPC wiring connects GTK4 Application to tray.py subprocess via stdin/stdout JSON protocol with app.hold() background persistence**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T19:02:05Z
- **Completed:** 2026-02-22T19:03:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Application now launches tray.py as a Gio.Subprocess on first activate with piped stdin/stdout
- Bidirectional IPC: async line reading dispatches select_profile/show/quit; outbound sends REFRESH/QUIT
- App persists as background process via self.hold() — window hiding no longer terminates the process
- MainWindow notifies tray of profile changes (save/delete) and syncs controls when tray selects a profile

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Application with tray subprocess launch and IPC** - `9967fa6` (feat)
2. **Task 2: Wire MainWindow profile save/delete to notify_tray_refresh + add load_profile_from_tray** - `b74476d` (feat)

## Files Created/Modified

- `kbd_backlight/ui/application.py` - Added _start_tray, _on_tray_message, _apply_profile_by_name, _send_tray, notify_tray_refresh, _shutdown_tray; hold/release lifecycle; _tray_only and _activated_once flags
- `kbd_backlight/ui/window.py` - Added notify_tray_refresh() calls after save and delete; added load_profile_from_tray() method

## Decisions Made

- `self.hold()` called exactly once on first activate to keep GLib main loop alive when window is hidden
- `_activated_once` guard distinguishes first-run (apply tray-only logic) from re-activation (always show window)
- `read_line_async` requeued at end of `_on_tray_message` — caller must requeue or IPC stops after first message
- `release()` called before `quit()` in quit action handler to balance the `hold()` from first activate

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Application IPC wiring complete — tray subprocess (04-01) and main app (04-02) are fully connected
- Ready for Phase 4 Plan 03 (autostart .desktop entry and packaging)
- No blockers

---
*Phase: 04-system-tray-and-autostart*
*Completed: 2026-02-22*

## Self-Check: PASSED

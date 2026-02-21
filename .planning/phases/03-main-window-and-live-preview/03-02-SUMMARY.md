---
phase: 03-main-window-and-live-preview
plan: "02"
subsystem: ui
tags: [gtk4, libadwaita, python, gi, debounce, glib, profiles]

# Dependency graph
requires:
  - phase: 03-01
    provides: Application class, ui/ package scaffold, BacklightController + ProfileManager wiring
  - phase: 02-02
    provides: ProfileManager (save/delete/list/get_last_profile)
  - phase: 01-02
    provides: BacklightController.apply(mode, r, g, b, speed, persist)
provides:
  - MainWindow(Adw.ApplicationWindow) with full backlight + profile UI
  - 100ms debounced live preview via GLib.timeout_add
  - Profile load/save/delete dialogs with Adw.Dialog, Adw.AlertDialog
  - do_close_request() hide-not-destroy behavior for Phase 4 tray
affects: [04-tray-icon, 05-hotkeys]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_loading guard: set True before programmatic UI updates to suppress signal-driven side effects"
    - "GLib debounce: cancel-and-reschedule pattern via GLib.source_remove + GLib.timeout_add"
    - "GLib.SOURCE_REMOVE: always return from timeout callbacks to prevent repeated firing"
    - "persist=False for live preview, persist=True only on explicit user action (save/load)"
    - "round() not int() for RGBA float-to-int conversion (precision)"

key-files:
  created:
    - kbd_backlight/ui/window.py
  modified:
    - kbd_backlight/ui/__init__.py

key-decisions:
  - "Adw.ComboRow for mode selector, not Gtk.DropDown — matches libadwaita preferences pattern"
  - "Gtk.ColorDialogButton not Gtk.ColorButton — ColorButton deprecated in GTK 4.10"
  - "Adw.Dialog for save dialog, Adw.AlertDialog for delete confirmation — no Gtk.Dialog (deprecated)"
  - "Speed row set_sensitive(False) for Static mode — speed is irrelevant, hide complexity"
  - "_on_speed_changed guards if button.get_active() — toggled fires twice per click"

patterns-established:
  - "Loading guard: _loading=True/finally:_loading=False wraps all programmatic control updates"
  - "Debounce pattern: source_remove+timeout_add(100) for any rapid hardware write"

requirements-completed: [WIND-01]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 3 Plan 02: MainWindow Summary

**Full GTK4/libadwaita config window with 100ms debounced live preview, mode/color/speed controls, and profile load/save/delete dialogs wired to BacklightController and ProfileManager**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T22:07:27Z
- **Completed:** 2026-02-21T22:09:20Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- `MainWindow(Adw.ApplicationWindow)` — 354 lines, full backlight control UI
- Mode selector (Adw.ComboRow), color picker (Gtk.ColorDialogButton), speed buttons (linked ToggleButton group)
- 100ms debounced live preview: GLib.timeout_add with _loading guard and SOURCE_REMOVE
- Profile management: dropdown, save dialog (Adw.Dialog+EntryRow), delete confirmation (Adw.AlertDialog)
- `do_close_request()` hides window rather than destroying — Phase 4 tray hook ready
- All 72 existing tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: MainWindow skeleton — all controls + debounce** - `1ea91c1` (feat)

## Files Created/Modified
- `kbd_backlight/ui/window.py` - MainWindow class: mode/color/speed controls, 100ms debounce, profile CRUD dialogs (354 lines)
- `kbd_backlight/ui/__init__.py` - Added MainWindow to package exports

## Decisions Made
- `Gtk.ColorDialogButton` not `Gtk.ColorButton` — ColorButton is deprecated in GTK 4.10
- `Adw.Dialog` + `Adw.EntryRow` for save dialog (not Gtk.Dialog, deprecated)
- `Adw.AlertDialog` for delete confirmation (destructive response appearance)
- Speed row `set_sensitive(False)` for Static mode — speed parameter irrelevant for static
- `_on_speed_changed` guards `if button.get_active()` — GTK toggled fires twice per click (deactivate + activate)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- MainWindow is complete and wired; Application._on_activate already imports and instantiates it
- Phase 4 (tray icon): `do_close_request()` + `Application.show_window()` stub already in place
- Phase 5 (hotkeys): no blocking issues

---
*Phase: 03-main-window-and-live-preview*
*Completed: 2026-02-21*

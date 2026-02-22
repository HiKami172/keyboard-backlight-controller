---
phase: 04-system-tray-and-autostart
plan: 01
subsystem: ui
tags: [gtk3, ayatana-appindicator3, tray, subprocess, gdkpixbuf, glib, ipc]

# Dependency graph
requires:
  - phase: 02-profile-data-layer
    provides: ProfileManager.get_all_profiles() used to build tray menu items
provides:
  - GTK3 tray subprocess script (kbd_backlight/ui/tray.py) with AyatanaAppIndicator3
  - Profile menu with 16x16 GdkPixbuf color swatches (sorted alphabetically)
  - JSON stdout IPC for select_profile / show / quit actions
  - stdin watcher via GLib.io_add_watch for REFRESH and QUIT commands
affects: [04-02-application-tray-integration, 04-03-autostart]

# Tech tracking
tech-stack:
  added: [AyatanaAppIndicator3 0.1, GTK 3.0 (subprocess only), GdkPixbuf 2.0, GLib.io_add_watch]
  patterns:
    - GTK3 subprocess isolation — AyatanaAppIndicator3 must run in a separate process from GTK4
    - JSON stdin/stdout IPC between GTK4 parent and GTK3 subprocess
    - GdkPixbuf.fill() RGBA packing formula for solid-color swatches
    - menu.show_all() before indicator.set_menu() is AppIndicator spec requirement

key-files:
  created: [kbd_backlight/ui/tray.py]
  modified: []

key-decisions:
  - "TrayProcess stores self._menu reference to prevent GLib garbage collection of the Gtk.Menu"
  - "Gray swatch (128,128,128) for color_cycle profiles where r=g=b=0 — otherwise swatch is invisible black"
  - "_on_stdin returns True to keep GLib.io_add_watch active; returns False only on QUIT to deregister"
  - "flush=True on all print() calls mandatory for pipe IPC — without it parent never receives messages"
  - "menu.show_all() called before indicator.set_menu() per AyatanaAppIndicator3 spec"

patterns-established:
  - "GTK3/GTK4 subprocess isolation: gi.require_version('AyatanaAppIndicator3') and GTK3 imports ONLY in tray.py"
  - "RGBA packing: packed = (r << 24) | (g << 16) | (b << 8) | 0xFF for GdkPixbuf.fill()"
  - "GLib.io_add_watch stdin watcher: returns True to keep active, False to deregister"

requirements-completed: [TRAY-01, TRAY-02, TRAY-03]

# Metrics
duration: 5min
completed: 2026-02-22
---

# Phase 4 Plan 01: GTK3 Tray Subprocess Summary

**AyatanaAppIndicator3 GTK3 subprocess with profile menu, GdkPixbuf color swatches, and JSON stdin/stdout IPC**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-22T19:02:03Z
- **Completed:** 2026-02-22T19:07:00Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments

- Created standalone GTK3 subprocess script that cannot coexist with GTK4 in same process
- AyatanaAppIndicator3 indicator with HARDWARE category shows in GNOME top panel (requires ubuntu-appindicators extension enabled)
- Profile menu built from sorted ProfileManager.get_all_profiles() with 16x16 GdkPixbuf solid-color swatches
- Gray swatch (128, 128, 128) for color_cycle profiles where r=g=b=0
- GLib.io_add_watch stdin watcher handles REFRESH (rebuilds menu) and QUIT (exits Gtk.main())
- JSON actions sent to stdout with flush=True: select_profile, show, quit

## Task Commits

Each task was committed atomically:

1. **Task 1: Create kbd_backlight/ui/tray.py — GTK3 tray subprocess** - `6aec605` (feat)

## Files Created/Modified

- `kbd_backlight/ui/tray.py` - GTK3 AyatanaAppIndicator3 tray subprocess; 166 lines; complete self-contained script

## Decisions Made

- Stored `self._menu` as instance variable to prevent GLib garbage collection of the Gtk.Menu before GTK processes it
- Used gray swatch (128,128,128) for color_cycle profiles (r=g=b=0) — showing black swatch would be invisible against dark tray backgrounds
- `_on_stdin` returns `False` only on QUIT (deregisters GLib watch); returns `True` for all other commands to keep watching
- All `print()` calls use `flush=True` — mandatory for pipe IPC so parent receives messages immediately without buffer delay
- `menu.show_all()` placed before `indicator.set_menu(menu)` per AyatanaAppIndicator3 specification (indicator won't render without this order)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None for this plan. Note: The ubuntu-appindicators GNOME Shell extension must be enabled once by the user:
```
gnome-extensions enable ubuntu-appindicators@ubuntu.com
```
This is documented as a known Phase 4 requirement from research.

## Next Phase Readiness

- `kbd_backlight/ui/tray.py` is ready to be launched as a subprocess from `application.py`
- Plan 04-02 will add `_start_tray()`, `_on_tray_line()`, `_send_tray()`, and `Application.hold()` to `application.py`
- Plan 04-02 will also wire tray REFRESH calls from `window.py` on profile save/delete

---
*Phase: 04-system-tray-and-autostart*
*Completed: 2026-02-22*

## Self-Check: PASSED

- FOUND: kbd_backlight/ui/tray.py
- FOUND: 04-01-SUMMARY.md
- FOUND commit: 6aec605

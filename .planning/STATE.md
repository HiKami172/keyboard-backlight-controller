# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** User can visually configure and switch keyboard backlight modes without touching the terminal — and the setting persists across reboots.
**Current focus:** Phase 3 — Main Window and Live Preview

## Current Position

Phase: 3 of 5 (Main Window and Live Preview)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-02-21 — Plan 03-02 complete: MainWindow with mode/color/speed controls, 100ms debounce, profile dialogs

Progress: [█████░░░░░] 36%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 1.5 min
- Total execution time: 9 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-permissions-and-hardware-foundation | 2 | 3 min | 2 min |
| 02-profile-data-layer | 2 | 3 min | 1.5 min |
| 03-main-window-and-live-preview | 2 | 3 min | 1.5 min |

**Recent Trend:**
- Last 5 plans: 1 min, 2 min, 1 min, 1 min, 2 min
- Trend: stable

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
- [02-01]: ProfileError subclasses ValueError so callers can catch either type
- [02-01]: VALID_MODES as ClassVar[set[str]] on @dataclass — Python stdlib excludes ClassVar from asdict() automatically
- [02-01]: Intentional validation duplication vs BacklightController — Profile must be hardware-independent
- [02-01]: ProfileManager NOT imported in __init__.py in Plan 01 — deferred to Plan 02 to avoid forward-ref errors
- [Phase 02-02]: Atomic write via tmp.replace(profiles_path) — prevents partial-write corruption on process kill
- [Phase 02-02]: _load() never caches (no self._data) — reads disk on every call to prevent stale state with multiple instances
- [Phase 02-02]: _dict_to_profile() silently filters unknown JSON keys via dataclasses.fields() — hand-edited profiles.json cannot crash
- [Phase 02-02]: get_all_profiles() added as single-_load() convenience for Phase 3/4 bulk profile iteration
- [03-01]: APPLICATION_ID = io.github.hikami.KbdBacklight (reverse-DNS, GTK convention)
- [03-01]: Controller init deferred to _on_activate — HardwareNotFoundError shows Adw.AlertDialog not a crash
- [03-01]: get_last_profile() returns Profile|None not string — _restore_last_profile uses returned Profile directly
- [03-01]: MainWindow imported inside _on_activate to prevent circular import at module level
- [03-01]: show_window() stub created now for Phase 4 tray hook — avoids AttributeError if tray calls early
- [03-02]: Gtk.ColorDialogButton not Gtk.ColorButton — ColorButton deprecated in GTK 4.10
- [03-02]: Adw.Dialog+EntryRow for save dialog; Adw.AlertDialog for delete confirmation — Gtk.Dialog deprecated
- [03-02]: Speed row set_sensitive(False) for Static mode — speed param irrelevant for static
- [03-02]: _on_speed_changed guards if button.get_active() — toggled fires twice per click (deactivate + activate)
- [03-02]: _loading guard pattern wraps all programmatic control updates to suppress signal-driven debounce

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 4]: GNOME Shell requires `gnome-shell-extension-appindicator` for tray icons — must detect and surface user-facing error if missing
- [Phase 4]: Confirm trayer vs. direct AppIndicator3 GObject introspection binding during Phase 4 planning
- [Phase 5]: Wayland global hotkeys (KEYS-01, KEYS-02) — XDG Desktop Portal Global Shortcuts API not fully researched; may hit implementation constraints

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 03-02-PLAN.md — MainWindow with mode/color/speed controls, 100ms debounce, profile load/save/delete dialogs.
Resume file: None

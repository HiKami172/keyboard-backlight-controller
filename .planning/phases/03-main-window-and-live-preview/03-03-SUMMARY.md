---
phase: 03-main-window-and-live-preview
plan: 03
subsystem: ui
tags: [gtk4, libadwaita, color-picker, presets, live-preview]

# Dependency graph
requires:
  - phase: 03-02
    provides: MainWindow with mode/color/speed controls and profile dialogs
provides:
  - 8-preset color palette section (Ocean, Sunset, Cyberpunk, Crimson, Gold, Lilac, Glacier, Monochrome)
  - Color Cycle mode UX: color row insensitive with hardware-explains subtitle
  - ColorDialogButton with reliable visibility via size_request(40,40)
affects: [04-tray-icon, 05-hotkeys]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FlowBox with NONE selection mode for palette grids"
    - "Per-button CssProvider for individual swatch colors"
    - "Mode-driven row sensitivity: _on_mode_changed updates both speed_row and color_row"

key-files:
  created: []
  modified:
    - kbd_backlight/ui/window.py

key-decisions:
  - "color_cycle mode disables color picker — ASUS hardware ignores RGB values and cycles all colors via firmware; no per-color control exists in the sysfs interface"
  - "Adw.ActionRow.set_subtitle() used to explain Color Cycle limitation inline rather than a separate info label"
  - "set_size_request(40,40) on ColorDialogButton ensures reliable rendering — without explicit sizing the button could appear missing"
  - "self._color_row stored as instance variable (not local) to allow mode-change handler to update sensitivity"
  - "App cannot be reopened after closing window — expected Phase 3 limitation; Phase 4 tray icon will add show_window() call"

patterns-established:
  - "Mode sensitivity pattern: _on_mode_changed checks mode string and updates all mode-dependent rows"
  - "Subtitle-as-explanation: use Adw.ActionRow.set_subtitle() to clarify hardware limitations inline"

requirements-completed: [COLR-01]

# Metrics
duration: ~20min
completed: 2026-02-22
---

# Phase 3 Plan 03: Color Palette Presets and Full Window Verification Summary

**8-color preset palette with FlowBox swatches, Color Cycle mode hardware explanation, and ColorDialogButton visibility fix completing Phase 3 MainWindow**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-02-22
- **Completed:** 2026-02-22
- **Tasks:** 2 (1 code task + 1 checkpoint with bug fixes)
- **Files modified:** 1

## Accomplishments

- Added 8 named color swatch presets (Ocean, Sunset, Cyberpunk, Crimson, Gold, Lilac, Glacier, Monochrome) in a FlowBox palette section below Profiles
- Fixed ColorDialogButton visibility: stored color_row as instance variable, added set_size_request(40, 40) for reliable rendering
- Implemented correct Color Cycle mode UX: color picker row becomes insensitive with subtitle "Hardware cycles all colors automatically" — matches actual sysfs behavior (r/g/b values are ignored in mode 2)
- All 72 unit/integration tests pass after changes

## Task Commits

1. **Task 1: Add color palette presets section to MainWindow** - `87c9be8` (feat)
2. **Fix: color picker visibility and Color Cycle mode UX** - `bb7874b` (fix)

**Plan metadata:** (docs commit — to follow)

## Files Created/Modified

- `/home/hikami/Documents/projects/keyboard-backlights-control/kbd_backlight/ui/window.py` — Added PRESETS constant, _build_palette(), _on_preset_clicked(), fixed color row visibility, Color Cycle mode disables color row with subtitle

## Decisions Made

- **Color Cycle uses hardware firmware cycling:** The sysfs payload format is `{cmd} {mode} {r} {g} {b} {speed}`. For mode=2 (color_cycle), the ASUS firmware ignores the r/g/b values and cycles through all colors automatically. There is no mechanism to specify custom colors for the cycle sequence. Therefore the correct UX is to disable the color picker row and explain this inline.
- **set_size_request(40, 40) on ColorDialogButton:** Without an explicit size request, GTK4's ColorDialogButton can render as zero-size or near-invisible, particularly in Adw.ActionRow suffix position. Explicit sizing ensures reliable display.
- **self._color_row as instance variable:** The color row must be stored on self (not as a local variable) so _on_mode_changed can update its sensitivity and subtitle dynamically.

## Deviations from Plan

### Auto-fixed Issues (found during user verification checkpoint)

**1. [Rule 1 - Bug] ColorDialogButton not reliably visible**
- **Found during:** Checkpoint: Visual verification on real hardware
- **Issue:** Gtk.ColorDialogButton added as suffix to color_row, but row stored as local variable only and button had no explicit size request. Button rendered as missing/invisible.
- **Fix:** Stored color_row as `self._color_row` (instance variable), added `self._color_button.set_size_request(40, 40)`
- **Files modified:** kbd_backlight/ui/window.py
- **Verification:** Button visible after fix; 72 tests still pass
- **Committed in:** bb7874b

**2. [Rule 2 - Missing Critical] Color Cycle mode had no UX indication of hardware limitation**
- **Found during:** Checkpoint: Visual verification on real hardware
- **Issue:** Color Cycle mode appeared to accept color values but the hardware ignores them entirely. User could change the color picker thinking it would affect the cycle, but it has no effect. No explanation existed.
- **Fix:** _on_mode_changed now disables color_row when mode == 'color_cycle' and sets subtitle "Hardware cycles all colors automatically". Subtitle cleared when switching to other modes.
- **Files modified:** kbd_backlight/ui/window.py
- **Verification:** Switching to Color Cycle greys out color row; switching back re-enables it
- **Committed in:** bb7874b

---

**Total deviations:** 2 auto-fixed (1 visibility bug, 1 missing hardware-limitation UX)
**Impact on plan:** Both fixes necessary for correctness and usability. No scope creep.

## Known Phase 3 Limitations

- **App cannot be reopened after closing the window** — This is expected behavior for Phase 3. The window's `do_close_request` hides the window (preventing destroy), but there is no mechanism to re-show it without a tray icon. Phase 4 will add the AppIndicator3 tray icon with a "Show Window" menu item that calls `Application.show_window()`. The `show_window()` stub is already present from Plan 03-01.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 3 is complete: all window controls functional end-to-end on real hardware
- Phase 4 (tray icon) can begin: `Application.show_window()` stub exists at `kbd_backlight/ui/application.py`
- Phase 4 prerequisite: validate `gi.repository.AppIndicator3` import on Ubuntu 24.04 (documented blocker in STATE.md)

---
*Phase: 03-main-window-and-live-preview*
*Completed: 2026-02-22*

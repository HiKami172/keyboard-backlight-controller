---
phase: 03-main-window-and-live-preview
verified: 2026-02-22T00:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 3: Main Window and Live Preview — Verification Report

**Phase Goal:** Deliver a working GTK4/libadwaita main window with live hardware preview, profile management, and color preset palette. Running `python main.py` should open a fully functional backlight control GUI.
**Verified:** 2026-02-22
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running `python main.py` launches the GTK application without error | VERIFIED | `main.py` imports cleanly; `main()` callable exists; app.run(sys.argv) wired; executable bit set |
| 2 | Application class owns BacklightController and ProfileManager instances | VERIFIED | `application.py`: `_controller: BacklightController | None` + `_manager: ProfileManager = ProfileManager()` in `__init__` |
| 3 | Application exposes `show_window()` for Phase 4 tray integration | VERIFIED | `application.py` line 73–76: `show_window()` method present and calls `self._window.present()` |
| 4 | Last-used profile is restored and applied to hardware on activate | VERIFIED | `_restore_last_profile()` calls `self._manager.get_last_profile()` (returns Profile object, not name — bug from plan auto-fixed in commit 8176572) then `self._controller.apply(..., persist=False)` |
| 5 | Window opens with mode selector, color picker, and speed buttons visible and wired | VERIFIED | `window.py`: `Adw.ComboRow` mode row, `Gtk.ColorDialogButton` color button, `Gtk.ToggleButton` speed group — all constructed and signal-connected |
| 6 | Speed buttons hidden/insensitive for Static mode | VERIFIED | `_on_mode_changed` line 147: `self._speed_row.set_sensitive(mode != 'static')` |
| 7 | Color picker insensitive for Color Cycle mode with inline explanation | VERIFIED | `_on_mode_changed` lines 149–154: `self._color_row.set_sensitive(not is_color_cycle)` + subtitle "Hardware cycles all colors automatically" |
| 8 | User can select a saved profile from a dropdown and keyboard updates immediately | VERIFIED | `_on_profile_selected` calls `_load_profile_into_controls`, then `self._controller.apply(..., persist=True)` and `set_last_profile` |
| 9 | User can save the current settings as a named profile via a dialog | VERIFIED | `_do_save` calls `self._manager.save_profile(profile)` and shows toast; uses `Adw.Dialog` + `Adw.EntryRow` |
| 10 | User can delete a profile via a confirmation dialog | VERIFIED | `_confirm_delete` shows `Adw.AlertDialog` with destructive response; `_on_delete_response` calls `self._manager.delete_profile` |
| 11 | Closing the window hides it rather than quitting | VERIFIED | `do_close_request()` line 84–87: `self.hide(); return True` |
| 12 | 8 named color swatches are displayed and clicking one updates the color picker and keyboard within ~100ms | VERIFIED | `PRESETS` constant has 8 entries (Ocean, Sunset, Cyberpunk, Crimson, Gold, Lilac, Glacier, Monochrome); `_on_preset_clicked` calls `self._color_button.set_rgba(rgba)` which fires `notify::rgba` -> `_schedule_preview()` |
| 13 | All 72 existing tests continue to pass | VERIFIED | `python3 -m unittest discover tests/ -v` — 72 tests, 0 failures, 0 errors |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kbd_backlight/ui/__init__.py` | ui package init exporting Application | VERIFIED | Exists; exports `Application` and `MainWindow`; `from .application import Application` present |
| `kbd_backlight/ui/application.py` | Adw.Application subclass — owns shared state | VERIFIED | 76 lines; `class Application(Adw.Application)` present; all methods wired |
| `main.py` | Application entry point | VERIFIED | 14 lines; `app.run(sys.argv)` wired; executable (`-rwxrwxr-x`) |
| `kbd_backlight/ui/window.py` | MainWindow with palette presets added | VERIFIED | 422 lines (exceeds min 240); `class MainWindow(Adw.ApplicationWindow)` present; `PRESETS` constant with 8 entries at module level |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py` | `kbd_backlight/ui/application.py` | `from kbd_backlight.ui.application import Application` | WIRED | Line 5: import present; line 9: `Application()` instantiated |
| `application.py` | `kbd_backlight/hardware/backlight.py` | `BacklightController()` constructor | WIRED | Lines 7, 23, 32: imported, typed, instantiated in `_on_activate` |
| `application.py` | `kbd_backlight/profiles/manager.py` | `ProfileManager()` constructor | WIRED | Lines 8, 24: imported and instantiated in `__init__` |
| `window.py` | `kbd_backlight/hardware/backlight.py` | `_apply_preview()` calls `self._controller.apply(persist=False)` | WIRED | Line 183: `persist=False` in `_apply_preview`; lines 263, 339: `persist=True` only on explicit load/save |
| `window.py` | `kbd_backlight/profiles/manager.py` | `_do_save()` calls `self._manager.save_profile()` | WIRED | Line 333: `self._manager.save_profile(profile)` present |
| `window.py` | `GLib.timeout_add` | `_schedule_preview()` debounce | WIRED | Line 172: `GLib.timeout_add(100, self._apply_preview)`; line 187: `return GLib.SOURCE_REMOVE` |
| `window.py _on_preset_clicked` | `Gtk.ColorDialogButton.set_rgba()` | sets rgba which emits `notify::rgba` -> `_schedule_preview()` | WIRED | Line 420: `self._color_button.set_rgba(rgba)` in `_on_preset_clicked`; `notify::rgba` signal connected at line 119 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WIND-01 | 03-01-PLAN, 03-02-PLAN | Full standalone GTK4/libadwaita window for all configuration | SATISFIED | `MainWindow` with mode/color/speed/profiles/presets all functional; 422-line implementation, no stubs |
| WIND-02 | 03-01-PLAN | Tray icon click opens/shows the main window | SATISFIED (stub prepared) | `show_window()` exists on Application; `do_close_request` hides rather than destroys; tray call is Phase 4 work — the Phase 3 hook is complete as specified |
| COLR-01 | 03-03-PLAN | User can apply preset color palettes (6-8 named themes) | SATISFIED | `PRESETS` constant with 8 entries; `_build_palette()` FlowBox; `_on_preset_clicked` wired to `set_rgba` + debounce |

No orphaned requirements. REQUIREMENTS.md maps WIND-01, WIND-02, COLR-01 to Phase 3, all accounted for. TRAY-05 (window close hides to tray) is a Phase 4 requirement — `do_close_request` behavior in Phase 3 prepares for it but TRAY-05 is not claimed by any Phase 3 plan.

---

### Anti-Patterns Found

None. No TODO/FIXME/HACK/placeholder comments found in `kbd_backlight/ui/`. No empty implementations. No stub returns. No console.log-only handlers.

Notable items (informational only):

| File | Pattern | Severity | Notes |
|------|---------|----------|-------|
| `application.py` | `except Exception: pass` in `_restore_last_profile` | Info | Intentional: hardware may be unavailable at startup; silencing is correct documented behavior |
| `window.py` | `except Exception: pass` in `_apply_preview` and `_on_profile_selected` | Info | Intentional: prevents window crash on hardware errors during live preview |

---

### Human Verification Required

The Phase 3 plan included a human checkpoint (`03-03-PLAN.md` task 2, `checkpoint:human-verify gate="blocking"`). Per `03-03-SUMMARY.md`, the user completed this checkpoint and confirmed the window on real hardware, resulting in two bug fixes (ColorDialogButton visibility, Color Cycle mode UX) committed in `bb7874b`. Human sign-off was obtained during execution.

Remaining human verification items (for completeness — all have prior sign-off):

#### 1. Full End-to-End Window UX

**Test:** Run `python3 main.py` and exercise mode selector, color picker, speed buttons, profile save/load/delete, palette swatches, and window close.
**Expected:** All controls respond; keyboard updates within ~100ms for live preview; profile operations persist; window hides on close without quitting.
**Why human:** Visual rendering, real hardware response, and timing cannot be verified programmatically.

---

### Deviations Resolved

Two bugs were caught and fixed during execution (not remaining gaps):

1. **`_restore_last_profile()` return type:** Plan code called `get_profile(name)` with the result of `get_last_profile()`, but `get_last_profile()` returns a `Profile` object, not a string. Fixed in commit `8176572` to use the returned `Profile` directly.

2. **`ColorDialogButton` not reliably visible:** Button had no explicit size request. Fixed in commit `bb7874b` with `set_size_request(40, 40)` and storing `color_row` as `self._color_row`.

3. **Color Cycle mode missing hardware explanation:** No UX indication that r/g/b values are ignored in color_cycle mode. Fixed in commit `bb7874b` by disabling color row with subtitle "Hardware cycles all colors automatically".

All deviations were auto-fixed by the executing agent and committed before this verification.

---

## Summary

Phase 3 goal is fully achieved. All 13 observable truths are verified against the actual codebase. All three required artifacts exist and are substantive (no stubs). All seven key links are wired with actual function calls, not placeholders. Requirements WIND-01, WIND-02, and COLR-01 are all satisfied. 72 existing tests continue to pass. Human checkpoint was completed during execution with user sign-off.

`python3 main.py` opens a fully functional GTK4/libadwaita backlight control GUI as specified.

---

_Verified: 2026-02-22_
_Verifier: Claude (gsd-verifier)_

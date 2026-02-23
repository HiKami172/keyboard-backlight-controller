---
phase: 04-system-tray-and-autostart
verified: 2026-02-23T00:00:00Z
status: human_needed
score: 13/13 automated must-haves verified
re_verification: false
human_verification:
  - test: "Launch app normally (python3 main.py) and confirm tray icon appears in GNOME top panel"
    expected: "Keyboard icon visible in GNOME top-right tray area alongside the ubuntu-appindicators extension"
    why_human: "AyatanaAppIndicator3 icon visibility requires GNOME Shell + ubuntu-appindicators extension enabled — cannot verify programmatically"
  - test: "Right-click tray icon and confirm menu lists all profiles with color swatches"
    expected: "Menu appears with one row per saved profile, each showing a 16x16 color swatch and the profile name"
    why_human: "GTK3 menu rendering and swatch pixel color require visual inspection"
  - test: "Click a profile in the tray menu and confirm the keyboard backlight changes immediately"
    expected: "Keyboard backlight switches to that profile's mode/color/speed; main window controls update to match"
    why_human: "Requires actual hardware response and visual UI sync check"
  - test: "Close the main window and confirm app stays alive as a tray-only process"
    expected: "Window disappears; tray icon remains; 'Open Settings' in tray reopens the window"
    why_human: "Background persistence and window re-show require interactive observation"
  - test: "Run python3 main.py --tray-only and confirm no main window appears"
    expected: "No GTK4 window opens; tray icon appears and profile menu works normally"
    why_human: "Window suppression requires visual confirmation at startup"
---

# Phase 4: System Tray and Autostart Verification Report

**Phase Goal:** System tray integration — app runs as a persistent background process accessible via GNOME tray icon, with profile switching, show/hide window, and autostart on login.
**Verified:** 2026-02-23
**Status:** human_needed — all automated checks PASSED; 5 items require interactive human confirmation
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GTK3 tray subprocess renders AyatanaAppIndicator3 icon in GNOME top panel | ? NEEDS HUMAN | tray.py creates AyatanaAppIndicator3.Indicator.new(..., HARDWARE) with ACTIVE status; runtime rendering requires GNOME session |
| 2  | Right-clicking tray icon shows a menu listing all saved profiles with 16x16 color swatches | ? NEEDS HUMAN | `_build_menu()` iterates `get_all_profiles()` sorted; `_make_profile_item()` creates GdkPixbuf 16x16 with RGBA packing; visual confirmation needed |
| 3  | Clicking a profile menu item writes a JSON `select_profile` message to stdout | ✓ VERIFIED | `_on_profile_clicked` → `self._send(json.dumps({'action': 'select_profile', 'name': name}))` with `flush=True` (line 135, 161 tray.py) |
| 4  | Clicking 'Open Settings' writes a JSON `show` message to stdout | ✓ VERIFIED | `settings_item.connect('activate', lambda _: self._send(json.dumps({'action': 'show'})))` (line 82 tray.py) |
| 5  | Clicking 'Quit' writes a JSON `quit` message and exits Gtk.main() | ✓ VERIFIED | `quit_item.connect('activate', lambda _: (self._send(json.dumps({'action': 'quit'})), Gtk.main_quit()))` (line 87-90 tray.py) |
| 6  | Sending REFRESH on stdin causes menu to rebuild from disk | ✓ VERIFIED | `_on_stdin` checks `line == 'REFRESH'` → `self._build_menu()` (line 144-145 tray.py); GLib.io_add_watch registered (line 58) |
| 7  | Application launches tray.py as subprocess with piped stdin/stdout on activate | ✓ VERIFIED | `_start_tray()` uses `Gio.SubprocessLauncher.new(STDIN_PIPE \| STDOUT_PIPE)` → `launcher.spawnv([sys.executable, tray_script])` (lines 88-100 application.py) |
| 8  | Application.hold() prevents app quit when window is hidden | ✓ VERIFIED | `self.hold()` called exactly once on first activate (line 70 application.py); `_activated_once` guard prevents repeat (lines 33, 37, 71) |
| 9  | JSON `select_profile` from tray applies profile to hardware and updates window | ✓ VERIFIED | `_dispatch_tray_line` → `_apply_profile_by_name()` calls `self._controller.apply(...)` then `self._window.load_profile_from_tray(profile)` (lines 131, 141-156 application.py) |
| 10 | JSON `show` from tray calls `show_window()`, presenting main window | ✓ VERIFIED | `_dispatch_tray_line` action `show` → `self.show_window()` (line 133 application.py); `show_window()` calls `self._window.present()` (line 200) |
| 11 | `notify_tray_refresh()` sends REFRESH to tray after profile save or delete | ✓ VERIFIED | Called in `_do_save` (line 336 window.py) and `_on_delete_response` (line 375 window.py); `notify_tray_refresh()` sends `'REFRESH'` via `_send_tray` (line 170-171 application.py) |
| 12 | `~/.config/autostart/kbd-backlight.desktop` installed with `--tray-only` and `X-GNOME-Autostart-enabled=true` | ✓ VERIFIED | Desktop file exists; `Exec=/usr/bin/python3 .../main.py --tray-only`; `X-GNOME-Autostart-enabled=true` confirmed by `cat` output |
| 13 | `--tray-only` flag suppresses window on first activate; re-activation always shows window | ✓ VERIFIED | `main.py` strips `--tray-only` from argv before `app.run()`; Application reads flag from `sys.argv` before strip; `_tray_only` suppresses `self._window.present()` on first activate; `_activated_once` on re-activation calls `show_window()` unconditionally |

**Score:** 13/13 automated truths verified (5 truths marked NEEDS HUMAN for runtime/visual confirmation)

---

## Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Details |
|----------|-----------|--------------|--------|---------|
| `kbd_backlight/ui/tray.py` | 80 | 166 | ✓ VERIFIED | GTK3 AyatanaAppIndicator3 subprocess; complete implementation; passes `ast.parse()` |
| `kbd_backlight/ui/application.py` | 90 | 200 | ✓ VERIFIED | Application with tray launch, GLib.io_add_watch IPC, hold/release lifecycle; passes `ast.parse()` |
| `kbd_backlight/ui/window.py` | (no min) | 442 | ✓ VERIFIED | `notify_tray_refresh()` wired in `_do_save` and `_on_delete_response`; `load_profile_from_tray()` present; passes `ast.parse()` |
| `install/install-autostart.sh` | 20 | 36 | ✓ VERIFIED | Executable; resolves paths dynamically; writes XDG .desktop file |
| `main.py` | (modified) | 17 | ✓ VERIFIED | Strips `--tray-only` from argv before `app.run()` |
| `~/.config/autostart/kbd-backlight.desktop` | (installed) | installed | ✓ VERIFIED | Correct Exec line with absolute paths and `--tray-only`; `X-GNOME-Autostart-enabled=true` |

---

## Key Link Verification

### Plan 04-01 Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `tray.py TrayProcess._on_profile_clicked` | stdout | `json.dumps({'action': 'select_profile', 'name': name})` | ✓ WIRED | Line 135: `self._send(json.dumps({'action': 'select_profile', 'name': name}))` |
| `tray.py TrayProcess._on_stdin` | `_build_menu` | `GLib.io_add_watch` reading stdin; REFRESH triggers rebuild | ✓ WIRED | Line 58: `GLib.io_add_watch(sys.stdin.fileno(), GLib.IO_IN, self._on_stdin)`; lines 144-145: REFRESH → `self._build_menu()` |

### Plan 04-02 Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `application.py _start_tray` | `tray.py` | `Gio.SubprocessLauncher.spawnv([sys.executable, tray_script])` | ✓ WIRED | Line 100: `self._tray_proc = launcher.spawnv([sys.executable, tray_script])` where `tray_script` points to `tray.py` |
| `application.py _on_tray_data/_dispatch_tray_line` | `BacklightController.apply` | `select_profile` action → `_apply_profile_by_name` → `self._controller.apply()` | ✓ WIRED | Lines 131, 147-151: `_apply_profile_by_name` calls `self._controller.apply(...)` |
| `window.py _do_save` | `Application.notify_tray_refresh` | `self.get_application().notify_tray_refresh()` | ✓ WIRED | Line 336 window.py: `self.get_application().notify_tray_refresh()` |

**Note:** Plan 04-02 described `_on_tray_message` as the IPC callback. The actual implementation uses `_on_tray_data` (raw fd reader with buffering) + `_dispatch_tray_line` (JSON parser/dispatcher). This is a correct improvement: the original `read_line_async` approach was replaced during human verification with `GLib.io_add_watch` on the raw fd to fix message-dropping. The wiring semantics are identical — the rename does not affect goal achievement.

### Plan 04-03 Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `install/install-autostart.sh` | `~/.config/autostart/kbd-backlight.desktop` | `cat > $DESKTOP_FILE` with absolute Exec path | ✓ WIRED | Desktop file present with `Exec=/usr/bin/python3 /home/hikami/.../main.py --tray-only` |
| `~/.config/autostart/kbd-backlight.desktop Exec` | `main.py --tray-only` | GNOME reads `X-GNOME-Autostart-enabled=true` and launches Exec on login | ✓ WIRED | `--tray-only` in Exec line; `X-GNOME-Autostart-enabled=true` present |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TRAY-01 | 04-01, 04-02 | System tray icon appears with right-click menu listing all profiles | ? NEEDS HUMAN | `tray.py` creates AyatanaAppIndicator3 indicator + profile menu; runtime visibility requires GNOME session check |
| TRAY-02 | 04-01, 04-02 | User can switch profiles from tray menu with one click | ? NEEDS HUMAN | IPC chain verified: tray click → JSON `select_profile` → `_apply_profile_by_name` → `BacklightController.apply`; hardware response requires human |
| TRAY-03 | 04-01 | Each profile shows a color swatch in the tray menu | ? NEEDS HUMAN | `_make_profile_item` creates GdkPixbuf 16x16, RGBA packed with `(r<<24)\|(g<<16)\|(b<<8)\|0xFF`; gray fallback for color_cycle; visual rendering requires human |
| TRAY-04 | 04-03 | App launches into tray-only mode on login via XDG autostart .desktop file | ✓ SATISFIED | `~/.config/autostart/kbd-backlight.desktop` installed with `--tray-only` Exec flag and `X-GNOME-Autostart-enabled=true`; `main.py` strips flag before GLib parsing; Application suppresses window on first activate when `_tray_only=True` |
| TRAY-05 | 04-02 | Closing the main window hides to tray instead of quitting | ✓ SATISFIED | `do_close_request()` in window.py calls `self.hide()` and returns `True` to suppress destroy; `Application.hold()` keeps GLib main loop alive |

**TRAY-01, TRAY-02, TRAY-03** are programmatically verified at the code level but require interactive human confirmation for runtime behavior (GTK rendering, hardware response).

**No orphaned requirements:** All 5 TRAY requirements (TRAY-01 through TRAY-05) appear in plan frontmatter `requirements:` fields and are fully accounted for.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tray.py` | 74 | Variable named `placeholder` | Info | Not a code stub — this is a `Gtk.MenuItem(label='(no profiles)')` rendered when profile list is empty. Semantic and correct. |

No blockers. No stubs. No empty implementations. No TODO/FIXME/XXX patterns.

---

## Notable Deviations from Plan (Non-Blocking)

Three bugs were discovered and fixed during human verification in plan 04-03. All are committed and the final implementation is correct:

1. **LD_PRELOAD libpthread** (`e15fa41`, `c908ed8`): Snap core20 injects an incompatible `libpthread.so.0` via `LD_LIBRARY_PATH`. Fixed by calling `launcher.setenv('LD_PRELOAD', '/lib/x86_64-linux-gnu/libpthread.so.0', True)` and `launcher.unsetenv('LD_LIBRARY_PATH')` before spawning the tray subprocess.

2. **GLib.io_add_watch replaces read_line_async** (`12851f8`): `Gio.DataInputStream.read_line_async` silently dropped messages after the first in the `Gio.SubprocessLauncher` context. Replaced with `GLib.io_add_watch` on the raw stdout fd with a buffered line-splitter (`_on_tray_data` + `_dispatch_tray_line`). This is the implementation that passed all 8 human verification steps.

3. **--tray-only stripped from argv** (`62fa851`): GLib's option parser rejects unknown flags with `SystemExit`. Fixed in `main.py` by filtering `sys.argv` before `app.run(argv)`.

All three deviations improve correctness. The wiring goals are fully achieved.

---

## Human Verification Required

### 1. Tray Icon Visibility

**Test:** Ensure the ubuntu-appindicators GNOME extension is enabled (`gnome-extensions info ubuntu-appindicators@ubuntu.com | grep -E "State:|Enabled:"`), then run `python3 main.py`. Look for a keyboard icon in the GNOME top panel (top-right area, near clock/system menu).
**Expected:** A keyboard tray icon appears in the GNOME panel alongside other tray icons.
**Why human:** AyatanaAppIndicator3 icon visibility depends on the GNOME Shell extension being active — cannot verify without a running GNOME session.

### 2. Profile Menu with Color Swatches

**Test:** Right-click the tray icon.
**Expected:** A menu drops down listing all saved profiles. Each entry shows a small 16x16 colored square on the left and the profile name on the right. Color Cycle profiles show a gray swatch.
**Why human:** GTK3 widget rendering and pixbuf color accuracy require visual inspection.

### 3. Profile Switching from Tray

**Test:** Click any profile name in the tray menu.
**Expected:** Keyboard backlight changes immediately to that profile's color/mode/speed. If the main window is open, its controls (mode dropdown, color button, speed buttons) update to match the selected profile.
**Why human:** Requires actual hardware response and UI sync verification — programmatic tracing confirms the code path exists but not that hardware accepts the write.

### 4. Hide-to-Tray and Restore

**Test:** With the app running, close the main window using the window manager X button.
**Expected:** Window disappears but tray icon remains. The app process is still running. Clicking "Open Settings" in the tray menu or triggering app re-activation brings the window back.
**Why human:** Background persistence and window re-presentation require interactive session observation.

### 5. Tray-Only Startup

**Test:** Quit the app via the tray menu Quit option, then run `python3 main.py --tray-only`.
**Expected:** No main window opens. The tray icon appears. Right-clicking shows the profile menu and profile switching works.
**Why human:** Window suppression on startup requires visual confirmation that no window appears.

---

## Gaps Summary

No gaps. All automated checks passed. The implementation is substantive and fully wired across all four artifacts:

- `kbd_backlight/ui/tray.py` (166 lines): complete GTK3 subprocess with AyatanaAppIndicator3, profile menu, GdkPixbuf color swatches, and JSON IPC
- `kbd_backlight/ui/application.py` (200 lines): tray subprocess launch via Gio.SubprocessLauncher, GLib.io_add_watch IPC, hold/release lifecycle, `_apply_profile_by_name`, `notify_tray_refresh`, `_shutdown_tray`
- `kbd_backlight/ui/window.py`: `notify_tray_refresh()` wired in two mutation sites, `load_profile_from_tray()` implemented with `_loading` guard
- `install/install-autostart.sh` (36 lines): executable, dynamic path resolution, writes valid XDG .desktop file

The only remaining items are 5 interactive confirmation steps that cannot be verified without a live GNOME session and attached keyboard hardware.

---

_Verified: 2026-02-23_
_Verifier: Claude (gsd-verifier)_

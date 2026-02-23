---
phase: 04-system-tray-and-autostart
plan: 03
subsystem: ui
tags: [autostart, xdg-desktop, gnome, tray, libpthread, gio, glib]

# Dependency graph
requires:
  - phase: 04-01
    provides: GTK3 tray subprocess (tray.py) with AyatanaAppIndicator3 and stdin IPC
  - phase: 04-02
    provides: Application tray wiring, Gio.SubprocessLauncher, app.hold(), bidirectional sync
provides:
  - XDG autostart install script (install/install-autostart.sh) with dynamic path resolution
  - ~/.config/autostart/kbd-backlight.desktop with --tray-only Exec line
  - Full Phase 4 end-to-end human verification (all 8 steps approved)
  - Fix: snap libpthread soname conflict resolved via LD_PRELOAD of system libpthread
  - Fix: GLib.io_add_watch IPC replaces broken read_line_async in application.py
  - Fix: --tray-only stripped from argv before GLib option parser in main.py
affects: [05-global-hotkeys]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "XDG autostart: write .desktop to ~/.config/autostart/ using resolved absolute paths from BASH_SOURCE[0]"
    - "LD_PRELOAD system libpthread before tray subprocess spawn prevents snap core20 soname mismatch"
    - "GLib.io_add_watch(stdin.fileno(), ...) for synchronous line-by-line IPC; read_line_async unreliable with SubprocessLauncher"
    - "Strip argv flags before GLib.Application.run() — GLib parses sys.argv directly and rejects unknown flags"

key-files:
  created:
    - install/install-autostart.sh
  modified:
    - main.py
    - kbd_backlight/ui/application.py

key-decisions:
  - "LD_PRELOAD=/lib/x86_64-linux-gnu/libpthread.so.0 injected into subprocess env before tray spawn — snap core20 ships soname-mismatched libpthread that crashes GTK3 imports"
  - "GLib.io_add_watch replaces Gio.DataInputStream.read_line_async for tray IPC — async variant silently dropped messages after first receive in SubprocessLauncher context"
  - "sys.argv[:] filtered to remove --tray-only before Gtk.Application.run() — GLib option parser raises SystemExit on unrecognised flags, must strip app-custom flags first"
  - "install-autostart.sh resolves python3 via command -v at script runtime (not hardcoded) — portable across virtualenvs and system installs"

patterns-established:
  - "Autostart installer pattern: resolve BASH_SOURCE[0] -> PROJECT_DIR, use command -v for interpreter path, write XDG .desktop with X-GNOME-Autostart-enabled=true"
  - "Snap/AppImage isolation pattern: LD_PRELOAD system library before subprocess spawn when host environment injects incompatible sonames"

requirements-completed: [TRAY-04]

# Metrics
duration: ~30min (including human verification session)
completed: 2026-02-23
---

# Phase 4 Plan 03: Autostart Installer and Phase 4 End-to-End Verification Summary

**XDG autostart .desktop installer with dynamic path resolution, three snap/GLib runtime bug fixes, and full Phase 4 interactive verification: tray icon, profile switching, hide-to-tray, and --tray-only startup all confirmed working.**

## Performance

- **Duration:** ~30 min (including human verification)
- **Started:** 2026-02-23
- **Completed:** 2026-02-23
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 3

## Accomplishments

- Created `install/install-autostart.sh` — resolves absolute paths at runtime, writes a valid XDG .desktop file to `~/.config/autostart/kbd-backlight.desktop` with `--tray-only` Exec flag and `X-GNOME-Autostart-enabled=true`
- Fixed snap core20 libpthread soname conflict by injecting `LD_PRELOAD=/lib/x86_64-linux-gnu/libpthread.so.0` into the tray subprocess environment in `application.py`
- Fixed IPC reliability by replacing `read_line_async` with `GLib.io_add_watch` on stdin fd — messages no longer silently dropped after first receive
- Fixed `--tray-only` flag causing GLib option parser `SystemExit` by stripping it from `sys.argv` before `Gtk.Application.run()` in `main.py`
- All 8 Phase 4 verification steps passed interactively: tray icon visible, profile menu with color swatches, profile switching, hide-to-tray, tray-only startup, save refreshes tray, autostart file correct

## Task Commits

Each task was committed atomically:

1. **Task 1: Create install/install-autostart.sh** — `667761c` (feat)
2. **Task 2 (verification fixes committed during):**
   - `e15fa41` — fix(04-02): preload system libpthread to prevent snap core20 soname conflict
   - `12851f8` — fix(04-02): replace Gio.SubprocessLauncher IPC with GLib.io_add_watch
   - `62fa851` — fix(04-03): strip --tray-only from argv before passing to GLib option parser

## Files Created/Modified

- `install/install-autostart.sh` — XDG autostart installer; resolves python3 and main.py paths at runtime, writes `~/.config/autostart/kbd-backlight.desktop`
- `kbd_backlight/ui/application.py` — LD_PRELOAD libpthread fix + GLib.io_add_watch IPC replacement
- `main.py` — strip `--tray-only` from `sys.argv` before `Gtk.Application.run()`

## Decisions Made

- **LD_PRELOAD libpthread:** When the app is launched from a snap terminal, snap injects `LD_LIBRARY_PATH` pointing to core20 libpthread with a mismatched soname. Preloading the system libpthread before the tray subprocess fork resolves the crash without affecting the GTK4 parent process.
- **GLib.io_add_watch over read_line_async:** `Gio.DataInputStream.read_line_async` silently stopped delivering messages after the first receive when used inside `Gio.SubprocessLauncher`. Replaced with synchronous `GLib.io_add_watch` on the raw stdin file descriptor, which is reliable and simpler.
- **Strip --tray-only from sys.argv:** GLib's built-in option parser processes `sys.argv` and raises `SystemExit(1)` for any flag it doesn't recognise. Custom app flags must be consumed and removed before calling `Gtk.Application.run()`.

## Deviations from Plan

### Auto-fixed Issues (during human verification)

**1. [Rule 1 - Bug] Snap libpthread soname conflict crashes tray subprocess**
- **Found during:** Task 2 (human verification, Step 2)
- **Issue:** Launching app from snap terminal caused `ImportError: libpthread.so.0: version GLIBC_PRIVATE not found` in tray subprocess
- **Fix:** Added `LD_PRELOAD=/lib/x86_64-linux-gnu/libpthread.so.0` to subprocess environment in `application.py` before spawning tray
- **Files modified:** `kbd_backlight/ui/application.py`
- **Committed in:** `e15fa41`

**2. [Rule 1 - Bug] GLib.io_add_watch IPC replaces broken read_line_async**
- **Found during:** Task 2 (human verification, Step 4/6)
- **Issue:** Tray IPC messages after the first were silently dropped; `read_line_async` did not requeue reliably with `Gio.SubprocessLauncher`
- **Fix:** Replaced `Gio.DataInputStream.read_line_async` with `GLib.io_add_watch` on the raw stdin file descriptor; handler returns True to stay registered, False only on QUIT
- **Files modified:** `kbd_backlight/ui/application.py`
- **Committed in:** `12851f8`

**3. [Rule 1 - Bug] --tray-only flag rejected by GLib option parser**
- **Found during:** Task 2 (human verification, Step 7)
- **Issue:** `python3 main.py --tray-only` raised `SystemExit` because GLib parsed `sys.argv` and didn't recognise `--tray-only`
- **Fix:** Added `sys.argv[:] = [a for a in sys.argv if a != '--tray-only']` before `app.run()` in `main.py`, after capturing the flag
- **Files modified:** `main.py`
- **Committed in:** `62fa851`

---

**Total deviations:** 3 auto-fixed (all Rule 1 bugs discovered during human verification)
**Impact on plan:** All three fixes were required for the verification steps to pass. No scope creep — all changes directly relate to the Phase 4 tray feature.

## Issues Encountered

Several runtime bugs were discovered only during interactive verification because they depend on the snap host environment and GLib subprocess internals not visible in unit testing. All three were fixed inline during the verification session with individual commits.

## User Setup Required

None — `install/install-autostart.sh` has been run; `~/.config/autostart/kbd-backlight.desktop` is installed and will auto-launch the app in tray-only mode on next GNOME login.

## Next Phase Readiness

- Phase 4 fully complete: tray icon, profile menu with color swatches, profile switching from tray, hide-to-tray, bidirectional sync on save/delete, `--tray-only` mode, and XDG autostart all working
- Phase 5 (Global Hotkeys) can begin — the app already has `load_profile_from_tray(name)` entry point in `MainWindow` which hotkey logic can reuse
- Known concern for Phase 5: XDG Desktop Portal Global Shortcuts API Wayland support not yet researched; may need X11 fallback path

---
*Phase: 04-system-tray-and-autostart*
*Completed: 2026-02-23*

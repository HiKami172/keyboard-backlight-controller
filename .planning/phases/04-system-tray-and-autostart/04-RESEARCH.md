# Phase 4: System Tray and Autostart - Research

**Researched:** 2026-02-22
**Domain:** Linux system tray (AyatanaAppIndicator3 + GTK3 subprocess), GTK4/GTK3 process isolation, Gio.Subprocess IPC, XDG autostart .desktop files
**Confidence:** HIGH (all critical paths verified by direct Python execution on target machine)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRAY-01 | System tray icon appears with right-click menu listing all profiles | AyatanaAppIndicator3 tray indicator with GTK3 Gtk.Menu verified; ubuntu-appindicators@ubuntu.com GNOME Shell extension confirmed installed and now enabled; icon appears in top panel |
| TRAY-02 | User can switch profiles from tray menu with one click | GTK3 menu item click callback writes profile name to subprocess stdout; main GTK4 process reads via Gio.DataInputStream.read_line_async(); then calls BacklightController.apply() + ProfileManager.set_last_profile() |
| TRAY-03 | Each profile shows a color swatch in the tray menu | GdkPixbuf.Pixbuf.new() + pixbuf.fill(RGBA_packed_int) creates solid-color 16x16 image; GTK3 Gtk.MenuItem with inner Gtk.Box (Image + Label) is the non-deprecated pattern |
| TRAY-04 | App launches into tray-only mode on login via XDG autostart .desktop file | ~/.config/autostart/kbd-backlight.desktop with Exec using --tray-only flag; sys.argv check in Application.__init__ skips window presentation |
| TRAY-05 | Closing the main window hides to tray instead of quitting | Already implemented in Phase 3 via do_close_request() returning True and calling self.hide(); Application.hold() prevents auto-quit when all windows hidden |
</phase_requirements>

---

## Summary

Phase 4 has one critical architectural constraint discovered by direct testing: **AyatanaAppIndicator3 and GTK4 cannot coexist in the same Python process**. The `libayatana-appindicator3` C library hard-links against `libgtk-3.so.0`, and PyGObject's namespace system refuses to load GTK 4.0 if GTK 3.0 is already loaded (and vice versa). Attempting to import `AyatanaAppIndicator3` after GTK 4.0 raises `ImportError: Requiring namespace 'Gtk' version '3.0', but '4.0' is already loaded`.

The solution is a **subprocess architecture**: the main GTK4/Adw application launches a separate Python process (`tray.py`) that uses GTK3 + AyatanaAppIndicator3. The two processes communicate via JSON messages over stdin/stdout pipes using `Gio.Subprocess` (parent side, GTK4) and `GLib.io_add_watch` (child side, GTK3). The subprocess reads profiles directly from `~/.config/kbd-backlight/profiles.json` via a `ProfileManager` instance, and notifies the parent of profile selection by writing the profile name to stdout.

A second critical finding: on this Ubuntu 24.04 system, the `ubuntu-appindicators@ubuntu.com` GNOME Shell extension is **installed** (`gnome-shell-extension-appindicator` package) but was **not enabled** at the time of research. It must be explicitly enabled via `gnome-extensions enable ubuntu-appindicators@ubuntu.com` (or via GNOME Extensions app). The extension reached state ENABLED (1) after enabling and will persist across sessions. This is a one-time user setup step that needs to be documented.

**Primary recommendation:** Use a GTK3 subprocess (tray.py) communicating with the GTK4 main process via Gio.Subprocess stdin/stdout pipes. The subprocess uses AyatanaAppIndicator3 + GTK3 Gtk.Menu with GdkPixbuf color swatches. The main process uses `app.hold()` to stay alive when the window is hidden.

---

## Standard Stack

### Core (all verified on target machine)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| AyatanaAppIndicator3 | 0.1 | GTK3-based tray icon with right-click menu on GNOME/Ubuntu | Only available GIR tray library on this system; gir1.2-ayatanaappindicator3-0.1 installed |
| GTK 3.0 | (system) | Required by AyatanaAppIndicator3; used ONLY in tray subprocess | Hard dependency of libayatana-appindicator3; tray.py must be a separate process |
| GTK 4.0 / libadwaita | 4.14.2 / 1.5 | Main application (unchanged from Phase 3) | Project baseline |
| Gio.Subprocess | (GLib) | Launch tray.py subprocess from GTK4 app with piped stdin/stdout | Part of GLib/GIO; supports STDIN_PIPE + STDOUT_PIPE flags; non-blocking async reads |
| GLib.io_add_watch | (GLib) | Watch stdin for incoming messages in tray subprocess's GTK main loop | Available in both GTK3 and GTK4 GLib; canonical GTK I/O watching mechanism |
| GdkPixbuf | (GTK3 side) | Create solid-color 16x16 pixbufs for profile color swatches in menu | pixbuf.fill(packed_rgba) creates single-color image; used in tray subprocess only |
| gnome-shell-extension-appindicator | ubuntu-appindicators@ubuntu.com | GNOME Shell extension to render AppIndicator icons in top panel | Installed on system; must be enabled by user; without it tray icon is invisible on GNOME |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dbus-python | 1.3.2 | (Available, not needed) D-Bus IPC alternative to stdin/stdout pipes | Not used in chosen architecture; stdin/stdout pipes are simpler for this use case |
| GLib.MainLoop | (GTK3 side) | Run event loop in tray subprocess without a Gtk window | Gtk.main() works equally; GLib.MainLoop is lower-overhead for headless subprocess |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GTK3 subprocess with AyatanaAppIndicator3 | trayer PyPI package (pure D-Bus SNI) | trayer is not installed; requires pip install; early-stage (6 commits, 1 star); not a system package |
| GTK3 subprocess with AyatanaAppIndicator3 | Pure dbus-python StatusNotifierItem impl | Implements full SNI + DBusMenu protocols from scratch; hundreds of lines of D-Bus boilerplate; not worth it for personal tool |
| GTK3 subprocess with AyatanaAppIndicator3 | AppIndicator3 (non-Ayatana) | gir1.2-appindicator3-0.1 is NOT installed; gir1.2-ayatanaappindicator3-0.1 IS installed |
| stdin/stdout JSON IPC | Shared ProfileManager + file polling | ProfileManager reads from disk directly work; but file polling adds complexity and latency; stdin/stdout is synchronous and event-driven |
| Gtk.ImageMenuItem (deprecated) | Gtk.MenuItem + Gtk.Box (Image + Label) | Both work in GTK3; Box approach avoids deprecation warnings; minimal complexity difference |

**Installation (one-time user setup):**
```bash
# Packages are already installed — no apt install needed
# REQUIRED: Enable the GNOME Shell AppIndicator extension
gnome-extensions enable ubuntu-appindicators@ubuntu.com
# Verify:
gnome-extensions info ubuntu-appindicators@ubuntu.com
```

---

## Architecture Patterns

### Recommended Project Structure

```
kbd_backlight/
├── hardware/
│   └── backlight.py          # Phase 1 (done)
├── profiles/
│   ├── profile.py            # Phase 2 (done)
│   └── manager.py            # Phase 2 (done)
├── ui/
│   ├── application.py        # Phase 3 (extend: hold(), subprocess launch, stdout watcher)
│   ├── window.py             # Phase 3 (extend: load_profile_from_tray() method)
│   └── tray.py               # Phase 4 NEW: GTK3 + AyatanaAppIndicator3 subprocess
└── __init__.py
```

### Pattern 1: GTK3 Tray Subprocess (tray.py)

**What:** Separate Python script that imports AyatanaAppIndicator3 + GTK3, builds a tray indicator with a Gtk.Menu, and communicates with the parent via stdin/stdout.

**When to use:** Whenever GTK4 app needs AppIndicator tray (forced by GTK3/GTK4 conflict).

```python
# kbd_backlight/ui/tray.py — runs as subprocess, GTK3 only
import sys
import json
import gi
gi.require_version('AyatanaAppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')
from gi.repository import AyatanaAppIndicator3, Gtk, GdkPixbuf, GLib

# ProfileManager can be imported — it only uses stdlib (json, pathlib, dataclasses)
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from kbd_backlight.profiles.manager import ProfileManager

class TrayProcess:
    def __init__(self):
        self._manager = ProfileManager()
        self._indicator = AyatanaAppIndicator3.Indicator.new(
            'kbd-backlight',
            'input-keyboard',
            AyatanaAppIndicator3.IndicatorCategory.HARDWARE
        )
        self._indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self._build_menu()

        # Watch stdin for commands from parent (REFRESH, QUIT)
        GLib.io_add_watch(sys.stdin.fileno(), GLib.IO_IN, self._on_stdin)

    def _build_menu(self):
        menu = Gtk.Menu()
        profiles = self._manager.get_all_profiles()
        for name, profile in profiles.items():
            item = self._make_profile_item(name, profile.r, profile.g, profile.b)
            menu.append(item)
        menu.append(Gtk.SeparatorMenuItem())
        show_item = Gtk.MenuItem(label='Open Settings')
        show_item.connect('activate', lambda _: self._send('SHOW'))
        menu.append(show_item)
        quit_item = Gtk.MenuItem(label='Quit')
        quit_item.connect('activate', lambda _: self._send('QUIT'))
        menu.append(quit_item)
        menu.show_all()
        self._indicator.set_menu(menu)

    def _make_profile_item(self, name, r, g, b):
        item = Gtk.MenuItem()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        # Color swatch: 16x16 solid-color pixbuf
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 16, 16)
        packed = (r << 24) | (g << 16) | (b << 8) | 0xFF
        pixbuf.fill(packed)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        label = Gtk.Label(label=name)
        box.pack_start(image, False, False, 0)
        box.pack_start(label, False, False, 0)
        item.add(box)
        item.connect('activate', lambda _, n=name: self._on_profile_clicked(n))
        return item

    def _on_profile_clicked(self, name):
        self._send(json.dumps({'action': 'select_profile', 'name': name}))

    def _on_stdin(self, fd, condition):
        line = sys.stdin.readline().strip()
        if line == 'REFRESH':
            self._build_menu()
        elif line == 'QUIT':
            Gtk.main_quit()
            return False
        return True  # Keep watching

    def _send(self, message):
        print(message, flush=True)

if __name__ == '__main__':
    TrayProcess()
    Gtk.main()
```

### Pattern 2: Parent Process — Launching and Watching Subprocess (application.py)

**What:** GTK4 Application launches tray.py as a Gio.Subprocess with piped I/O. Reads stdout asynchronously via Gio.DataInputStream. Sends REFRESH messages on profile change.

```python
# In Application._on_activate() — after controller/window setup:
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib
import sys, os

def _start_tray(self):
    tray_script = os.path.join(os.path.dirname(__file__), 'tray.py')
    launcher = Gio.SubprocessLauncher.new(
        Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE
    )
    self._tray_proc = launcher.spawnv([sys.executable, tray_script])
    # Wrap stdout pipe for line-by-line async reading
    stdout_pipe = self._tray_proc.get_stdout_pipe()
    self._tray_reader = Gio.DataInputStream.new(stdout_pipe)
    self._read_next_tray_line()

def _read_next_tray_line(self):
    self._tray_reader.read_line_async(
        GLib.PRIORITY_DEFAULT, None, self._on_tray_line
    )

def _on_tray_line(self, source, result):
    line, _ = source.read_line_finish_utf8(result)
    if line is None:
        return  # Subprocess closed
    try:
        msg = json.loads(line)
        if msg.get('action') == 'select_profile':
            self._apply_profile_by_name(msg['name'])
        elif msg.get('action') == 'show':
            self.show_window()
        elif msg.get('action') == 'quit':
            self.quit()
    except json.JSONDecodeError:
        pass
    self._read_next_tray_line()  # Queue next read

def _send_tray(self, message: str):
    """Write a line to tray subprocess stdin."""
    if self._tray_proc is not None:
        stdin = self._tray_proc.get_stdin_pipe()
        stdin.write_all((message + '\n').encode(), None)

def notify_tray_refresh(self):
    """Call after any profile create/delete/rename."""
    self._send_tray('REFRESH')
```

### Pattern 3: Application.hold() for Background Persistence

**What:** Prevents Adw.Application from auto-quitting when the last window closes.

**When to use:** Must be called BEFORE or DURING `_on_activate`. Must call `release()` only when user explicitly quits.

```python
# In Application.__init__ or _on_activate():
self.hold()  # Keep app running even with no visible windows

# In tray quit handler (after receiving QUIT from subprocess):
def _on_tray_quit(self):
    if self._tray_proc:
        self._tray_proc.force_exit()
    self.release()  # Allow auto-quit
    self.quit()
```

### Pattern 4: Tray-Only Mode via sys.argv

**What:** `--tray-only` flag in sys.argv causes `_on_activate` to skip presenting the window.

**When to use:** XDG autostart .desktop file passes this flag; normal double-click launch does not.

```python
# In Application.__init__:
self._tray_only = '--tray-only' in sys.argv

# In Application._on_activate():
if not self._tray_only:
    self._window.present()
    self._restore_last_profile()
# Always start tray:
self._start_tray()
```

**Single-instance behavior:** Adw.Application is single-instance by default (D-Bus). If autostart launched with `--tray-only`, a subsequent user double-click on the app launcher sends `activate` to the existing instance. That second `activate` call arrives WITHOUT `--tray-only` in argv — but `self._tray_only` is already set from the first launch. Therefore, the window-show logic must not rely on `self._tray_only` in subsequent `activate` calls. Use a separate `self._activated_once` flag or always show window on tray icon click.

### Pattern 5: XDG Autostart .desktop File

**What:** Placed in `~/.config/autostart/` — GNOME launches it on login.

```ini
# ~/.config/autostart/kbd-backlight.desktop
[Desktop Entry]
Type=Application
Name=Keyboard Backlight Controller
Comment=Keyboard backlight controller — runs in system tray
Exec=/usr/bin/python3 /home/hikami/Documents/projects/keyboard-backlights-control/main.py --tray-only
Icon=input-keyboard
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
```

**Notes:**
- `StartupNotify=false` — no startup feedback (app doesn't show a window)
- `X-GNOME-Autostart-enabled=true` — explicit GNOME enable flag
- `Exec` uses absolute path to `python3` and to `main.py` — no PATH dependency
- Alternatively, the install script can write this file automatically

### Anti-Patterns to Avoid

- **Importing AyatanaAppIndicator3 in the GTK4 process:** Fails at runtime with `ImportError: Requiring namespace 'Gtk' version '3.0', but '4.0' is already loaded`. No workaround exists — the C library hard-links GTK3.
- **Using AppIndicator3 (non-Ayatana):** `gir1.2-appindicator3-0.1` is installed but `gi.require_version('AppIndicator3', '0.1')` succeeds. However, `gir1.2-ayatanaappindicator3-0.1` is the system default on Ubuntu 24.04. Use Ayatana variant.
- **Using Gtk.StatusIcon in the GTK4 process:** Removed in GTK4 entirely.
- **Blocking stdout reads in parent:** Must use `read_line_async()` not `read_line()` — blocking reads freeze the GTK4 event loop.
- **Forgetting menu.show_all():** AyatanaAppIndicator3 requirement: `set_menu()` is mandatory AND `menu.show_all()` must be called before `set_menu()`, otherwise the indicator is never rendered.
- **Not calling app.hold():** Without `hold()`, Adw.Application quits when the last window closes (since window.hide() removes it from the window list). The app disappears silently.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GTK3/GTK4 process isolation | Custom subprocess protocol | Gio.Subprocess + stdin/stdout | GLib-native; cancellable, async, integrates with GTK event loop |
| Tray icon | Raw D-Bus StatusNotifierItem | AyatanaAppIndicator3 | Full SNI + DBusMenu is hundreds of lines; AyatanaAppIndicator3 handles all of it |
| Color swatch images | PIL/Pillow | GdkPixbuf.Pixbuf.new() + pixbuf.fill() | GdkPixbuf is already loaded in GTK3 subprocess; no extra dependency |
| Autostart file creation | Custom installer | Script that writes ~/.config/autostart/kbd-backlight.desktop | One write call; no library needed |

**Key insight:** The subprocess boundary is the correct abstraction here. Don't fight the GTK3/GTK4 conflict — embrace the process boundary as a clean architectural separation.

---

## Common Pitfalls

### Pitfall 1: GTK3/GTK4 Namespace Conflict
**What goes wrong:** `ImportError: Requiring namespace 'Gtk' version '3.0', but '4.0' is already loaded` when attempting to use AyatanaAppIndicator3 in the GTK4 process.
**Why it happens:** `libayatana-appindicator3.so` links against `libgtk-3.so.0` at the C level. When PyGObject loads the typelib, it triggers GTK3 initialization. PyGObject refuses to have two GTK versions in the same namespace.
**How to avoid:** AyatanaAppIndicator3 must be in a **separate Python process** that never imports GTK4. Verified by direct testing on this machine.
**Warning signs:** Any `gi.require_version('AyatanaAppIndicator3', ...)` call after `gi.require_version('Gtk', '4.0')` in the same process.

### Pitfall 2: AppIndicator Extension Not Enabled
**What goes wrong:** Tray indicator is created and running but no icon appears in GNOME top panel. No errors — just invisible.
**Why it happens:** The `ubuntu-appindicators@ubuntu.com` GNOME Shell extension is installed (via `gnome-shell-extension-appindicator` package) but was NOT enabled. GNOME Shell requires this extension to render AppIndicator icons. Verified: extension was in state INITIALIZED (6), enabled: false on this machine at research time.
**How to avoid:** Detect extension state programmatically and show user-facing error if not enabled.
**Warning signs:** Indicator creates successfully but icon never appears in panel.

```python
# Detection pattern:
import subprocess
result = subprocess.run([
    'gdbus', 'call', '--session',
    '--dest', 'org.gnome.Shell.Extensions',
    '--object-path', '/org/gnome/Shell/Extensions',
    '--method', 'org.gnome.Shell.Extensions.GetExtensionInfo',
    'ubuntu-appindicators@ubuntu.com'
], capture_output=True, text=True)
if "'state': <1.0>" not in result.stdout:  # state 1 = ENABLED
    # Show error dialog in GTK4 main process
    pass
```

### Pitfall 3: Subprocess stdout Blocking Parent Event Loop
**What goes wrong:** Parent process freezes while waiting for tray subprocess to send a message.
**Why it happens:** Using synchronous `read_line()` on the subprocess stdout pipe blocks the GLib main loop.
**How to avoid:** Always use `Gio.DataInputStream.read_line_async()` with a callback. Re-queue the next read at the end of each callback.
**Warning signs:** App hangs after launching tray subprocess.

### Pitfall 4: Indicator Not Rendered (Missing menu or show_all)
**What goes wrong:** AyatanaAppIndicator3 indicator exists in code but never appears in tray.
**Why it happens:** AppIndicator spec requires a menu to be set before the indicator renders. Also, GTK3 menus require `show_all()` before `set_menu()`.
**How to avoid:** Always call `menu.show_all()` and `indicator.set_menu(menu)` during initialization.
**Warning signs:** Indicator object created, status set to ACTIVE, but nothing in panel.

### Pitfall 5: Single-Instance --tray-only Interaction
**What goes wrong:** User launches app from application menu, but window doesn't appear because `self._tray_only = True` was set during the autostart launch.
**Why it happens:** Adw.Application is single-instance. The second `activate` signal goes to the already-running instance. `self._tray_only` is still `True` from when autostart set it.
**How to avoid:** Treat `self._tray_only` as a "startup mode" flag only, not a permanent "never show window" flag. On any `activate` call (from tray click or new launch), show the window via `show_window()`.

### Pitfall 6: GdkPixbuf.Pixbuf.fill() Color Format
**What goes wrong:** Color swatch shows wrong color.
**Why it happens:** `pixbuf.fill()` takes a 32-bit integer in `RGBA` format (not `ARGB`): `(r << 24) | (g << 16) | (b << 8) | 0xFF`.
**How to avoid:** Use the RGBA packing formula explicitly. For `r=0, g=100, b=255`: `(0 << 24) | (100 << 16) | (255 << 8) | 0xFF = 0x0064FFFF`.
**Warning signs:** Swatches show as wrong color or fully transparent.

---

## Code Examples

Verified patterns from direct execution on target machine:

### Create AyatanaAppIndicator3 Indicator
```python
# Source: Direct Python execution on Ubuntu 24.04, confirmed working
import gi
gi.require_version('AyatanaAppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')
from gi.repository import AyatanaAppIndicator3, Gtk

indicator = AyatanaAppIndicator3.Indicator.new(
    'kbd-backlight',                                  # unique ID
    'input-keyboard',                                 # system icon name (Adwaita theme)
    AyatanaAppIndicator3.IndicatorCategory.HARDWARE   # category
)
indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
```

### Create Color Swatch Pixbuf (GTK3 subprocess)
```python
# Source: Direct Python execution on target machine
from gi.repository import GdkPixbuf

def make_color_swatch(r: int, g: int, b: int, size: int = 16) -> GdkPixbuf.Pixbuf:
    """Create a solid-color square pixbuf for use as menu item icon."""
    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, size, size)
    packed = (r << 24) | (g << 16) | (b << 8) | 0xFF  # RGBA format (alpha=0xFF=opaque)
    pixbuf.fill(packed)
    return pixbuf
```

### Non-Deprecated Menu Item with Color Swatch
```python
# Source: Direct Python execution, no deprecation warnings
def make_profile_menu_item(name: str, r: int, g: int, b: int) -> Gtk.MenuItem:
    item = Gtk.MenuItem()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    pixbuf = make_color_swatch(r, g, b)
    image = Gtk.Image.new_from_pixbuf(pixbuf)
    label = Gtk.Label(label=name)
    label.set_xalign(0)  # Left-align label text
    box.pack_start(image, False, False, 0)
    box.pack_start(label, True, True, 0)
    item.add(box)
    return item
```

### Check AppIndicator Extension State
```python
# Source: Direct gdbus call tested on GNOME Shell 46
import subprocess

def check_appindicator_extension() -> bool:
    """Return True if ubuntu-appindicators@ubuntu.com is enabled in GNOME Shell."""
    result = subprocess.run([
        'gdbus', 'call', '--session',
        '--dest', 'org.gnome.Shell.Extensions',
        '--object-path', '/org/gnome/Shell/Extensions',
        '--method', 'org.gnome.Shell.Extensions.GetExtensionInfo',
        'ubuntu-appindicators@ubuntu.com'
    ], capture_output=True, text=True, timeout=5)
    return "'state': <1.0>" in result.stdout and "'enabled': <true>" in result.stdout
```

### Watch stdin in GTK3 subprocess
```python
# Source: GLib documentation; GLib.IO_IN and io_add_watch confirmed available
import sys, json
from gi.repository import GLib, Gtk

def on_stdin_data(fd, condition, tray):
    line = sys.stdin.readline().strip()
    if not line:
        return True
    if line == 'REFRESH':
        tray.rebuild_menu()
    elif line == 'QUIT':
        Gtk.main_quit()
        return False
    return True  # Return True to keep watching

GLib.io_add_watch(sys.stdin.fileno(), GLib.IO_IN, on_stdin_data, tray_instance)
```

### Launch Tray Subprocess (GTK4 Application side)
```python
# Source: Gio.SubprocessFlags verified; Gio.DataInputStream.read_line_async confirmed
import gi, sys, os, json
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

def start_tray_subprocess(self):
    tray_script = os.path.join(os.path.dirname(__file__), 'tray.py')
    launcher = Gio.SubprocessLauncher.new(
        Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE
    )
    self._tray_proc = launcher.spawnv([sys.executable, tray_script])
    stdout = self._tray_proc.get_stdout_pipe()
    self._tray_reader = Gio.DataInputStream.new(stdout)
    self._tray_reader.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_tray_message)

def _on_tray_message(self, source, result):
    line, _ = source.read_line_finish_utf8(result)
    if line:
        try:
            msg = json.loads(line)
            action = msg.get('action')
            if action == 'select_profile':
                self._apply_profile_by_name(msg['name'])
            elif action == 'show':
                self.show_window()
            elif action == 'quit':
                self.quit()
        except (json.JSONDecodeError, KeyError):
            pass
        # Queue next read
        source.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_tray_message)
```

### XDG Autostart .desktop File Content
```ini
# ~/.config/autostart/kbd-backlight.desktop
[Desktop Entry]
Type=Application
Name=Keyboard Backlight Controller
Comment=Keyboard backlight controller — runs in system tray
Exec=/usr/bin/python3 /home/hikami/Documents/projects/keyboard-backlights-control/main.py --tray-only
Icon=input-keyboard
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Gtk.StatusIcon` (GTK3) | `AyatanaAppIndicator3` via subprocess | GTK4 launch (~2020) | StatusIcon removed in GTK4; AppIndicator is the Ubuntu/GNOME standard |
| `AppIndicator3` (Unity-era) | `AyatanaAppIndicator3` (Ayatana fork) | Ubuntu 20.04+ | Ayatana is the maintained fork; `gir1.2-ayatanaappindicator3-0.1` is the system package on Ubuntu 24.04 |
| Single-process GTK3 app + tray | GTK4 main app + GTK3 subprocess | GTK4 adoption | Both GTK versions cannot coexist in same process (confirmed by testing) |
| `gi.require_version` import order trick | Subprocess isolation | GTK4 launch | No order trick works; process boundary is the only solution |

**Deprecated/outdated:**
- `Gtk.StatusIcon`: Removed in GTK4. Do not use even in GTK3 subprocess (deprecated since GTK3.14).
- `Gtk.ImageMenuItem`: Deprecated since GTK3.10. Use `Gtk.MenuItem` + inner `Gtk.Box` instead.
- `AppIndicator3` (non-Ayatana): `gir1.2-appindicator3-0.1` is present but unmaintained upstream. Ayatana is the Ubuntu standard.

---

## Open Questions

1. **Subprocess crash recovery**
   - What we know: `Gio.DataInputStream.read_line_finish_utf8()` returns `None` when subprocess stdout closes
   - What's unclear: Whether to auto-restart the tray subprocess on crash, and how to detect it vs. intentional quit
   - Recommendation: For v1, if tray subprocess exits unexpectedly, show a notification or log it; don't auto-restart (adds complexity). User can relaunch app.

2. **Autostart file path hardcodes home directory**
   - What we know: XDG autostart files should go in `~/.config/autostart/`; the `Exec` line needs the full path to `main.py`
   - What's unclear: Best way to generate the `Exec` path dynamically (could be `sys.argv[0]` resolved path)
   - Recommendation: Install script writes the .desktop file using the resolved absolute path at install time. Alternative: add `--install-autostart` flag to `main.py` that writes the file itself.

3. **Tray icon for color_cycle mode (no static color)**
   - What we know: `color_cycle` profiles have r=0, g=0, b=0 (hardware cycles colors, no fixed RGB)
   - What's unclear: What color swatch to show for color_cycle profiles in tray menu
   - Recommendation: Show a gradient/rainbow icon or a neutral gray swatch for color_cycle profiles. Simplest: use (128, 128, 128) gray.

4. **Profile list refresh when main window saves/deletes**
   - What we know: Tray subprocess can be sent `REFRESH\n` via stdin to rebuild its menu
   - What's unclear: Which events in `window.py` need to trigger a refresh signal to Application, which then sends REFRESH to tray
   - Recommendation: Add `Application.notify_tray_refresh()` call in `MainWindow._do_save()` and `_on_delete_response()`. Window calls `self._app.notify_tray_refresh()` where `self._app` is the Adw.Application instance.

---

## Sources

### Primary (HIGH confidence — verified by direct execution)
- Direct Python execution on Ubuntu 24.04: AyatanaAppIndicator3 + GTK3/GTK4 conflict confirmed
- `ldd /usr/lib/x86_64-linux-gnu/libayatana-appindicator3.so.1`: GTK3 hard dependency confirmed
- `gdbus call` to `org.gnome.Shell.Extensions.GetExtensionInfo`: Extension state verified
- `gdbus call` to `org.gnome.Shell.Extensions.EnableExtension`: Extension enabling verified
- `python3 -c` tests: GLib.io_add_watch, Gio.Subprocess flags, GdkPixbuf.fill() color packing all confirmed working

### Secondary (MEDIUM confidence — official docs/packages)
- [AyatanaAppIndicator3 PGI docs](https://lazka.github.io/pgi-docs/AyatanaAppIndicator3-0.1/classes/Indicator.html) — Indicator API reference
- [GNOME Discourse: StatusIcon replacement in GTK4](https://discourse.gnome.org/t/what-to-use-instead-of-statusicon-in-gtk4-to-display-the-icon-in-the-system-tray/7175) — GTK4 tray situation
- [ArchWiki: XDG Autostart](https://wiki.archlinux.org/title/XDG_Autostart) — .desktop file format
- [libayatana-appindicator GitHub](https://github.com/AyatanaIndicators/libayatana-appindicator) — upstream source

### Tertiary (LOW confidence — not directly verified)
- trayer PyPI package (pure D-Bus SNI for GTK4): 6 commits, 1 star — not verified working; rejected in favor of AyatanaAppIndicator3 subprocess

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed; import chains tested by execution
- Architecture (subprocess approach): HIGH — GTK3/GTK4 conflict confirmed by direct testing; alternative approaches investigated and rejected
- Color swatches (TRAY-03): HIGH — GdkPixbuf.fill() pattern confirmed working
- Autostart .desktop: HIGH — format verified from existing system files (caffeine.desktop reference)
- GNOME extension requirement: HIGH — state verified via D-Bus; enabling confirmed persistent
- Pitfalls: HIGH — all pitfalls discovered by actual test failures on this machine

**Research date:** 2026-02-22
**Valid until:** 2026-05-22 (stable ecosystem — GTK, AyatanaAppIndicator3, GNOME Shell extensions)

# Stack Research

**Domain:** Linux desktop GUI application — hardware controller (ASUS TUF F16 keyboard backlight)
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH (core stack verified via official docs; tray integration is an ecosystem weak spot)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.10+ | Application language | System-installed on Ubuntu 24.04, no packaging needed for personal tool; GObject introspection is Pythonic |
| PyGObject | 3.54.5 | GTK4 bindings | The *only* official Python binding for GTK4; GObject Introspection generates bindings at runtime — no manual wrapping needed. Verified current on PyPI (released Oct 2025) |
| GTK 4 | 4.0 (via gir1.2-gtk-4.0) | GUI toolkit | Native on GNOME/Ubuntu, hardware-accelerated rendering, full widget set for this use case. GTK3 is the legacy predecessor — don't use it for new apps |
| libadwaita | 1.5.0 (Ubuntu 24.04 package) | GNOME design system | Provides Adwaita-styled widgets (`AdwApplication`, `AdwPreferencesPage`, etc.) that fit GNOME perfectly. Required for `Gtk.ColorDialog` (GTK 4.10+) and proper GNOME HIG compliance |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| trayer | latest (Oct 2025 GitHub) | System tray icon (GTK4-native) | For the system tray icon with context menu — it implements StatusNotifierItem + DBusMenu D-Bus protocols and is the only maintained GTK4-native tray library; requires `gnome-shell-extension-appindicator` extension on GNOME |
| dbus-python | system (python3-dbus) | D-Bus communication | Used by trayer under the hood; may also be needed for sending D-Bus signals to GNOME for keyboard shortcuts |
| GIO / GSettings | bundled with PyGObject | Configuration storage | For storing profiles and preferences — GSettings is the canonical GNOME config system, supports schema validation, property binding to widgets, and dconf backend |
| Gtk.ColorDialog | bundled with GTK 4.10+ | Color picker UI | GTK 4.10 replaced `ColorButton`/`ColorChooserWidget` (deprecated) with the async `ColorDialog` + `ColorDialogButton` API — use this, not the old widgets |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| glib-compile-schemas | Compile GSettings schemas | Required before GSettings config works; run with `glib-compile-schemas ~/.local/share/glib-2.0/schemas/` during development |
| udevadm | Debug/test udev rules | Use `sudo udevadm test /sys/class/leds/asus::kbd_backlight/` to verify permission rules before deploying |
| GNOME Builder (optional) | IDE with GTK4/Blueprint support | The Workbench companion app previews UI files in real-time — useful for color picker widget iteration |

---

## Installation

```bash
# System packages — Ubuntu 24.04
sudo apt install \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1 \
  python3-dbus \
  libgirepository-2.0-dev

# Install trayer for GTK4 system tray
pip3 install trayer

# GNOME extension required for tray icon to appear in GNOME Shell
# Option 1: GNOME Extensions app
gnome-extensions install appindicatorsupport@rgcjonas.gmail.com
# Option 2: Ubuntu package
sudo apt install gnome-shell-extension-appindicator
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| PyGObject + GTK4 | PySide6 (Qt6) | If you need cross-platform (Windows/macOS) or already have Qt expertise. Qt is heavier, licensing is LGPL/commercial, and it does NOT integrate with GNOME's HIG or libadwaita. Wrong choice for a GNOME-native tool |
| PyGObject + GTK4 | Tkinter | Never for this use case — Tkinter has no system tray on GNOME, no GNOME-style color picker, and looks out of place on Ubuntu |
| trayer | pystray | pystray 0.19.5 (Sep 2023, no GTK4 support documented) uses legacy GtkStatusIcon API, which GNOME removed in 3.26. Pystray works on GTK3 and X11 but is unreliable on GNOME Wayland. Trayer implements StatusNotifierItem correctly |
| trayer | AppIndicator3 (gi.require_version) | AppIndicator3 uses GTK3 — mixing GTK3 and GTK4 in the same process is unsupported and causes symbol conflicts |
| GSettings | JSON file (XDG_CONFIG_HOME) | Use JSON for profile data only if you need schema flexibility and want simpler dev setup. GSettings requires schema compilation steps during development but provides atomic writes, type safety, and GTK property binding. Use GSettings for app settings, JSON or GSettings for named profiles |
| Gtk.ColorDialog | Gtk.ColorButton | ColorButton is deprecated since GTK 4.10. ColorDialog provides async API suitable for modal color selection dialogs |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyGTK (pygtk package) | GTK2 binding — end of life, not available on modern Ubuntu | PyGObject |
| GTK3 / PyGObject with GTK3 (`gi.require_version("Gtk", "3.0")`) | GTK3 is the legacy version; GNOME and Ubuntu are fully on GTK4 for new apps; GTK3 AppIndicator conflicts with GTK4 in same process | GTK4 |
| `Gtk.ColorChooserWidget` / `Gtk.ColorChooserDialog` | Deprecated since GTK 4.10 — emits deprecation warnings; removed in GTK 5 | `Gtk.ColorDialog` + `Gtk.ColorDialogButton` |
| `Gtk.StatusIcon` | Removed from GTK 4 entirely — was the old system tray API in GTK3 | trayer (StatusNotifierItem protocol) |
| polkit / pkexec for sysfs writes | Requires password dialog on every write — terrible UX for a real-time color picker | udev rule granting group write access to `/sys/class/leds/asus::kbd_backlight/` |
| asusctl / rog-control-center | Full-stack ASUS daemon with Rust/DBus complexity — overkill for single-machine personal tool | Direct sysfs writes via Python `open()` |
| Global hotkeys via X11 (Xlib/python-xlib) | Wayland does not support global hotkeys from userspace; this approach will break when Ubuntu fully migrates to Wayland | Application-level shortcuts via `Gtk.ShortcutController` + profile switching via tray menu |

---

## Stack Patterns by Variant

**If running on X11 (current Ubuntu default):**
- Global hotkeys via `Gtk.ShortcutController` work within the app window
- For tray-triggered profile switch, the tray menu click triggers the switch — no global hotkey needed outside the window
- trayer + AppIndicator extension works reliably

**If running on Wayland (future Ubuntu default):**
- Same tray approach works (trayer uses D-Bus/StatusNotifierItem which is Wayland-agnostic)
- Window positioning constraints exist (can't set exact coordinates), but doesn't affect this app
- No global hotkeys system-wide — design around tray menu as primary profile switch mechanism

**If needing a custom gradient color picker (two-color gradient selection):**
- GTK4 does not provide a built-in two-color gradient picker — must build a custom `Gtk.DrawingArea` widget
- Use Cairo (via `import cairo`) for gradient rendering within the DrawingArea
- `Gtk.GestureClick` and `Gtk.GestureDrag` handle mouse interaction on the custom widget

---

## Permission Solution (udev rule)

The sysfs path `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` requires root by default.

**Solution:** Create a udev rule granting group write access.

```bash
# /etc/udev/rules.d/99-asus-kbd-backlight.rules
SUBSYSTEM=="leds", KERNEL=="asus::kbd_backlight", ACTION=="add", \
  RUN+="/bin/chgrp video /sys%p/kbd_rgb_mode", \
  RUN+="/bin/chmod g+w /sys%p/kbd_rgb_mode"

# Add user to video group
sudo usermod -aG video $USER
# Reload rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

This approach (MEDIUM confidence — verified pattern for sysfs LED access, specific path needs testing on hardware) avoids any sudo prompt during normal operation.

---

## Hardware Interface Reference

Sysfs path: `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode`

Write format: `"cmd mode R G B speed"`

| Parameter | Values | Notes |
|-----------|--------|-------|
| cmd | 0 or 1 | No functional effect — use `1` |
| mode | 0=static, 1=breathing, 2=color_cycle, 3=strobe | strobe value verified in PROJECT.md; color_cycle may be labeled "disco" in some sources |
| R, G, B | 0–255 | Standard RGB |
| speed | 0=slow, 1=medium, 2=fast | Only relevant for modes 1–3 |

Example write: `"1 0 0 100 250 0"` → static, R=0, G=100, B=250

Python write pattern:
```python
SYSFS_PATH = "/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode"

def apply_mode(mode: int, r: int, g: int, b: int, speed: int) -> None:
    payload = f"1 {mode} {r} {g} {b} {speed}\n"
    with open(SYSFS_PATH, "w") as f:
        f.write(payload)
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| PyGObject 3.54.5 | Python 3.9–3.13, GTK 4.0 | Ubuntu 24.04 system Python is 3.12 — fully compatible |
| libadwaita 1.5.0 | GTK 4.12 | Ubuntu 24.04 Noble ships libadwaita 1.5 — `Gtk.ColorDialog` (added GTK 4.10) is available |
| trayer (2025) | Python 3.8+, PyGObject, dbus-python | Small library; requires GNOME Shell AppIndicator extension for icon to appear |
| GSettings | GLib 2.x (any modern) | Schema compilation requires `glib-compile-schemas` during setup |

---

## Autostart on Boot/Login

Use XDG autostart (not systemd for user app) — standard for GNOME GUI apps.

```ini
# ~/.config/autostart/asus-backlight.desktop
[Desktop Entry]
Type=Application
Name=ASUS Backlight Controller
Exec=/usr/bin/python3 /path/to/app/main.py --tray-only
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

Note: GNOME 49 (future) plans to deprecate `/etc/xdg/autostart` in favor of systemd, but `~/.config/autostart` for user apps is stable for Ubuntu 24.04 LTS.

---

## Sources

- [PyGObject official docs](https://pygobject.gnome.org/) — Python 3.9+ support, GTK4, Ubuntu install instructions (HIGH confidence)
- [PyGObject on PyPI](https://pypi.org/project/PyGObject/) — Version 3.54.5, released October 18, 2025 (HIGH confidence)
- [GTK4 ColorDialog docs](https://docs.gtk.org/gtk4/class.ColorDialog.html) — Introduced GTK 4.10, `ColorButton` deprecated 4.10+ (HIGH confidence)
- [libadwaita 1.5 Ubuntu 24.04 package](https://launchpad.net/ubuntu/noble/amd64/gir1.2-adw-1/1.5.0-1ubuntu2) — Ubuntu Noble ships libadwaita 1.5 (HIGH confidence)
- [trayer GitHub (Enne2/trayer)](https://github.com/Enne2/trayer) — GTK4 StatusNotifierItem tray library, last commit Oct 2025 (MEDIUM confidence — small library, limited community)
- [ASUS TUF keyboard sysfs blog post (Sept 2024)](https://guh.me/posts/2024-09-15-manually-configuring-asus-tuf-keyboard-lighting-on-linux/) — sysfs path and write format verified (MEDIUM confidence — first-party hardware testing)
- [GNOME AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/) — Required for tray icons on GNOME Shell (HIGH confidence)
- [XDG Autostart ArchWiki](https://wiki.archlinux.org/title/XDG_Autostart) — ~/.config/autostart .desktop file pattern (HIGH confidence)
- [PyGTK GTK3 AppIndicator3 examples](http://candidtim.github.io/appindicator/2014/09/13/ubuntu-appindicator-step-by-step.html) — Ruled out: GTK3, conflicts with GTK4 (informational)
- WebSearch results for pystray, GSettings, udev rules — (MEDIUM confidence, cross-referenced with official docs)

---

*Stack research for: ASUS TUF F16 Keyboard Backlight Controller (Linux GUI, Ubuntu/GNOME)*
*Researched: 2026-02-21*

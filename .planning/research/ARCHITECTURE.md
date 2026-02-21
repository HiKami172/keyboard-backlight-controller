# Architecture Research

**Domain:** Linux hardware control GUI application (keyboard backlight controller)
**Researched:** 2026-02-21
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      GUI Layer                               │
├──────────────────────┬──────────────────────────────────────┤
│  ┌────────────────┐  │  ┌───────────────────────────────┐   │
│  │  Main Window   │  │  │      System Tray Icon         │   │
│  │ (config UI)    │  │  │  (AppIndicator + popup menu)  │   │
│  └───────┬────────┘  │  └───────────────┬───────────────┘   │
│          │           │                  │                    │
├──────────┴───────────┴──────────────────┴────────────────── ┤
│                   Application Core                           │
├────────────────────┬─────────────────────────────────────── ┤
│  ┌──────────────┐  │  ┌────────────────┐  ┌─────────────┐   │
│  │Profile Manager│  │  │ Config Storage │  │Shortcut Mgr │   │
│  │(CRUD profiles)│  │  │(XDG ~/.config) │  │(keybindings)│   │
│  └──────┬───────┘  │  └────────────────┘  └─────────────┘   │
│         │          │                                         │
├─────────┴──────────┴────────────────────────────────────────┤
│                Hardware Abstraction Layer                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            BacklightController                        │   │
│  │  (validates inputs, formats sysfs command string,     │   │
│  │   writes to /sys/class/leds/asus::kbd_backlight/)     │   │
│  └─────────────────────────────┬────────────────────────┘   │
└────────────────────────────────┼────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────┐
│                    OS / Kernel Layer                          │
│  /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode            │
│  (permissions granted via udev rule, no sudo prompt)         │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Main Window | Full configuration UI: color pickers, mode selectors, preview, palette management | `Gtk.ApplicationWindow` with child widgets |
| System Tray Icon | Quick profile switching, show/hide main window | `AppIndicator3` (libayatana-appindicator) |
| Profile Manager | CRUD operations for named profiles, active profile tracking | Plain Python class, no external deps |
| Config Storage | Persist profiles to disk, load on startup, XDG path resolution | JSON file at `~/.config/kbd-backlight/profiles.json` |
| Shortcut Manager | Register keyboard shortcuts for profile cycling | GTK `ShortcutController` (in-app) or `keybinder` lib (global) |
| BacklightController | Format the sysfs write string, write to hardware, validate inputs | Python class wrapping `open(path).write(...)` |
| Autostart | Launch app on user login in system tray mode | XDG `.desktop` file at `~/.config/autostart/` |

## Recommended Project Structure

```
kbd_backlight/
├── __main__.py              # Entry point: parse args, create Gtk.Application
├── application.py           # Gtk.Application subclass, lifecycle, tray icon
├── hardware/
│   ├── __init__.py
│   └── backlight.py         # BacklightController: sysfs writes and validation
├── ui/
│   ├── __init__.py
│   ├── main_window.py       # Gtk.ApplicationWindow: full config UI
│   ├── tray.py              # AppIndicator3 system tray + popup menu
│   └── color_picker.py      # Custom color picker widget (gradient)
├── profiles/
│   ├── __init__.py
│   ├── manager.py           # ProfileManager: CRUD, active profile state
│   └── storage.py           # JSON serialization/deserialization to XDG path
├── shortcuts/
│   ├── __init__.py
│   └── handler.py           # Keyboard shortcut registration and dispatch
├── data/
│   └── palettes.py          # Built-in color palettes (ocean, sunset, etc.)
└── install/
    ├── 99-kbd-backlight.rules   # udev rule (install to /etc/udev/rules.d/)
    └── kbd-backlight.desktop    # Autostart file (install to ~/.config/autostart/)
```

### Structure Rationale

- **hardware/:** Isolates all sysfs interaction. No UI code touches the file system directly. This boundary makes testing possible without hardware.
- **ui/:** All GTK widgets. Never writes to hardware directly — always calls `BacklightController`.
- **profiles/:** Pure data concern. No GTK dependencies, no sysfs. Can be unit-tested in isolation.
- **shortcuts/:** Separate because shortcut registration differs significantly between in-app (GTK) and global (keybinder/X11) approaches — isolating it avoids coupling.
- **install/:** Non-Python artifacts that ship with the project. Keeping them grouped makes the installation step explicit.

## Architectural Patterns

### Pattern 1: Hardware Abstraction with Validation at the Boundary

**What:** All sysfs writes go through a single `BacklightController` class that validates inputs before writing. The UI never writes to `/sys/...` directly.

**When to use:** Always. This is the foundational boundary. The hardware interface is brittle — wrong values can be silently ignored or cause kernel module errors. Validation at the boundary catches these before they reach the kernel.

**Trade-offs:** One extra indirection. Benefit far outweighs cost: enables testing via a mock controller, centralizes error handling, and prevents the UI from needing to know the sysfs write format.

**Example:**
```python
# hardware/backlight.py
SYSFS_PATH = "/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode"

MODES = {
    "static": 0,
    "breathing": 1,
    "color_cycle": 2,
    "strobe": 3,
}

class BacklightController:
    def __init__(self, sysfs_path: str = SYSFS_PATH):
        self._path = sysfs_path

    def apply(self, mode: str, r: int, g: int, b: int, speed: int) -> None:
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        if not all(0 <= c <= 255 for c in (r, g, b)):
            raise ValueError("Color values must be 0-255")
        if speed not in (0, 1, 2):
            raise ValueError("Speed must be 0, 1, or 2")
        cmd = f"1 {MODES[mode]} {r} {g} {b} {speed}"
        with open(self._path, "w") as f:
            f.write(cmd)
```

### Pattern 2: Profile as Pure Data, Applied via Controller

**What:** A Profile is a plain dataclass (or dict) with no behavior. The Profile Manager stores/retrieves profiles. The UI passes a profile's values to the BacklightController to apply it.

**When to use:** Always. Keeps profiles serializable to JSON without custom serialization logic.

**Trade-offs:** None meaningful for this project's scale.

**Example:**
```python
# profiles/manager.py
from dataclasses import dataclass, asdict

@dataclass
class Profile:
    name: str
    mode: str         # "static" | "breathing" | "color_cycle" | "strobe"
    r: int
    g: int
    b: int
    speed: int        # 0 | 1 | 2

class ProfileManager:
    def __init__(self, storage):
        self._storage = storage
        self._profiles: dict[str, Profile] = {}
        self._active: str | None = None

    def load(self) -> None:
        self._profiles = self._storage.load()

    def save(self) -> None:
        self._storage.save(self._profiles)

    def add(self, profile: Profile) -> None:
        self._profiles[profile.name] = profile

    def get_active(self) -> Profile | None:
        return self._profiles.get(self._active)

    def set_active(self, name: str) -> None:
        if name not in self._profiles:
            raise KeyError(f"No profile: {name}")
        self._active = name
```

### Pattern 3: Live Preview via Immediate Hardware Write

**What:** Slider/picker changes in the UI call `BacklightController.apply()` immediately, so the keyboard reflects changes in real-time. There is no separate "preview" state — the hardware is the preview.

**When to use:** This pattern works because the hardware is local and writes are fast (< 5ms). Do not debounce too aggressively — 50-100ms is enough to avoid flooding the sysfs path while dragging sliders.

**Trade-offs:** Requires the permission solution (udev rule) to be in place before the live preview works. During development without the udev rule, the controller can be constructed with a mock path for testing.

## Data Flow

### Profile Apply Flow

```
User selects profile in tray menu
    |
    v
SystemTray.on_profile_selected(name)
    |
    v
ProfileManager.set_active(name)
    |
    v
Profile data (mode, r, g, b, speed) retrieved
    |
    v
BacklightController.apply(mode, r, g, b, speed)
    |
    v
sysfs write: "1 {mode} {r} {g} {b} {speed}"
    |
    v
/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode
```

### Live Preview Flow (slider drag in main window)

```
User drags color slider
    |
    v
UI widget emits 'value-changed' signal (debounced ~50ms)
    |
    v
MainWindow._on_color_changed(r, g, b)
    |
    v
BacklightController.apply(current_mode, r, g, b, current_speed)
    |
    v
Hardware reflects change immediately
```

### Startup / Auto-restore Flow

```
Application starts (launched via autostart .desktop or manually)
    |
    v
ProfileManager.load() reads ~/.config/kbd-backlight/profiles.json
    |
    v
Last-active profile identified (stored in config)
    |
    v
BacklightController.apply(...) restores last state
    |
    v
AppIndicator created, main window hidden
    |
    v
GTK main loop starts
```

### Permission Architecture

```
[Install Time]
udev rule → /etc/udev/rules.d/99-kbd-backlight.rules
    SUBSYSTEM=="leds", KERNEL=="asus::kbd_backlight",
    RUN+="/bin/chmod 0666 /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode"

[Runtime]
BacklightController (running as user) → open(sysfs_path, "w").write(cmd)
    No sudo, no polkit dialog, no privilege escalation required
```

## Scaling Considerations

This is a local single-user desktop application. Traditional web-app scaling doesn't apply. The relevant concerns are:

| Concern | Practical Reality | Approach |
|---------|-------------------|----------|
| Number of profiles | Dozens max | Flat JSON list is sufficient; no database needed |
| Write frequency | ~20/sec during slider drag | Debounce slider signals to ~50ms; sysfs writes are fast |
| Startup time | Should feel instant | Load JSON config at startup, no heavy imports at module level |
| Memory use | Irrelevant at this scale | PyGObject + Python baseline is ~30-50MB, acceptable |

## Anti-Patterns

### Anti-Pattern 1: Writing to sysfs Directly from UI Code

**What people do:** Put the `open("/sys/.../kbd_rgb_mode", "w").write(...)` call directly inside a GTK signal handler.

**Why it's wrong:** The hardware interface detail is now coupled to the UI. Cannot test the UI without hardware present. Cannot swap the sysfs path (e.g., for a mock in tests). Error handling is scattered across the widget tree.

**Do this instead:** Route all hardware writes through `BacklightController`. UI code calls `self.controller.apply(...)`.

### Anti-Pattern 2: Using polkit for Per-Write Authorization

**What people do:** Set up a polkit action that prompts the user for their password each time the app writes to the sysfs path.

**Why it's wrong:** A password dialog appears every time the user moves a color slider. The core value proposition — "no terminal commands, no password prompts" — is destroyed. polkit is appropriate for install-time setup actions, not per-write hardware access.

**Do this instead:** Install a udev rule at setup time that sets the sysfs file permissions to allow group write access. The user adds themselves to the group once; no further prompts are needed.

### Anti-Pattern 3: Storing Profiles in a Database (SQLite/etc.)

**What people do:** Reach for SQLite because "that's where data goes."

**Why it's wrong:** Profiles are simple structured data with no relational requirements. SQLite adds a dependency, complicates backup/inspection, and provides no benefit for a handful of named color configs.

**Do this instead:** Store profiles as a JSON file at `~/.config/kbd-backlight/profiles.json`. Human-readable, trivially backed up, no migration infrastructure needed.

### Anti-Pattern 4: Global Hotkeys via X11 XGrabKey in GTK4

**What people do:** Implement global keyboard shortcuts by calling X11's `XGrabKey` directly.

**Why it's wrong:** GTK4 is moving toward Wayland. X11 keygrabbing does not work on Wayland sessions. On GNOME with Wayland (the default on Ubuntu 24.04+), global hotkeys require a different mechanism (portal API or GNOME Shell extension).

**Do this instead:** Use GTK's built-in `ShortcutController` for in-application shortcuts (work when window is focused). For global shortcuts, use the `keybinder3` library if the user is on X11, or document a GNOME keyboard shortcut pointing to a CLI command as the fallback for Wayland. Flag this as a known limitation.

### Anti-Pattern 5: Running the Entire Application as Root

**What people do:** Launch the app with `sudo` or via a root systemd service to avoid dealing with permissions.

**Why it's wrong:** Running a GTK application as root is dangerous (security) and often broken (GNOME will refuse to launch GTK apps as root in some configurations). The system tray, D-Bus connections, and AppIndicator all depend on the user session.

**Do this instead:** Solve permissions with a udev rule so the application runs as the regular user.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Linux kernel (sysfs) | Direct file write via `open(..., 'w').write(...)` | Requires udev rule for non-root write access |
| udev (permission setup) | Static rule file installed to `/etc/udev/rules.d/` | One-time setup at install; runs before desktop login |
| GNOME Autostart | XDG `.desktop` file at `~/.config/autostart/` | Starts app in tray-only mode on login |
| AppIndicator / SNI | `gi.repository.AppIndicator3` via libayatana-appindicator | Requires GNOME Shell extension on Ubuntu 24.04+ (AppIndicator Support) |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| UI Window <-> ProfileManager | Direct method calls (same process) | Pass Profile dataclass objects; no serialization needed |
| ProfileManager <-> Storage | Direct method calls | Storage handles JSON encode/decode |
| UI Window <-> BacklightController | Direct method calls | Controller is injected at construction for testability |
| SystemTray <-> MainWindow | GTK signals or direct reference | Tray shows/hides window; shares same ProfileManager instance |
| SystemTray <-> BacklightController | Direct method calls | Tray applies profiles on menu selection |

## Suggested Build Order

Dependencies flow bottom-up. Build in this order to avoid integration blockers:

1. **udev rule + permission setup** — Enables hardware writes without sudo; all subsequent development depends on this working.
2. **BacklightController** — Core hardware abstraction. Can be developed and tested with a mock path before the udev rule is installed.
3. **Config Storage + Profile dataclass** — Pure Python, no GTK, no hardware. Write and test independently.
4. **ProfileManager** — Depends on Storage. No GTK. Test in isolation.
5. **Main Window (basic)** — GTK window with mode/color controls wired to BacklightController. Live preview works once controller is built.
6. **System Tray Icon** — Depends on ProfileManager (for menu items) and BacklightController (for applying profiles).
7. **Color picker / palette widgets** — UI refinement; MainWindow must exist first.
8. **Keyboard shortcuts** — Requires GTK application to be running; add after window is working.
9. **Autostart .desktop file** — Integration concern; add after the application runs correctly in tray mode.

## Sources

- ClevoKeyboardControl (reference implementation for keyboard backlight GUI architecture): https://github.com/anetczuk/ClevoKeyboardControl
- AsusTUFLinuxKeyboard (reference for ASUS-specific sysfs interface): https://github.com/llybin/AsusTUFLinuxKeyboard
- Manually configuring ASUS TUF keyboard lighting on Linux (sysfs path and permissions): https://guh.me/posts/2024-09-15-manually-configuring-asus-tuf-keyboard-lighting-on-linux/
- udev documentation (permission rules): https://www.freedesktop.org/software/systemd/man/latest/udev.html
- GTK4 ShortcutController (in-app keyboard shortcuts): https://docs.gtk.org/gtk4/class.Shortcut.html
- Ayatana AppIndicator (system tray, Ubuntu): https://github.com/AyatanaIndicators/libayatana-appindicator
- XDG Autostart Specification (login startup): https://specifications.freedesktop.org/autostart-spec/autostart-spec-latest.html
- GLib.get_user_config_dir (XDG config path via GLib): https://docs.gtk.org/glib/func.get_user_config_dir.html
- AppIndicator and KStatusNotifierItem Support extension (required on GNOME): https://extensions.gnome.org/extension/615/appindicator-support/

---
*Architecture research for: Linux keyboard backlight GUI controller (ASUS TUF F16, Ubuntu/GNOME)*
*Researched: 2026-02-21*

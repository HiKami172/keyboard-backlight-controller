# Project Research Summary

**Project:** ASUS TUF F16 Keyboard Backlight Controller
**Domain:** Linux desktop GUI application — hardware controller (sysfs-based LED control, GNOME/Ubuntu)
**Researched:** 2026-02-21
**Confidence:** MEDIUM

## Executive Summary

This is a single-machine personal Linux desktop application that replaces manual `tee` commands to the sysfs backlight interface with a GUI. The hardware (ASUS TUF F16) exposes a single sysfs file (`/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode`) that accepts a space-separated string controlling mode (static/breathing/color_cycle/strobe), RGB color, and speed. The entire value proposition is ergonomic: remove the need to type raw commands and persist configurations across boots. The recommended implementation uses Python 3 + GTK4 + libadwaita with PyGObject bindings, layered into four concerns: hardware I/O, profile data management, GUI, and system integration (tray + autostart).

The recommended architecture is a strict layer model: a `BacklightController` class owns all sysfs interaction and validates inputs; profile data is a plain dataclass serialized to JSON in `~/.config/`; the GTK4 GUI calls the controller through clean method boundaries and never touches the filesystem directly. The system tray (via libayatana-appindicator) is the daily-use surface, while the main window handles first-run setup and profile management. This structure makes hardware writes testable via dependency injection, keeps profiles trivially human-readable, and matches established patterns from comparable tools (OpenRGB, TUXEDO Control Center).

The two highest-risk areas are permissions and tray integration. Write access to the sysfs file requires a udev rule using explicit `RUN+chgrp/chmod` commands — the simpler `GROUP=`/`MODE=` approach is unreliable for sysfs attribute files. System tray icons are invisible on GNOME Shell by default because GNOME removed native tray support in version 3.26; the `gnome-shell-extension-appindicator` extension is a required dependency that users must install. Both issues are well-understood and have documented solutions, but both must be addressed in the very first phases before any other feature is built.

## Key Findings

### Recommended Stack

Python 3.12 (system-installed on Ubuntu 24.04) with PyGObject 3.54.5 + GTK4 + libadwaita 1.5 is the correct and only reasonable stack for a GNOME-native application on Ubuntu. PySide6/Qt is the only credible alternative but produces non-native GNOME UX and carries heavier dependencies. All deprecated GTK3 paths (`Gtk.StatusIcon`, `Gtk.ColorChooserWidget`, `gi.require_version("Gtk","3.0")`) must be avoided — GTK4 removed or deprecated all of them.

System tray requires the `libayatana-appindicator3` library (not the unmaintained original) combined with the `gnome-shell-extension-appindicator` GNOME extension. For GTK4 tray integration, the `trayer` library (StatusNotifierItem + DBusMenu via D-Bus) is the maintained option. Configuration storage is GSettings for application settings and JSON (via plain `json` stdlib) for named user profiles. The GTK4 `Gtk.ColorDialog` + `Gtk.ColorDialogButton` API is the correct color picker (the `ColorChooserWidget`/`ColorChooserDialog` APIs were deprecated in GTK 4.10).

**Core technologies:**
- Python 3.10+: Application language — system-installed on Ubuntu 24.04, no packaging overhead
- PyGObject 3.54.5: GTK4 bindings — the only official Python binding for GTK4; GObject Introspection at runtime
- GTK 4 (gir1.2-gtk-4.0): GUI toolkit — native on GNOME/Ubuntu, full widget set, hardware-accelerated rendering
- libadwaita 1.5: GNOME design system — `AdwApplication`, GNOME HIG compliance, required for `Gtk.ColorDialog`
- libayatana-appindicator3: System tray — StatusNotifierItem protocol, GNOME Shell compatible with extension
- GSettings / JSON: Configuration — GSettings for app prefs (typed, schema-validated), JSON for named profiles (human-readable, git-trackable)

### Expected Features

See [FEATURES.md](.planning/research/FEATURES.md) for full feature matrix and competitor analysis.

**Must have (table stakes):**
- All 4 hardware modes selectable (static, breathing, color_cycle, strobe) — any missing mode makes the app feel broken
- RGB color picker with GTK4 `Gtk.ColorDialog` — core GUI value proposition
- Speed control (3-stop: slow/medium/fast) — breathing and cycle modes are unusable without it
- Live preview — writes to hardware on change with ~100ms debounce; this is what every comparable tool does
- udev permission setup — without non-root write access, nothing else works; must guide the user through this
- Auto-restore on login — profiles must survive reboots via XDG autostart `.desktop` entry
- Named profiles (create/save/delete) — stored as JSON in `~/.config/kbd-backlight/`; required for tray switching
- System tray with profile quick-switch menu — the primary daily-use surface; requires named profiles to be useful
- Full config window — required for profile management and first-run setup

**Should have (competitive advantage):**
- Preset color palettes (6-8 named themes: Ocean, Sunset, Cyberpunk, etc.) — no competing tool offers this; low effort
- Per-profile color swatch in tray menu — visual identity for profiles; low effort polish
- Color harmony suggestions (complementary/analogous/triadic swatches) — novel feature, no competitor offers it
- Gradient two-color selector — color-picking aid for the hardware's single-RGB constraint

**Defer (v2+):**
- Keyboard shortcut profile switching — Wayland global hotkey restrictions make this unreliable; requires further research
- CLI interface (`kbd-backlight --profile Work`) — useful for scripting hooks; defer until GUI is stable
- Dim on screen lock / restore on unlock — D-Bus screen lock event listener; low priority automation

### Architecture Approach

The application is structured in four strict layers: GUI (GTK4 window + system tray), Application Core (ProfileManager, Config Storage), Hardware Abstraction Layer (`BacklightController`), and OS/Kernel (sysfs file). No UI code writes to sysfs directly; all hardware interaction routes through `BacklightController`, which validates inputs and formats the write string. Profiles are plain Python dataclasses serialized to JSON — no ORM, no SQLite, no custom serialization. The tray and main window share a single `ProfileManager` instance; the controller is injected at construction to enable mock-based testing without hardware.

**Major components:**
1. `BacklightController` (hardware/) — validates mode/color/speed inputs, formats sysfs write string, wraps `open(path).write()`; accepts `persist=False` parameter to distinguish live preview (cmd=0) from explicit save (cmd=1)
2. `ProfileManager` + `Storage` (profiles/) — CRUD for named profiles, active profile tracking, JSON serialization to `~/.config/kbd-backlight/profiles.json`
3. `MainWindow` (ui/) — GTK4 `Gtk.ApplicationWindow` with mode selector, color picker, speed control, palette browser; calls controller for live preview
4. `SystemTray` (ui/tray.py) — AppIndicator3 tray icon with popup menu listing profiles; shows/hides main window; shares ProfileManager and BacklightController instances
5. `Application` (application.py) — `Gtk.Application` subclass managing lifecycle, startup restore, and component wiring

**Recommended build order (bottom-up to avoid integration blockers):**
1. udev rule + permission setup
2. BacklightController (mock-path testable)
3. Config Storage + Profile dataclass
4. ProfileManager
5. Main Window (basic mode/color controls + live preview)
6. System Tray
7. Color picker polish + palette widgets
8. Keyboard shortcuts (if pursued)
9. Autostart .desktop file

### Critical Pitfalls

See [PITFALLS.md](.planning/research/PITFALLS.md) for full pitfall analysis with recovery strategies.

1. **udev rule with GROUP/MODE fails on sysfs** — The `GROUP=`/`MODE=` approach does not reliably set permissions on sysfs attribute files. Use `RUN+="/bin/chgrp plugdev /sys/class/leds/%k/kbd_rgb_mode"` and `RUN+="/bin/chmod g+w ..."` instead. Must be solved in Phase 1 before anything else is built.

2. **Hardcoded sysfs path breaks after kernel update** — The asus-wmi driver renames `asus::kbd_backlight` to `asus::kbd_backlight_1` on name collisions (documented Red Hat BZ #1665505). Use glob discovery (`asus::kbd_backlight*`) at startup instead of hardcoding the path. Fail fast with a user-facing error, not a Python traceback.

3. **System tray invisible on GNOME without extension** — GNOME Shell removed native tray support in 3.26. AppIndicator3 silently produces no icon without the `gnome-shell-extension-appindicator` extension. Must document and check for this dependency; show a first-run dialog if the extension is missing.

4. **Blocking sysfs write on GTK main thread causes stutter** — Signal handlers run on the main thread; sysfs writes involve kernel/WMI/ACPI/EC round-trips that can take 50-500ms. Implement 100ms debounce via `GLib.timeout_add`; use `GLib.idle_add` for background-thread UI callbacks per PyGObject official threading guidance.

5. **cmd=1 used for live preview wears BIOS flash** — The write format's `cmd` field: cmd=0 = "set temporarily," cmd=1 = "save permanently to BIOS." Using cmd=1 on every color slider drag writes to BIOS firmware memory thousands of times per session. Live preview must always use cmd=0; `BacklightController.apply()` must accept a `persist=False` parameter from day one.

## Implications for Roadmap

Based on combined research, the architecture's bottom-up build order maps directly to phases. All feature and architecture dependencies converge on the same phase ordering.

### Phase 1: Permissions and Hardware Foundation

**Rationale:** Everything depends on being able to write to sysfs without sudo. The udev rule and `BacklightController` are the foundation every subsequent phase requires. Solving this first eliminates the most common failure mode in this domain and validates the hardware interface works at all.

**Delivers:** Non-root write access to `kbd_rgb_mode`; a validated `BacklightController` with glob-based path discovery, input validation, and a `persist=False` parameter; a mock-path test harness for development without hardware in the loop.

**Addresses:** udev permission setup, all 4 hardware modes, speed control, sysfs write format

**Avoids:** Pitfall 1 (udev GROUP/MODE failure), Pitfall 2 (hardcoded path rename), Pitfall 5 (BIOS wear from cmd=1)

**Research flag:** Standard patterns — udev rule format and sysfs write interface are well-documented. No additional research-phase needed.

### Phase 2: Profile Data Layer

**Rationale:** Profile data is the shared state that both the main window and tray depend on. Building it before any UI means the GUI phase can focus on widget wiring rather than data design. Pure Python — no GTK, no hardware — makes this independently testable.

**Delivers:** `Profile` dataclass, `ProfileManager` (CRUD + active tracking), JSON storage to XDG config dir; deterministic load/save behavior

**Addresses:** Named profiles, auto-restore on login (profile persistence half), profile data schema

**Avoids:** Pitfall of storing profiles in wrong location (`~/.config/` not `/etc/`), profile name collision (validate uniqueness on save)

**Research flag:** Standard patterns — Python dataclasses + json stdlib are well-documented. No additional research-phase needed.

### Phase 3: Main Window and Live Preview

**Rationale:** The main window is the configuration surface and depends on both the hardware layer (Phase 1) and profile data layer (Phase 2). Live preview — the core UX differentiator — requires all three concerns working together. Building the window third means it immediately functions end-to-end.

**Delivers:** GTK4 `Gtk.ApplicationWindow` with mode selector, `Gtk.ColorDialog` color picker, speed control, live preview (debounced sysfs writes), profile save/load UI

**Addresses:** RGB color picker, live preview, speed control, full config window, preset color palettes

**Avoids:** Pitfall 4 (blocking GTK thread — implement debounce from the start), deprecated `ColorChooserWidget` (use `Gtk.ColorDialog`)

**Research flag:** Standard patterns for GTK4 widget wiring. Custom `Gtk.DrawingArea` gradient picker (v1.x feature) may need a brief research pass on Cairo gradient rendering API.

### Phase 4: System Tray and Autostart

**Rationale:** The tray is the daily-use surface but depends on named profiles (Phase 2) to populate its menu. Autostart depends on the tray working correctly (so the app launches silently into the tray on login). These concerns are grouped because they share the same integration risk (GNOME extension dependency) and together complete the background-daemon behavior of the app.

**Delivers:** AppIndicator3 system tray with profile quick-switch menu, per-profile color swatches in menu items, XDG autostart `.desktop` file (tray-only mode on boot), profile-restore-on-launch behavior

**Addresses:** System tray with profile menu, auto-restore on login, per-profile color swatch in tray

**Avoids:** Pitfall 3 (invisible tray — must check for GNOME extension and show first-run dialog), app-opens-window-on-autostart (use `--tray-only` flag), close-window-exits-app (intercept `delete-event`, route to `hide()`)

**Research flag:** Needs a research pass on libayatana-appindicator3 API for GTK4, specifically whether `trayer` library or direct `gi.repository.AppIndicator3` is the correct import path for Ubuntu 24.04. The GNOME extension detection mechanism also warrants a code-level research spike.

### Phase 5: Polish and Differentiators

**Rationale:** Once the end-to-end flow works (permissions → profiles → main window → tray → autostart), this phase adds the features that make the tool pleasant rather than merely functional. All items here are independently addable; none block each other.

**Delivers:** Color harmony suggestions (HSV math, swatch panel), gradient two-color selector (custom `Gtk.DrawingArea` + Cairo), per-profile tray swatches (if not completed in Phase 4), first-run setup wizard for udev rule

**Addresses:** Color harmony suggestions, gradient selector, UX polish, user-facing error handling for missing asus-wmi module

**Avoids:** Anti-features (per-key RGB, multi-model support, cloud sync — explicitly out of scope)

**Research flag:** Color harmony math (HSV/colorsys) is stdlib — no research needed. Custom `Gtk.DrawingArea` + Cairo for gradient picker may benefit from a GTK4 drawing API reference pass.

### Phase Ordering Rationale

- **Bottom-up dependency order:** Hardware access (P1) → data layer (P2) → GUI consuming both (P3) → system integration consuming GUI (P4) → polish (P5). Each phase's outputs are inputs to the next.
- **Risk-first ordering:** The two highest-risk items (udev permissions, tray GNOME extension) are isolated into their own phases (P1, P4) so they can be validated independently without invalidating other work.
- **Test isolation preserved:** The hard boundary between `BacklightController` (P1) and the GUI (P3) means development can continue with a mock controller even before the udev rule is applied on a given machine.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (System Tray):** The libayatana-appindicator3 GTK4 integration and GNOME extension detection mechanism are niche enough to warrant a targeted code-level research spike before implementation begins. The `trayer` library (StatusNotifierItem via D-Bus) vs. direct AppIndicator3 GObject introspection binding choice needs confirmation on Ubuntu 24.04.
- **Phase 5 (Gradient Picker, if pursued):** Custom `Gtk.DrawingArea` + Cairo gradient rendering is well-documented in general but GTK4-specific examples are sparse. A brief research pass on GTK4 custom drawing and `Gtk.GestureClick`/`Gtk.GestureDrag` APIs would reduce uncertainty.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Permissions + Hardware):** udev rule format and sysfs write interface are kernel-documented and community-verified. Pattern is clear.
- **Phase 2 (Profile Data):** Python dataclasses + json stdlib; XDG paths via GLib. Entirely standard patterns.
- **Phase 3 (Main Window):** GTK4 + PyGObject widget wiring with `Gtk.ColorDialog` is official-docs-documented. Standard.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyGObject + GTK4 + libadwaita is the only correct choice; versions verified against Ubuntu 24.04 packages and PyPI. Only weak spot is `trayer` (small library, MEDIUM confidence). |
| Features | MEDIUM | Hardware mode capabilities verified against sysfs docs and multiple 2024 blog posts. GUI feature norms drawn from OpenRGB, TUXEDO CC, asusctl. Competitor analysis is solid; novel features (color harmony) have no comparables to validate against. |
| Architecture | MEDIUM | Layer model and component boundaries are well-reasoned and match patterns in reference implementations (ClevoKeyboardControl, AsusTUFLinuxKeyboard). The specific AppIndicator3-in-GTK4 wiring is the area of lowest certainty. |
| Pitfalls | MEDIUM-HIGH | Core pitfalls (udev sysfs permission model, GNOME tray, GTK main thread) are verified via kernel docs, PyGObject official threading guide, GNOME Discourse, and Arch wiki. The BIOS wear pitfall is MEDIUM confidence (patch series docs describe cmd=1 as "save permanently" but real-world wear rate is unquantified). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **trayer vs. direct AppIndicator3 binding:** Research confirmed StatusNotifierItem is the right protocol; `trayer` (Python library) is the named option but is a small library with limited community signal. During Phase 4 planning, validate that `gi.repository.AppIndicator3` from `libayatana-appindicator3` is directly importable in GTK4 context on Ubuntu 24.04, or confirm `trayer` is required.
- **sysfs path on specific hardware unit:** The glob pattern `asus::kbd_backlight*` is the documented workaround for the rename issue, but the exact sysfs path on this specific machine has not been confirmed in the research files. The very first Phase 1 task should be to `ls /sys/class/leds/asus*` on the actual hardware.
- **Wayland global hotkeys (deferred feature):** The research is clear that X11 keygrabbing is the wrong approach, but the XDG Desktop Portal Global Shortcuts API (GNOME 45+) as the Wayland-correct alternative was identified but not researched in depth. This gap is acceptable since keyboard shortcut switching is deferred to v1.x.
- **cmd=0 vs cmd=1 real-world behavior:** The research notes cmd=0 as "set temporarily" and cmd=1 as "save permanently." The practical behavior (does cmd=0 survive a suspend/resume cycle? does it reset on logout?) needs to be tested on hardware in Phase 1 to determine whether auto-restore-on-launch is sufficient or whether cmd=1 at profile-save time is also needed.

## Sources

### Primary (HIGH confidence)
- PyGObject official docs (https://pygobject.gnome.org/) — Python 3.9+ support, GTK4, Ubuntu install
- GTK4 ColorDialog docs (https://docs.gtk.org/gtk4/class.ColorDialog.html) — deprecation of ColorChooserWidget in GTK 4.10
- libadwaita 1.5 Ubuntu 24.04 package (Launchpad) — version confirmation for Noble
- PyGObject threading guide (https://pygobject.gnome.org/guide/threading.html) — GLib.idle_add() pattern for worker threads
- GNOME AppIndicator extension (https://extensions.gnome.org/extension/615/appindicator-support/) — required for GNOME tray
- Kernel LED class documentation (https://docs.kernel.org/leds/leds-class.html)
- XDG Autostart specification (https://specifications.freedesktop.org/autostart-spec/autostart-spec-latest.html)

### Secondary (MEDIUM confidence)
- ASUS TUF keyboard sysfs blog post (https://guh.me/posts/2024-09-15-manually-configuring-asus-tuf-keyboard-lighting-on-linux/) — sysfs path and write format; 2024, matches PROJECT.md
- asus-wmi TUF RGB LWN article (https://lwn.net/Articles/903564/) — cmd=0/cmd=1 distinction from patch series
- GNOME Discourse — system tray GTK4 discussion — StatusNotifierItem protocol confirmation
- Arch Linux udev backlight forum (https://bbs.archlinux.org/viewtopic.php?id=262630) — GROUP/MODE vs RUN+chmod failure analysis
- Arch Linux Backlight wiki (https://wiki.archlinux.org/title/Backlight) — udev permission patterns
- trayer GitHub (https://github.com/Enne2/trayer) — GTK4 StatusNotifierItem tray library, last commit Oct 2025
- Red Hat BZ #1665505 — asus::kbd_backlight_1 rename behavior documented

### Tertiary (LOW confidence)
- AsusTUFBacklitColorChanger (https://github.com/oshin94/AsusTUFBacklitColorChanger) — minimal docs, feature comparison only
- Aurora (https://github.com/legacyO7/Aurora) — minimal docs, feature comparison only

---
*Research completed: 2026-02-21*
*Ready for roadmap: yes*

# Requirements: ASUS TUF F16 Keyboard Backlight Controller

**Defined:** 2026-02-21
**Core Value:** User can visually configure and switch keyboard backlight modes without touching the terminal — and the setting persists across reboots.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Permissions

- [ ] **PERM-01**: App sets up udev rule granting user write access to kbd_rgb_mode sysfs file without sudo
- [ ] **PERM-02**: App discovers sysfs path dynamically via glob (`asus::kbd_backlight*`) — not hardcoded

### Hardware Control

- [ ] **CTRL-01**: User can select any of the 4 hardware modes (static, breathing, color cycle, strobe)
- [ ] **CTRL-02**: User can pick any RGB color via color picker dialog
- [ ] **CTRL-03**: User can set animation speed (slow, medium, fast) for breathing/cycle/strobe modes
- [ ] **CTRL-04**: Changes apply to keyboard in real-time as user adjusts controls (debounced ~100ms live preview)
- [ ] **CTRL-05**: Live preview uses cmd=0 (temporary); explicit save uses cmd=1 (persist to BIOS)

### Profiles

- [ ] **PROF-01**: User can create named profiles with mode, color, and speed settings
- [ ] **PROF-02**: User can save, rename, and delete profiles
- [ ] **PROF-03**: Profiles stored as JSON in ~/.config/kbd-backlight/
- [ ] **PROF-04**: Last used profile auto-restores on app launch

### System Integration

- [ ] **TRAY-01**: System tray icon appears with right-click menu listing all profiles
- [ ] **TRAY-02**: User can switch profiles from tray menu with one click
- [ ] **TRAY-03**: Each profile shows a color swatch in the tray menu
- [ ] **TRAY-04**: App launches into tray-only mode on login via XDG autostart .desktop file
- [ ] **TRAY-05**: Closing the main window hides to tray instead of quitting

### Color Tools

- [ ] **COLR-01**: User can apply preset color palettes (6-8 named themes: Ocean, Sunset, Cyberpunk, etc.)
- [ ] **COLR-02**: When user picks a color, app suggests complementary, analogous, and triadic harmony colors
- [ ] **COLR-03**: User can pick two colors and select a gradient midpoint as the keyboard color

### Keyboard Shortcuts

- [ ] **KEYS-01**: User can switch between profiles via keyboard shortcuts
- [ ] **KEYS-02**: Shortcut implementation works on Wayland (via GNOME custom shortcuts + CLI flag if needed)

### Main Window

- [ ] **WIND-01**: Full standalone GTK4/libadwaita window for all configuration
- [ ] **WIND-02**: Tray icon click opens/shows the main window

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### CLI Interface

- **CLI-01**: CLI mode for scripting (`kbd-backlight --profile Work`)
- **CLI-02**: Export/import profiles as JSON files

### Automation

- **AUTO-01**: Dim keyboard on screen lock, restore on unlock (D-Bus listener)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom animation sequences / software-driven effects | Hardware only supports 4 fixed modes; rapid sysfs writes cause kernel errors |
| Per-key RGB lighting | TUF F16 hardware accepts single global RGB value — no per-key interface |
| Multi-laptop/model support | Personal tool for one machine; adds abstraction complexity for zero benefit |
| GNOME Shell extension | Requires JavaScript, separate repo, breaks on GNOME updates; tray is more stable |
| Cloud sync of profiles | Single machine; JSON in ~/.config/ is sufficient |
| Packaging (.deb, Flatpak) | Personal daily driver; install from source |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PERM-01 | Phase 1: Permissions and Hardware Foundation | Pending |
| PERM-02 | Phase 1: Permissions and Hardware Foundation | Pending |
| CTRL-01 | Phase 1: Permissions and Hardware Foundation | Pending |
| CTRL-02 | Phase 1: Permissions and Hardware Foundation | Pending |
| CTRL-03 | Phase 1: Permissions and Hardware Foundation | Pending |
| CTRL-04 | Phase 1: Permissions and Hardware Foundation | Pending |
| CTRL-05 | Phase 1: Permissions and Hardware Foundation | Pending |
| PROF-01 | Phase 2: Profile Data Layer | Pending |
| PROF-02 | Phase 2: Profile Data Layer | Pending |
| PROF-03 | Phase 2: Profile Data Layer | Pending |
| PROF-04 | Phase 2: Profile Data Layer | Pending |
| WIND-01 | Phase 3: Main Window and Live Preview | Pending |
| WIND-02 | Phase 3: Main Window and Live Preview | Pending |
| COLR-01 | Phase 3: Main Window and Live Preview | Pending |
| TRAY-01 | Phase 4: System Tray and Autostart | Pending |
| TRAY-02 | Phase 4: System Tray and Autostart | Pending |
| TRAY-03 | Phase 4: System Tray and Autostart | Pending |
| TRAY-04 | Phase 4: System Tray and Autostart | Pending |
| TRAY-05 | Phase 4: System Tray and Autostart | Pending |
| COLR-02 | Phase 5: Color Tools and Keyboard Shortcuts | Pending |
| COLR-03 | Phase 5: Color Tools and Keyboard Shortcuts | Pending |
| KEYS-01 | Phase 5: Color Tools and Keyboard Shortcuts | Pending |
| KEYS-02 | Phase 5: Color Tools and Keyboard Shortcuts | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after roadmap creation — traceability phase names added*

# Roadmap: ASUS TUF F16 Keyboard Backlight Controller

## Overview

Five phases build bottom-up from hardware access to daily-use polish. Phase 1 solves the foundational blocker (sysfs permissions + validated hardware writes) before any GUI exists. Phase 2 builds the profile data layer in pure Python so both the window and tray can share it. Phase 3 wires the main window with live preview — the core UX differentiator. Phase 4 adds the system tray and autostart, completing the background-daemon behavior. Phase 5 adds the color tools (palettes, harmony, gradient) and keyboard shortcuts that make the tool pleasant rather than merely functional.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Permissions and Hardware Foundation** - udev rule + BacklightController with glob path discovery and validated sysfs writes
- [x] **Phase 2: Profile Data Layer** - Profile dataclass, ProfileManager CRUD, and JSON storage — no GTK dependency (completed 2026-02-21)
- [x] **Phase 3: Main Window and Live Preview** - GTK4/libadwaita window with mode selector, color picker, speed control, and debounced live preview (completed 2026-02-22)
- [x] **Phase 4: System Tray and Autostart** - AppIndicator3 tray with profile menu, XDG autostart, and tray-only launch mode (completed 2026-02-23)
- [ ] **Phase 4.1: Profile Gap Closure** - Fix PROF-04 autostart restore and PROF-02 rename UI (gap closure from v1.0 audit)
- [ ] **Phase 5: Color Tools and Keyboard Shortcuts** - Preset palettes, color harmony suggestions, gradient selector, and Wayland-compatible profile shortcuts

## Phase Details

### Phase 1: Permissions and Hardware Foundation
**Goal**: The user can write any valid backlight command to the hardware without a password prompt, and the app can discover the sysfs path dynamically
**Depends on**: Nothing (first phase)
**Requirements**: PERM-01, PERM-02, CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05
**Success Criteria** (what must be TRUE):
  1. User can run the app without sudo — writes to kbd_rgb_mode succeed without a password dialog
  2. App discovers the sysfs path via glob at startup and fails fast with a readable error if the path is missing (not a Python traceback)
  3. All 4 hardware modes (static, breathing, color cycle, strobe) can be commanded from the app with any valid RGB color and speed
  4. Live preview writes use cmd=0 (temporary); explicit save uses cmd=1 (persist to BIOS) — never cmd=1 during slider drag
  5. BacklightController can be tested with a mock sysfs path (no hardware required for development)
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Project skeleton + udev rule + install script
- [ ] 01-02-PLAN.md — BacklightController implementation + unit tests

### Phase 2: Profile Data Layer
**Goal**: Named profiles can be created, saved, loaded, and deleted as JSON on disk — with no GUI or hardware dependency
**Depends on**: Phase 1
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04
**Success Criteria** (what must be TRUE):
  1. User can create a named profile with mode, color, and speed settings and it persists to disk
  2. User can rename and delete profiles; changes reflect in the JSON file immediately
  3. Profiles are stored as human-readable JSON in ~/.config/kbd-backlight/ — readable and editable by hand
  4. On app launch the last used profile is automatically restored and applied to the keyboard
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Profile dataclass with __post_init__ validation and unit tests (TDD)
- [ ] 02-02-PLAN.md — ProfileManager CRUD with atomic JSON storage and integration tests (TDD)

### Phase 3: Main Window and Live Preview
**Goal**: The user has a full GTK4 window where they can configure any backlight setting and see it applied to the keyboard in real time
**Depends on**: Phase 2
**Requirements**: WIND-01, WIND-02, COLR-01
**Success Criteria** (what must be TRUE):
  1. User can open a standalone window and select any of the 4 hardware modes from a control in the window
  2. User can pick any RGB color via the GTK4 color picker dialog and it applies to the keyboard within ~100ms
  3. User can set animation speed (slow/medium/fast) for modes that support it
  4. User can apply any of the 6-8 preset color palettes and the keyboard changes immediately
  5. User can load and save profiles from within the main window without opening a terminal
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — GTK4 application scaffold: ui/ package, Application class, main.py entry point
- [ ] 03-02-PLAN.md — MainWindow: mode/color/speed controls + debounced live preview + profile load/save/delete
- [ ] 03-03-PLAN.md — Color palette presets (8 swatches) + visual verification checkpoint

### Phase 4: System Tray and Autostart
**Goal**: The app lives in the system tray and switches profiles with one click — and launches automatically into tray-only mode on login
**Depends on**: Phase 3
**Requirements**: TRAY-01, TRAY-02, TRAY-03, TRAY-04, TRAY-05
**Success Criteria** (what must be TRUE):
  1. A system tray icon appears in GNOME; right-clicking it shows a menu listing all saved profiles
  2. User can switch profiles from the tray menu with one click and the keyboard changes immediately
  3. Each profile entry in the tray menu shows a color swatch for visual identification
  4. App launches automatically on login in tray-only mode (no window opened) via XDG autostart
  5. Closing the main window hides it to the tray rather than quitting the app; clicking the tray icon restores it
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — GTK3 tray subprocess (tray.py): AyatanaAppIndicator3 indicator, profile menu with color swatches, stdin/stdout JSON IPC
- [ ] 04-02-PLAN.md — Application IPC wiring: tray subprocess launch, hold(), _apply_profile_by_name(), notify_tray_refresh(); MainWindow save/delete hooks + load_profile_from_tray()
- [ ] 04-03-PLAN.md — XDG autostart install script + end-to-end visual verification checkpoint

### Phase 4.1: Profile Gap Closure
**Goal**: Close the two v1.0 audit gaps: restore last profile on autostart (PROF-04) and expose rename UI in MainWindow (PROF-02)
**Depends on**: Phase 4
**Requirements**: PROF-02, PROF-04
**Gap Closure**: Closes gaps from v1.0 audit (GAP-1, GAP-2)
**Success Criteria** (what must be TRUE):
  1. Launching with `--tray-only` via XDG autostart applies the last saved profile to the keyboard at login
  2. User can rename any profile from within the MainWindow profile list without deleting and re-creating it
  3. `_restore_last_profile()` runs on every first activation regardless of `_tray_only` flag
  4. Rename action is wired to `manager.rename_profile()` and reflected immediately in UI and JSON
**Plans**: 2 plans

Plans:
- [ ] 04.1-01-PLAN.md — Fix PROF-04: move _restore_last_profile() before _tray_only guard in application.py
- [ ] 04.1-02-PLAN.md — Fix PROF-02: add Rename UI row + dialog + handler to MainWindow window.py

### Phase 5: Color Tools and Keyboard Shortcuts
**Goal**: The color-picking experience is enhanced with harmony suggestions and gradient selection, and profiles are switchable via keyboard shortcuts
**Depends on**: Phase 4
**Requirements**: COLR-02, COLR-03, KEYS-01, KEYS-02
**Success Criteria** (what must be TRUE):
  1. When the user picks a color, the app displays complementary, analogous, and triadic harmony swatches that can be applied with one click
  2. User can pick two colors and select any gradient midpoint between them as the keyboard color
  3. User can switch between saved profiles using a keyboard shortcut without opening the app window
  4. Keyboard shortcut switching works on Wayland (does not rely on X11 keygrabbing)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Permissions and Hardware Foundation | 1/2 | In Progress|  |
| 2. Profile Data Layer | 2/2 | Complete   | 2026-02-21 |
| 3. Main Window and Live Preview | 3/3 | Complete   | 2026-02-22 |
| 4. System Tray and Autostart | 3/3 | Complete   | 2026-02-23 |
| 4.1. Profile Gap Closure | 0/TBD | Not started | - |
| 5. Color Tools and Keyboard Shortcuts | 0/TBD | Not started | - |

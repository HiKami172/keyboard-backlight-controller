# Feature Research

**Domain:** Linux keyboard backlight GUI controller (ASUS TUF F16)
**Researched:** 2026-02-21
**Confidence:** MEDIUM — Hardware mode capabilities verified against sysfs docs and multiple blog posts; GUI feature norms drawn from OpenRGB, TUXEDO Control Center, asusctl, and similar Linux hardware GUI tools.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| All hardware modes selectable (static, breathing, color cycle, strobe) | Hardware supports exactly 4 modes; any GUI that omits one is immediately broken | LOW | Write format: `"1 [mode] [R] [G] [B] [speed]"` — mode values 0-3 |
| RGB color picker | No point in a GUI if you still have to pick RGB manually | LOW | GTK4 provides `Gtk.ColorChooserWidget` out of the box; includes hex + RGB input, palette memory |
| Speed control (slow/medium/fast) | Breathing and cycle modes are useless without speed adjustment | LOW | Only 3 values (0, 1, 2) — a radio group or slider with 3 stops is sufficient |
| Live preview (changes apply immediately) | Every comparable tool (OpenRGB, TUXEDO CC) applies changes in real-time; a "save then apply" model feels broken | MEDIUM | Write to sysfs on every UI change; debounce rapid slider drags ~150ms to avoid write thrashing |
| Permission handling (no sudo prompt) | A GUI that pops a password dialog on every color change is unusable; this is the core UX problem the tool solves | MEDIUM | udev rule granting write access to `asus::kbd_backlight` sysfs path to `video` or custom group; one-time setup |
| Auto-restore last setting on login/boot | systemd-backlight does this for brightness natively; users expect color/mode to also persist | MEDIUM | Write to config file on change; read and reapply via systemd `--user` service or GNOME autostart `.desktop` entry |
| Named profiles (save/load configurations) | Multiple comparable tools offer this (OpenRGB `.orp` files, TUXEDO CC profiles, KeyRGB profile system); users with "Gaming," "Work," "Night" use cases need it | MEDIUM | JSON or INI config files in `~/.config/kbd-backlight/`; profile = mode + color + speed |
| Full configuration window | Needed for initial setup and profile management; tray alone is insufficient for first-run experience | LOW | Standard GTK4 window with mode tabs/sections |
| System tray icon with profile menu | Users want quick switching without opening the full window; this is the daily-use surface | MEDIUM | `libayatana-appindicator` or GLib status icon; right-click menu listing profiles |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Color harmony suggestions | When user picks a primary color, show complementary, analogous, and triadic swatches as quick picks — reduces aesthetic trial-and-error | MEDIUM | No built-in GTK support; implement with HSV math (colorsys stdlib). Show swatches in a small palette panel beside the color picker. Confidence: LOW — no competing Linux keyboard tool offers this; it's a novel feature borrowed from design tools |
| Preset color palettes | Named aesthetic groups (Ocean, Sunset, Cyberpunk, Forest) give non-technical users a starting point | LOW | Hard-coded list of 6-10 palettes, each a named color + mode combo; displayed as clickable swatches |
| Gradient selector between two colors | Pick start and end colors; app picks an intermediate color as the hardware RGB value (hardware only supports one RGB at a time) | MEDIUM | A two-stop gradient UI that computes a midpoint or lets user drag a slider; useful for "warm white" style picking. Note: hardware limitation means true gradient is not possible — this is a color-picking aid, not a rendering feature |
| Keyboard shortcut profile switching | Toggle profiles from anywhere without even opening the tray | HIGH | Requires global hotkey daemon (e.g., `keybinder3` or `xdg-open` via custom keybindings); GNOME custom shortcuts can call a CLI mode. Hard because Wayland global hotkeys are restricted — flag as needing further research |
| Per-profile color preview swatch in tray menu | Tray menu items show a colored dot matching each profile's color — instant visual recognition | LOW | GTK menu items support custom icons; render a small colored circle as a `Gtk.Image` |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Custom animation sequences / software-driven effects | Users want "rainbow wave" or "breathing between two colors" | Hardware only supports 4 fixed modes; writing to sysfs at high frequency (>10Hz) causes kernel errors, missed writes, or system instability. Would require a background daemon constantly writing to sysfs. | Expose the 4 hardware modes with their native speed control. Document hardware limitations clearly in the UI (e.g., tooltip: "Hardware supports 3 speeds only") |
| Per-key RGB lighting | Power users want individual key colors | TUF F16's `kbd_rgb_mode` accepts a single global RGB value — there is no per-key sysfs interface on this hardware. Building fake per-key UI would be misleading. | Explicitly scope to "global keyboard color" in UI; label clearly |
| Multi-laptop/model support | Other Linux keyboard tools (Aurora, asusctl) support multiple ASUS models | Different ASUS models have different sysfs paths, mode sets, and command formats. Abstraction layer required, adds significant complexity for zero personal benefit. | Hard-code TUF F16 paths; add a `--sysfs-path` flag for power users if needed later |
| GNOME Shell extension integration | Feels native; appears in Quick Settings | GNOME extensions require JavaScript, separate repo, GNOME version pinning, and break on every major GNOME release. Fragile for a personal daily driver. | System tray via `libayatana-appindicator` is stable and works on GNOME without extension infrastructure |
| Cloud sync of profiles | Sync profiles across machines | Only one machine (personal tool); adds infrastructure complexity, account management, privacy surface | Use plaintext JSON in `~/.config/` — user can git-track or sync manually if desired |
| Packaging (.deb, Flatpak, AppImage) | Makes it shareable | Explicitly out of scope — personal daily driver. Packaging adds maintenance burden without benefit. | Install from source with a Makefile or install script |

---

## Feature Dependencies

```
[udev permission rule]
    └──required by──> [Live preview]
    └──required by──> [Auto-restore on boot]
    └──required by──> [System tray profile switching]

[Named profiles]
    └──required by──> [System tray profile menu]
    └──required by──> [Keyboard shortcut switching]
    └──enhances──> [Auto-restore on boot]

[Color picker]
    └──enhances──> [Color harmony suggestions]
    └──enhances──> [Gradient selector]
    └──enhances──> [Preset palettes]

[Full config window]
    └──required by──> [Profile create/edit/delete]
    └──required by──> [Preset palette selection]
    └──required by──> [Color harmony suggestions]

[System tray]
    └──requires──> [Named profiles] (something to switch between)
    └──requires──> [Auto-restore] (tray app must be running at login)
```

### Dependency Notes

- **udev rule required by live preview:** Without write permission to sysfs, no real-time feedback is possible. Must be installed first or the app must detect and guide setup.
- **Named profiles required by system tray:** A tray menu without profiles is just an on/off toggle — not worth building tray without profiles.
- **Auto-restore requires app to run at login:** Either a systemd --user service that reapplies the last profile on boot, or a `.desktop` autostart entry that launches the tray app (which then restores on launch). These are two distinct strategies.
- **Keyboard shortcut switching:** Depends on both named profiles and a working CLI interface (`kbd-backlight --profile Gaming`). Global hotkeys on Wayland are not reliably achievable without `xdg-desktop-portal` or GNOME-specific APIs — defer to v1.x.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to replace the `tee` command workflow.

- [ ] udev rule installer / setup guide — without this nothing works without sudo
- [ ] All 4 hardware modes selectable in UI (static, breathing, color cycle, strobe)
- [ ] RGB color picker (GTK native `ColorChooserWidget`)
- [ ] Speed control (3-position: slow / medium / fast)
- [ ] Live preview — writes to sysfs on change with debounce
- [ ] Named profiles — create, save, delete; stored as JSON in `~/.config/kbd-backlight/`
- [ ] Auto-restore last profile on launch (enables boot persistence via autostart)
- [ ] System tray icon with profile quick-switch menu
- [ ] Full config window for profile management
- [ ] Preset color palettes (6-8 named palettes as starting points)

### Add After Validation (v1.x)

Features to add once core is working and permissions/autostart are stable.

- [ ] Color harmony suggestions — add once color picker UX is proven; needs HSV math module
- [ ] Gradient two-color selector — add after basic color picker is well-used
- [ ] Per-profile color swatch in tray menu — low effort, polish pass
- [ ] Keyboard shortcut profile switching — research Wayland global hotkey feasibility first; may require GNOME custom shortcut pointing to a CLI flag

### Future Consideration (v2+)

Features to defer until the tool is proven stable.

- [ ] CLI interface (`kbd-backlight --profile Work`) — enables scripting and keyboard shortcut hooks; defer until core GUI is solid
- [ ] Export/import profiles as JSON — useful for backup; low priority until profile count grows
- [ ] Dim on screen lock / restore on unlock — nice automation, requires D-Bus screen lock event listener

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| udev permission setup | HIGH | LOW | P1 |
| All 4 hardware modes | HIGH | LOW | P1 |
| RGB color picker | HIGH | LOW | P1 |
| Speed control | HIGH | LOW | P1 |
| Live preview | HIGH | MEDIUM | P1 |
| Auto-restore on login | HIGH | MEDIUM | P1 |
| Named profiles | HIGH | MEDIUM | P1 |
| System tray + profile menu | HIGH | MEDIUM | P1 |
| Preset color palettes | MEDIUM | LOW | P1 |
| Full config window | HIGH | LOW | P1 (scaffold for everything else) |
| Color harmony suggestions | MEDIUM | MEDIUM | P2 |
| Gradient two-color selector | MEDIUM | MEDIUM | P2 |
| Per-profile swatch in tray | LOW | LOW | P2 |
| Keyboard shortcut switching | MEDIUM | HIGH | P2 (Wayland risk) |
| CLI interface | MEDIUM | MEDIUM | P2 |
| Export/import profiles | LOW | LOW | P3 |
| Dim on screen lock | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | OpenRGB | TUXEDO Control Center | asusctl / rog-control-center | AsusTUFBacklitColorChanger | Our Approach |
|---------|---------|----------------------|------------------------------|---------------------------|--------------|
| Mode selection | Yes (hardware modes) | Yes | Yes | Basic | Yes — all 4 TUF modes |
| RGB color picker | Yes | Yes | CLI only | Basic | Yes — GTK native |
| Speed control | Yes | Yes | CLI only | Unknown | Yes — 3-stop radio/slider |
| Live preview | Yes | Yes | No (CLI apply) | Unknown | Yes — debounced sysfs write |
| Named profiles | Yes (.orp files) | Yes (import/export) | Partial | No | Yes — JSON in ~/.config |
| System tray | Yes (buggy on Linux as root) | No | No | No | Yes — libayatana-appindicator |
| Auto-restore on boot | Needs workaround (startup script) | Yes | Yes (daemon) | No | Yes — autostart .desktop |
| Preset palettes | No | No | No | No | Yes — 6-8 named palettes |
| Color harmony | No | No | No | No | Yes (v1.x) — novel feature |
| Gradient picker | No | No | No | No | Yes (v1.x) |
| Keyboard shortcuts | No | No | No | No | Defer — Wayland risk |
| Per-key RGB | Yes (many devices) | Yes (some models) | Yes (some models) | No | No — hardware limitation |

---

## Sources

- OpenRGB official site and wiki: https://openrgb.org/ and https://openrgb-wiki.readthedocs.io/en/latest/Using-OpenRGB/ (MEDIUM confidence — official docs)
- asusctl / rog-control-center manual: https://asus-linux.org/manual/asusctl-manual/ (MEDIUM confidence — official)
- TUXEDO keyboard backlight dev thoughts: https://www.tuxedocomputers.com/en/Dev-Thoughts-Background-information-on-the-new-keyboard-lighting-control.tuxedo (MEDIUM confidence — official)
- ASUS TUF keyboard sysfs configuration guide: https://guh.me/posts/2024-09-15-manually-configuring-asus-tuf-keyboard-lighting-on-linux/ (MEDIUM confidence — 2024, matches PROJECT.md sysfs format)
- AsusTUFLinuxKeyboard (llybin): https://github.com/llybin/AsusTUFLinuxKeyboard (LOW confidence — minimal docs)
- AsusTUFBacklitColorChanger (oshin94): https://github.com/oshin94/AsusTUFBacklitColorChanger (LOW confidence — minimal docs)
- Aurora (legacyO7): https://github.com/legacyO7/Aurora (LOW confidence — minimal docs)
- KeyRGB (Rainexn0b): https://github.com/Rainexn0b/keyRGB (MEDIUM confidence — feature list in README)
- GTK ColorChooserWidget docs: https://docs.gtk.org/gtk4/class.ColorChooserWidget.html (HIGH confidence — official GTK docs)
- GNOME keyboard backlight added in 45: https://www.omglinux.com/gnome-adds-keyboard-backlight-control/ (MEDIUM confidence)
- systemd-backlight service: https://man7.org/linux/man-pages/man8/systemd-backlight@.service.8.html (HIGH confidence — official manpage)
- OpenRGB profile startup workaround: https://gitlab.com/CalcProgrammer1/OpenRGB/-/issues/319 (MEDIUM confidence — official issue tracker)

---
*Feature research for: Linux keyboard backlight GUI controller (ASUS TUF F16)*
*Researched: 2026-02-21*

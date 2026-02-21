# ASUS TUF F16 Keyboard Backlight Controller

## What This Is

A GUI application for Ubuntu that controls the keyboard backlight on an ASUS TUF F16 laptop. Replaces manual `tee` commands to `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` with a visual interface featuring color pickers, preset palettes, named profiles, and a system tray for quick switching.

## Core Value

The user can visually configure and switch keyboard backlight modes without touching the terminal — and the setting persists across reboots.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Control all hardware-supported modes (static, breathing, color cycle, strobe) with color and speed
- [ ] Live preview — changes apply to keyboard in real-time as user adjusts settings
- [ ] Color picker with gradient selection between two colors
- [ ] Preset color palettes (ocean, sunset, cyberpunk, etc.)
- [ ] Color harmony suggestions (complementary, analogous, triadic) when a color is picked
- [ ] Named profiles (e.g., Gaming, Work, Night) — save and manage configurations
- [ ] System tray icon with quick profile switching menu
- [ ] Full standalone window for detailed configuration
- [ ] Keyboard shortcut support for switching between profiles
- [ ] Auto-restore last used profile on boot/login
- [ ] Proper permission handling (udev rule or similar) — no password prompts for color changes

### Out of Scope

- Custom animation sequences — hardware only supports fixed modes (static, breathing, cycle, strobe); software-driven rapid writes would be unreliable
- Support for other ASUS laptop models — built specifically for TUF F16
- Packaging as .deb or distribution — personal daily driver tool
- Cross-platform support — Ubuntu only

## Context

- Hardware interface: `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode`
- Write format: `"1 [mode] [R] [G] [B] [speed]"` where mode: 0=static, 1=breathing, 2=color_cycle, 3=strobe; speed: 0=slow, 1=medium, 2=fast
- Requires root/sudo to write to sysfs — needs permission solution (udev rule preferred)
- Target: Ubuntu with GNOME desktop environment
- The user currently manages this via shell commands and wants a polished GUI replacement

## Constraints

- **Hardware**: Limited to 4 built-in modes — static, breathing, color cycle, strobe
- **Hardware**: Single RGB value per command — no per-key lighting
- **Hardware**: 3 speed levels only (0, 1, 2)
- **Platform**: Ubuntu/Linux only, GNOME desktop
- **Permissions**: Must solve sysfs write access without repeated sudo prompts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| TUF F16 only, no multi-model support | Simpler, faster to build for personal use | — Pending |
| Udev rule for permissions (over polkit) | Avoids password dialog on every color change | — Pending |
| Full window + tray icon | Full window for setup, tray for daily quick switching | — Pending |

---
*Last updated: 2026-02-21 after initialization*

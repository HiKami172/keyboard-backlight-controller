# ASUS TUF F16 Keyboard Backlight Controller

A sleek GTK4/libadwaita GUI for controlling the keyboard backlight on ASUS TUF F16 laptops running Ubuntu. No more terminal commands — just pick your colors and go.

```
┌──────────────────────────────────────────┐
│  Mode: [Static ▾]  Color: [■ #0064FF]   │
│  Speed: [Slow] [Med] [Fast]             │
│                                          │
│  ● Ocean    ● Sunset    ● Cyberpunk     │
│  ● Crimson  ● Gold      ● Lilac         │
│  ● Glacier  ● Monochrome                │
│                                          │
│  Profile: [Gaming ▾] [Save] [Delete]    │
└──────────────────────────────────────────┘
         ↕ lives in your system tray
        [🔆] → Gaming | Work | Night
```

## Features

- **4 animation modes** — static, breathing, color cycle, strobe
- **Full RGB color picker** with GTK4 ColorDialog
- **8 preset palettes** — Ocean, Sunset, Cyberpunk, Crimson, Gold, Lilac, Glacier, Monochrome
- **Live preview** — changes apply to the keyboard in real-time (~100ms debounce)
- **Named profiles** — save, load, rename, and delete configurations
- **System tray** — quick profile switching with color swatches, powered by AyatanaAppIndicator3
- **Auto-restore** — last used profile is restored on login
- **No sudo prompts** — udev rule grants write access to your user

## Requirements

- Ubuntu 24.04+ with GNOME
- ASUS TUF F16 (or any ASUS laptop with `asus::kbd_backlight` sysfs interface)
- Python 3.10+

## Installation

**1. Install system dependencies:**

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-appindicator3-0.1 python3-dbus
```

**2. Clone and set up permissions:**

```bash
git clone https://github.com/HiKami172/keyboard-backlight-controller.git
cd keyboard-backlight-controller
sudo bash install/setup-permissions.sh
```

> This installs a udev rule and adds your user to the `plugdev` group.
> **Log out and back in** for group changes to take effect.

**3. Run:**

```bash
python3 main.py
```

## Usage

| Action | How |
|--------|-----|
| Open main window | `python3 main.py` |
| Tray-only mode | `python3 main.py --tray-only` |
| Switch profiles | Click the tray icon |
| Save current settings | Type a name and click **Save** |
| Auto-start on login | Run `bash install/install-autostart.sh` |

## How It Works

```
         ┌─────────────┐     ┌───────────────┐
         │ Main Window  │     │  System Tray   │
         │   (GTK4)     │     │ (AppIndicator) │
         └──────┬───────┘     └───────┬────────┘
                │    JSON over stdin   │
                └──────────┬───────────┘
                           │
                ┌──────────┴──────────┐
                │    Application      │
                │  (Adw.Application)  │
                └──┬──────────────┬───┘
                   │              │
          ┌────────┴───┐  ┌──────┴───────┐
          │ ProfileMgr │  │ BacklightCtl │
          │   (JSON)   │  │   (sysfs)    │
          └────────────┘  └──────┬───────┘
                                 │
                    /sys/class/leds/
                    asus::kbd_backlight/
                    kbd_rgb_mode
```

The system tray runs as a **separate subprocess** to avoid GTK3/GTK4 conflicts (AppIndicator3 links GTK3). Communication happens via JSON over stdin.

## Project Structure

```
kbd_backlight/
├── hardware/
│   └── backlight.py       # sysfs interface — path discovery, command formatting
├── profiles/
│   ├── profile.py         # Profile dataclass with validation
│   └── manager.py         # CRUD, atomic JSON storage, last-profile tracking
└── ui/
    ├── application.py     # App lifecycle, tray subprocess, IPC
    ├── window.py          # Main config window — mode/color/speed/profiles
    └── tray.py            # System tray process (GTK3, isolated)
```

## Testing

All 72 tests run without root or hardware — they use temporary files to simulate sysfs:

```bash
python3 -m pytest tests/
```

## License

MIT

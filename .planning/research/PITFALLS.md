# Pitfalls Research

**Domain:** Linux keyboard backlight GUI controller (ASUS TUF F16, sysfs, GNOME system tray)
**Researched:** 2026-02-21
**Confidence:** MEDIUM — Core pitfalls verified via kernel docs, GNOME discourse, PyGObject official docs, and community forum analysis. A few edge cases are MEDIUM/LOW confidence where evidence is forum-only.

---

## Critical Pitfalls

### Pitfall 1: Hardcoded sysfs Path That Vanishes or Renames

**What goes wrong:**
The application hardcodes `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` and ships. On some kernels or after certain asus-wmi updates, this path becomes `/sys/class/leds/asus::kbd_backlight_1/kbd_rgb_mode` due to name collision resolution. A reported kernel bug (Red Hat BZ #1665505) documents exactly this rename happening silently. The app breaks with a permissions or file-not-found error with no clear feedback to the user.

**Why it happens:**
Developers test on one machine, the path works, and it gets hardcoded. The asus-wmi driver resolves LED name collisions by appending `_1`, `_2`, etc., which is a kernel-level decision the app cannot predict.

**How to avoid:**
- At startup, scan `/sys/class/leds/` for any entry matching the pattern `asus::kbd_backlight*` rather than a fixed name.
- Resolve through `/sys/class/leds/` symlinks to real `/sys/devices/platform/asus-nb-wmi/leds/` paths.
- Fail fast with a clear user-facing error ("Could not find ASUS keyboard backlight device. Is the asus-nb-wmi kernel module loaded?") rather than a Python traceback.

**Warning signs:**
- Path works during development but fails after kernel upgrade.
- Any hardcoded string containing `asus::kbd_backlight` without glob/discovery logic.

**Phase to address:**
Hardware I/O foundation phase — the path discovery logic must be in the very first working sysfs integration, not retrofitted later.

---

### Pitfall 2: GNOME Has No Native System Tray — Assuming AppIndicator "Just Works"

**What goes wrong:**
GNOME Shell removed native system tray support in version 3.26 (Ubuntu 17.10+). An app using `AppIndicator3` or `libayatana-appindicator` will produce no visible tray icon on a default Ubuntu GNOME installation. The app silently starts with no tray presence — users cannot access quick profile switching, cannot tell the app is running, and cannot exit it.

**Why it happens:**
Developers find `AppIndicator3` examples written for Unity or older GNOME, copy the pattern, and it works in their specific setup (often because they have the AppIndicator GNOME Shell extension installed already). It fails on a clean Ubuntu install.

**How to avoid:**
- Use `libayatana-appindicator3` (the modern fork), not the unmaintained `libappindicator3`.
- Require and document that the AppIndicator Support GNOME Shell extension must be installed (`gnome-shell-extension-appindicator` package on Ubuntu, or install from extensions.gnome.org extension ID 615).
- At first launch, detect whether the indicator is actually displaying (indicator status != PASSIVE after a short delay) and show a one-time dialog explaining the extension requirement.
- For the indicator to appear at all: `set_status(AppIndicator3.IndicatorStatus.ACTIVE)` AND `set_menu(menu)` must both be called — either alone is insufficient.

**Warning signs:**
- No tray icon visible after running the app.
- No error raised by AppIndicator — it fails silently when GNOME doesn't process the SNI (StatusNotifierItem) protocol.
- Using `Gtk.StatusIcon` (GTK3) — this is deprecated and removed in GTK4; it will not work on GNOME Shell.

**Phase to address:**
System tray integration phase — must include a setup/dependency check step and document the GNOME extension requirement.

---

### Pitfall 3: udev Rule Doesn't Grant Write Permission to sysfs Files

**What goes wrong:**
A udev rule using only `GROUP="plugdev", MODE="0664"` on the LED subsystem appears to work conceptually but does not reliably change file permissions on the `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` sysfs file. The user is added to the group, reboots, and still gets "Permission denied" when writing. This is one of the most consistently reported failure modes in every Linux forum thread about udev and backlight.

**Why it happens:**
Two root causes combine. First, `MODE` in udev rules applies to `/dev` device nodes, not to sysfs attribute files. sysfs files have their own permission model, and GROUP/MODE in udev rules is described as "a kind of hack" that works inconsistently. Second, timing: udev rules with `RUN+="/bin/chgrp"` or `RUN+="/bin/chmod"` can execute before the sysfs file exists in the filesystem (the WMI driver creates it asynchronously).

**How to avoid:**
The reliable solution for `asus::kbd_backlight` specifically is a udev rule using `RUN` commands with explicit chgrp/chmod on the specific file path, not just device-level permissions. However, the most robust approach — recommended by the kernel community for backlight control — is:

```
# /etc/udev/rules.d/99-asus-kbd-backlight.rules
ACTION=="add", SUBSYSTEM=="leds", KERNEL=="asus::kbd_backlight*", \
  RUN+="/bin/chgrp plugdev /sys/class/leds/%k/kbd_rgb_mode", \
  RUN+="/bin/chmod g+w /sys/class/leds/%k/kbd_rgb_mode"
```

Additionally, the user must be in the `plugdev` group (Ubuntu default for the installing user), and must log out and back in after adding the rule. The udev rule itself requires `udevadm control --reload-rules && udevadm trigger` after installation, or a reboot.

**Warning signs:**
- "Permission denied" writing to `kbd_rgb_mode` even after adding udev rule.
- Rule uses only `GROUP=` and `MODE=` without `RUN+` chmod/chgrp.
- User has not re-logged in after group membership change.

**Phase to address:**
Permissions/udev setup phase — must be the very first thing solved and tested before any other feature. Everything else depends on being able to write to the sysfs file.

---

### Pitfall 4: Blocking sysfs Writes on the GTK Main Thread

**What goes wrong:**
Color picker `color-set` signal fires → handler writes to sysfs → the GTK main loop blocks for the duration of the write. With typical sysfs writes this is ~milliseconds and seems fine. But if the kernel module is slow, if there's a delay in WMI firmware response, or if the hardware is busy, the write can take 50-500ms. The UI stutters. If the user drags a color slider, the handler fires continuously, each write potentially blocking for hundreds of milliseconds. The GUI feels broken.

**Why it happens:**
GTK signal handlers run on the main thread. Writing to a file looks like instant I/O but involves kernel → WMI → ACPI → EC (embedded controller) round trips, which are not guaranteed to return quickly.

**How to avoid:**
- Never write to sysfs from a GTK signal handler directly.
- Implement debouncing: collect the "last requested value" and write it in a `GLib.timeout_add(100, ...)` callback (100ms debounce is sufficient — the eye can't distinguish faster than ~100ms color changes anyway).
- For any blocking write in a non-trivial path, use a background thread and `GLib.idle_add()` to signal completion back to the UI. Per PyGObject official docs, only the main thread may call GTK code; worker threads must schedule UI updates via `GLib.idle_add()`.

**Warning signs:**
- Color slider dragging causes visible stutter.
- Signal handlers directly calling `open(...).write(...)` on sysfs paths.
- No debounce or rate-limiting around live preview writes.

**Phase to address:**
Live preview / hardware I/O phase — debounce must be designed in from the start, not added when stutter is reported.

---

### Pitfall 5: sysfs cmd=1 ("Save to BIOS") Used for Live Preview

**What goes wrong:**
The `kbd_rgb_mode` write format is `"cmd mode R G B speed"` where cmd=0 means "set temporarily" and cmd=1 means "save permanently to BIOS". If the live preview implementation uses cmd=1 on every color slider drag, it writes to BIOS firmware with every mouse movement — potentially thousands of BIOS writes per session. BIOS flash memory has limited write cycles. This is the equivalent of writing to an SSD on every keypress; it will eventually wear out firmware storage.

**Why it happens:**
The kernel docs (from the patch series) describe cmd=1 as "save permanently." Developers may read this and use it thinking it's the "correct" write mode for persistence. Or they copy a one-shot example that used cmd=1 for convenience.

**How to avoid:**
- Use cmd=0 for ALL live preview and interactive writes.
- Use cmd=1 ONLY when the user explicitly clicks "Save Profile" or confirms a persistent setting.
- Document this distinction in a code comment wherever cmd is set.

**Warning signs:**
- Any live preview code path using `"1 {mode} {r} {g} {b} {speed}"` as the write string.
- No separate concept of "apply" vs "save" in the codebase.

**Phase to address:**
Hardware I/O foundation phase — the write function must accept a `persist=False` parameter from day one.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode sysfs path | Simpler code | Breaks on kernel update or asus-wmi rename | Never — path discovery is 5 lines of code |
| Write sysfs on every GTK signal | Simpler code, "live" preview | UI stutter, potential EBUSY, fast BIOS wear if cmd=1 | Never — debounce is trivial to implement |
| Use cmd=1 for all writes | Single write mode | Firmware wear from live preview | Only for explicit "save" actions |
| Skip AppIndicator extension check | Fewer lines of code | Silent failure with no tray icon | MVP only, must add check before first user |
| Store profiles as raw sysfs strings | Fast to implement | Brittle when write format changes | Never — parse into a structured dict/dataclass |
| Run as root to avoid udev | "Works immediately" | Root GUI apps break D-Bus, DBus-activated services, keyring; security risk | Never |
| `Gtk.StatusIcon` for tray | Simple API | Deprecated, removed in GTK4, broken on GNOME Shell | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| sysfs `kbd_rgb_mode` | Use path `/sys/class/leds/asus::kbd_backlight/` directly | Use glob `asus::kbd_backlight*` to handle `_1` rename variant |
| sysfs `kbd_rgb_mode` | Write as bytes or binary | Write as space-separated decimal ASCII string: `"0 0 255 0 128 1\n"` |
| AppIndicator3 | Import `gi.repository.AppIndicator3` and assume it works | Check `libayatana-appindicator3-1` is installed; warn user if GNOME extension is missing |
| Autostart `.desktop` file | Use `X-GNOME-Autostart-Phase=` extension | Omit this key — GNOME 49+ emits warnings and may drop support; use plain XDG autostart |
| Autostart `.desktop` file | Autostart to full main window | Autostart with `--tray-only` flag so boot is silent, not a window pop-up |
| Global keyboard shortcuts | Assume GTK accelerators work globally | GTK accelerators only work when the window has focus; use XDG Desktop Portal Global Shortcuts API for system-wide bindings (GNOME 45+) |
| Profile persistence | Store profiles in `/etc/` or next to the binary | Store in `~/.config/asus-kbd-backlight/profiles.json` (XDG config dir) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Writing sysfs on every `color-set` event | Slider drag causes UI stutter; BIOS writes accumulate | 100ms debounce via `GLib.timeout_add` | First time user drags color picker slowly |
| No rate limiting on profile switching shortcuts | Rapid key presses flood sysfs with writes | Debounce shortcut handler with 200ms minimum interval | User holds down shortcut key |
| Polling sysfs to detect external changes | CPU spin loop consuming power | Don't poll — app owns the hardware state, no external changes expected | Continuous background operation |
| Loading large icon resources on system tray init | Startup delay, possible GNOME Shell freeze (reported with large embedded PNGs in AppIndicator) | Use a small icon (32x32 PNG), avoid embedding large images in indicator | First run on slow machines |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Running the GUI as root (sudo app) | Root GUI breaks D-Bus session services, can corrupt user keyring; security escalation risk | Implement udev rule instead; NEVER suggest `sudo python app.py` in docs |
| Using `os.system()` or `subprocess.run(["sudo", ...])` to write to sysfs | Password prompt in GUI; breaks when passwordless sudo not configured | Only direct file write after udev rule grants group permission |
| Storing profiles with executable code paths | If profile JSON is read unsafely with eval or similar | Use `json.load()` only; never eval config file content |
| World-writable config file | Any local user can change hardware behavior | Config written with `0o600` permissions to user's home directory |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| App opens full window on every autostart | User sees a window pop up on every login even if they just want the tray icon | Autostart with minimized/tray-only mode; only show window on explicit tray-click |
| No visual feedback when profile is applied | User can't tell if click on tray menu worked or not | Brief notification or tray tooltip update showing active profile name |
| Color cycle and strobe modes show color picker | Misleading UI — these modes don't use a static color | Disable/hide color picker for non-static modes; show only relevant controls per mode |
| No "test" vs "save" distinction | User accidentally saves a half-configured profile | Two-stage UX: "Apply" (live, cmd=0) and "Save to Profile" (persists to JSON, separately) |
| Closing window exits the app | User expects "close window" = minimize to tray | Intercept `delete-event`, hide window, keep tray icon running |
| No indication that asus-wmi module is missing | Cryptic Python error or silent failure | On startup, check for sysfs path; show actionable error dialog with module load instructions |
| Profiles with duplicate names silently overwrite | Data loss | Validate profile name uniqueness on save; prompt to overwrite or rename |

---

## "Looks Done But Isn't" Checklist

- [ ] **udev rule**: Does it actually work on a clean Ubuntu install without the rule applied yet? Test by removing the rule, logging out, and verifying permission denied, then re-applying. Many rules "work" in testing because the developer added group membership separately.
- [ ] **System tray**: Is the tray icon visible on a fresh Ubuntu installation without any GNOME extensions pre-installed? Test on a clean VM.
- [ ] **Autostart**: Does the app start silently (no window) on login and only appear in the tray? Test by rebooting without opening the app first.
- [ ] **Profile restore on boot**: Is the last profile applied after boot without the user doing anything? Test by switching profile, rebooting, and checking keyboard color.
- [ ] **sysfs path discovery**: Does the app still find the device if the kernel names it `asus::kbd_backlight_1`? Test by temporarily renaming the sysfs entry or mocking it.
- [ ] **Permission denied handling**: Does the app show a clear error (not a Python traceback) when sysfs is not writable? Test by removing udev rule temporarily.
- [ ] **Close to tray**: Does closing the main window keep the app running in the tray? Test without reading the documentation.
- [ ] **Global shortcuts**: Do profile-switching shortcuts work when the app window is closed and another application has focus? Test with the window hidden.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Hardcoded sysfs path breaks after kernel update | LOW | Refactor path to use glob discovery; 30 min fix |
| System tray not working on clean GNOME install | MEDIUM | Add dependency check + first-run dialog; test on clean VM |
| udev rule not granting permissions | LOW | Switch from GROUP/MODE to RUN+chgrp/chmod pattern; re-test |
| sysfs writes blocking UI | MEDIUM | Introduce debounce layer and background thread; touches live preview code |
| BIOS wear from cmd=1 overuse | LOW | Audit all write call sites; change to cmd=0; add persist= parameter |
| App exits instead of minimizing to tray | LOW | Intercept delete-event in window; route to hide() not destroy() |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Hardcoded sysfs path / rename | Phase: Hardware I/O foundation | Integration test with `asus::kbd_backlight_1` mock path |
| No tray icon on GNOME (extension required) | Phase: System tray integration | Tested on clean Ubuntu VM without pre-installed extensions |
| udev rule not working | Phase: Permissions setup (must be Phase 1) | Write test succeeds as non-root user after clean install |
| Blocking sysfs write on GTK thread | Phase: Live preview implementation | Drag color slider for 5 seconds; no UI stutter |
| cmd=1 used for live preview (BIOS wear) | Phase: Hardware I/O foundation | Code review: no live path uses cmd=1 |
| App opens window on autostart | Phase: Autostart implementation | Reboot; verify only tray icon appears, no window |
| Global shortcuts only work with focus | Phase: Keyboard shortcut implementation | Test shortcut while another app has focus |
| Profile persistence to wrong location | Phase: Profile management | Config stored in `~/.config/`, survives package reinstall |

---

## Sources

- Kernel LED class documentation: https://docs.kernel.org/leds/leds-class.html
- asus-wmi RGB keyboard patch (write format spec): https://www.mail-archive.com/linux-kernel@vger.kernel.org/msg1975758.html
- asus-wmi TUF RGB LWN article: https://lwn.net/Articles/903564/
- ASUS TUF kbd_backlight sysfs usage (blog): https://guh.me/posts/2024-09-15-manually-configuring-asus-tuf-keyboard-lighting-on-linux/
- Red Hat BZ #1665505 (asus::kbd_backlight_1 rename): https://bugzilla.redhat.com/show_bug.cgi?id=1665505
- GNOME Discourse — System tray GTK4: https://discourse.gnome.org/t/system-tray-icons-in-gtk4/22615
- GNOME Discourse — StatusIcon replacement GTK4: https://discourse.gnome.org/t/what-to-use-instead-of-statusicon-in-gtk4-to-display-the-icon-in-the-system-tray/7175
- ubuntu/gnome-shell-extension-appindicator GitHub: https://github.com/ubuntu/gnome-shell-extension-appindicator
- PyGObject threading guide (official): https://pygobject.gnome.org/guide/threading.html
- Arch Linux udev backlight forum (permission failure analysis): https://bbs.archlinux.org/viewtopic.php?id=262630
- Arch Linux udev wiki: https://wiki.archlinux.org/title/Udev
- Arch Linux Backlight wiki: https://wiki.archlinux.org/title/Backlight
- XDG Autostart specification: https://specifications.freedesktop.org/autostart-spec/autostart-spec-latest.html
- GNOME 49 autostart deprecation: https://discourse.gnome.org/t/autostart-files-with-x-gnome-autostart-phase-entry-in-gnome-49/31620/9
- sysfs rules (kernel docs): https://www.kernel.org/doc/html/latest/admin-guide/sysfs-rules.html

---
*Pitfalls research for: Linux keyboard backlight GUI controller (ASUS TUF F16, Ubuntu/GNOME)*
*Researched: 2026-02-21*

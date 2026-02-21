# Phase 1: Permissions and Hardware Foundation - Research

**Researched:** 2026-02-21
**Domain:** Linux sysfs LED permissions (udev), Python hardware abstraction, path discovery
**Confidence:** HIGH — core facts verified against kernel source, live hardware, and kernel patch mailing lists

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERM-01 | App sets up udev rule granting user write access to kbd_rgb_mode sysfs file without sudo | udev RUN+chgrp/chmod pattern confirmed; user is in `plugdev` group; exact rule syntax verified against PITFALLS.md decision |
| PERM-02 | App discovers sysfs path dynamically via glob (`asus::kbd_backlight*`) — not hardcoded | Python `pathlib.Path.glob()` and `glob.glob()` both confirmed working on this hardware; mock path pattern verified |
| CTRL-01 | User can select any of the 4 hardware modes (static, breathing, color cycle, strobe) | Mode values 0-3 confirmed from llybin gist (primary hardware community source); kernel source confirms modes 0-11 valid (9 excluded); mode 3 (strobe) may not exist on all TUF models — needs on-hardware test |
| CTRL-02 | User can pick any RGB color via color picker dialog | RGB values 0-255 confirmed in kernel source (`sscanf` reads r, g, b as u32); no validation range in kernel — value clamps happen at hardware level |
| CTRL-03 | User can set animation speed (slow, medium, fast) for breathing/cycle/strobe modes | Speed values 0/1/2 confirmed in kernel source; internally map to 0xe1/0xeb/0xf5; `BacklightController` passes 0/1/2, kernel handles the encoding |
| CTRL-04 | Changes apply to keyboard in real-time as user adjusts controls (debounced ~100ms live preview) | Debounce is a controller-layer concern; no hardware constraints prevent rapid writes; `GLib.timeout_add(100, ...)` is the GTK-safe debounce mechanism (Phase 3 concern but controller must not block) |
| CTRL-05 | Live preview writes use cmd=0 (temporary); explicit save uses cmd=1 (persist to BIOS) — never cmd=1 during slider drag | CONFIRMED from kernel source: cmd=0 → 0xb3 (set, no BIOS save), cmd=1 → 0xb4 (save to BIOS). LWN article confirms: "settings revert on cold boot" if cmd=0 used. BacklightController must accept `persist: bool` parameter |
</phase_requirements>

---

## Summary

Phase 1 establishes the two preconditions everything else depends on: write access to the sysfs file without sudo, and a validated `BacklightController` that abstracts the hardware interface. Both are well-understood problems with confirmed solutions.

The sysfs file `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` is confirmed present on this specific machine (verified live with `ls -la`). Current permissions are `--w-------` owned by root — no user access without the udev rule. The reliable permission solution is a udev rule using `RUN+="/bin/chgrp"` and `RUN+="/bin/chmod"` commands rather than `GROUP=`/`MODE=` (which is unreliable for sysfs attribute files). The user (`hikami`) is already in the `plugdev` group, so no `usermod` step is needed on this machine — though the install script should still include it for reproducibility.

The write format is confirmed from the kernel source (`asus-wmi.c`): six space-separated integers `"cmd mode red green blue speed\n"`, parsed via `sscanf`. cmd=0 (→ 0xb3 internally) sets temporarily; cmd=1 (→ 0xb4) saves to BIOS. Mode values 0-3 are confirmed: 0=static, 1=breathing, 2=color_cycle, 3=strobe — though mode 3 may not be implemented on all TUF hardware. The `BacklightController` class should accept a `persist=False` boolean rather than exposing the cmd integer directly, to prevent accidental BIOS write overuse during live preview.

**Primary recommendation:** Write a `BacklightController(sysfs_path)` class that accepts an injected path (enabling mock-path testing), formats the write string with cmd=0 or cmd=1 based on a `persist` parameter, validates all inputs, and wraps errors in clean exceptions rather than letting `IOError` propagate as tracebacks.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.12 (system) | All Phase 1 logic | No external deps needed: `pathlib`, `glob`, `dataclasses`, `json`, `unittest` are all stdlib |
| pathlib | stdlib | Sysfs path discovery | `Path('/sys/class/leds').glob('asus::kbd_backlight*/kbd_rgb_mode')` confirmed working on this hardware |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python3-pytest | 7.4.4 (apt) | Test runner | Install via `sudo apt install python3-pytest` for cleaner test output; stdlib `unittest` works without it |
| udevadm | system | Debug udev rules | `udevadm control --reload-rules && udevadm trigger` to reload without reboot |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pathlib glob | `glob.glob()` | Both work on this hardware (confirmed); pathlib is more idiomatic Python 3 |
| plugdev group | video group | User is in plugdev but NOT video; plugdev is the Ubuntu default for hardware-access groups |
| RUN+chgrp/chmod | GROUP=/MODE= udev keys | GROUP/MODE unreliable on sysfs attribute files (documented pitfall); RUN+ is explicit and reliable |

**Installation:**
```bash
# No Python packages needed for Phase 1 beyond system Python
# Optional test runner:
sudo apt install python3-pytest
# udev rule (one-time setup):
sudo cp install/99-kbd-backlight.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---

## Architecture Patterns

### Recommended Project Structure

```
kbd_backlight/
├── hardware/
│   ├── __init__.py
│   └── backlight.py         # BacklightController: sysfs path discovery + writes
└── install/
    └── 99-kbd-backlight.rules   # udev rule (install to /etc/udev/rules.d/)
tests/
└── hardware/
    └── test_backlight.py    # Unit tests using mock sysfs path
```

Phase 1 only creates `hardware/` and `install/`. The broader structure from ARCHITECTURE.md applies to later phases.

### Pattern 1: BacklightController with Injected Path

**What:** The controller accepts the sysfs path at construction time. Production code passes the real path (discovered via glob); tests pass a temp-directory mock path. No monkeypatching required.

**When to use:** Always. This is the foundational testability pattern for hardware code.

**Example:**
```python
# hardware/backlight.py
from pathlib import Path

SYSFS_GLOB = "/sys/class/leds/asus::kbd_backlight*/kbd_rgb_mode"

MODES = {
    "static":      0,
    "breathing":   1,
    "color_cycle": 2,
    "strobe":      3,
}

class HardwareNotFoundError(RuntimeError):
    """Raised when the ASUS keyboard backlight sysfs path cannot be found."""
    pass

class BacklightController:
    def __init__(self, sysfs_path: str | None = None):
        if sysfs_path is None:
            sysfs_path = self._discover()
        self._path = Path(sysfs_path)

    @staticmethod
    def _discover() -> str:
        """Find the sysfs path via glob. Handles asus::kbd_backlight_1 renames."""
        matches = list(Path("/sys/class/leds").glob("asus::kbd_backlight*/kbd_rgb_mode"))
        if not matches:
            raise HardwareNotFoundError(
                "Could not find ASUS keyboard backlight device at "
                "/sys/class/leds/asus::kbd_backlight*/kbd_rgb_mode. "
                "Is the asus-nb-wmi kernel module loaded?"
            )
        return str(matches[0])

    def apply(
        self,
        mode: str,
        r: int,
        g: int,
        b: int,
        speed: int,
        persist: bool = False,
    ) -> None:
        """Write backlight command to hardware.

        Args:
            mode: One of "static", "breathing", "color_cycle", "strobe"
            r, g, b: RGB values 0-255
            speed: 0=slow, 1=medium, 2=fast (ignored for static mode)
            persist: If True, writes cmd=1 (save to BIOS). Use only on explicit
                     user save action — never during live preview to avoid BIOS wear.
        """
        if mode not in MODES:
            raise ValueError(f"Unknown mode '{mode}'. Valid: {list(MODES)}")
        if not all(0 <= c <= 255 for c in (r, g, b)):
            raise ValueError(f"RGB values must be 0-255, got ({r}, {g}, {b})")
        if speed not in (0, 1, 2):
            raise ValueError(f"Speed must be 0, 1, or 2, got {speed}")

        cmd = 1 if persist else 0
        payload = f"{cmd} {MODES[mode]} {r} {g} {b} {speed}\n"
        try:
            self._path.write_text(payload)
        except PermissionError:
            raise PermissionError(
                f"Cannot write to {self._path}. "
                "Is the udev rule installed? Run: sudo install/setup-permissions.sh"
            ) from None
```

### Pattern 2: Glob-Based Path Discovery with Fail-Fast Error

**What:** At startup, discover the sysfs path via `pathlib.Path.glob()`. If not found, raise a domain-specific exception with an actionable message — never let `FileNotFoundError` propagate as a Python traceback.

**When to use:** In `BacklightController.__init__()` when no explicit path is provided.

**Confirmed working on this hardware:**
```python
# Verified: returns [PosixPath('/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode')]
list(Path("/sys/class/leds").glob("asus::kbd_backlight*/kbd_rgb_mode"))
```

The `*` handles the `asus::kbd_backlight_1` rename variant documented in Red Hat BZ #1665505.

### Pattern 3: udev Rule Using RUN+chgrp/chmod

**What:** Instead of `GROUP=`/`MODE=` (unreliable on sysfs attribute files), use explicit `RUN+` commands to change ownership and permissions after device add.

**When to use:** This is the ONLY reliable udev approach for sysfs attribute files. Confirmed by PITFALLS.md research and STATE.md decision.

**Exact rule (verified against this hardware's udev attributes):**
```
# /etc/udev/rules.d/99-kbd-backlight.rules
# Grant plugdev group write access to ASUS TUF keyboard RGB mode control
# (plugdev is Ubuntu's default hardware-access group; user must be a member)
ACTION=="add", SUBSYSTEM=="leds", KERNEL=="asus::kbd_backlight*", \
  RUN+="/bin/chgrp plugdev /sys/class/leds/%k/kbd_rgb_mode", \
  RUN+="/bin/chmod g+w /sys/class/leds/%k/kbd_rgb_mode"
```

**Key facts confirmed from live hardware:**
- `KERNEL=="asus::kbd_backlight"` confirmed via `udevadm info --attribute-walk`
- `SUBSYSTEM=="leds"` confirmed via `udevadm info`
- `%k` expands to `asus::kbd_backlight` (the kernel name)
- `/sys/class/leds/%k/kbd_rgb_mode` is the symlink path that resolves correctly
- The user `hikami` is already in `plugdev` group (confirmed with `id`)
- `video` group has no members — do NOT use `video` on this machine

**After installing:**
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
# OR reboot
```

**Testing the rule works (without reboot):**
```bash
# Simulate the add event:
sudo udevadm trigger --action=add /sys/class/leds/asus::kbd_backlight
# Verify permissions changed:
ls -la /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode
# Expected: --w--w---- root plugdev
```

### Anti-Patterns to Avoid

- **GROUP=/MODE= in udev rule:** Does not reliably change sysfs attribute file permissions. The research and STATE.md decision both confirm: use `RUN+chgrp/chmod` only.
- **Hardcoded sysfs path:** Any `"/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode"` literal in code (not the glob) is wrong. The kernel can rename to `asus::kbd_backlight_1`.
- **cmd=1 in live preview writes:** Writes to BIOS flash on every slider drag. Use `persist=False` (cmd=0) for all interactive writes.
- **Running the app as root:** GTK applications as root break D-Bus session services. The udev rule solves permissions at the OS level.
- **Catching all exceptions and silencing them:** The controller should raise specific, actionable exceptions. Silent failures make the "fail fast with readable error" success criterion impossible.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| sysfs path discovery | Custom recursive search | `pathlib.Path.glob("asus::kbd_backlight*/kbd_rgb_mode")` | One line, handles rename variant, returns Path objects |
| Permission setup | Custom privilege escalation | udev rule with `RUN+chgrp/chmod` | OS-level solution, no runtime privilege escalation needed |
| RGB value validation | Custom range-check class | `all(0 <= c <= 255 for c in (r, g, b))` | stdlib one-liner |
| Mock sysfs for tests | Custom hardware mock framework | `tmp_path` (pytest fixture) or `tempfile.mkdtemp()` + write a regular file | The controller accepts a path; a temp file is a complete mock |

**Key insight:** The hardware interface is a file write. Everything complex about this phase is in the permission setup (OS-level) and path discovery (one glob call). The Python code itself is 30-40 lines.

---

## Common Pitfalls

### Pitfall 1: udev GROUP/MODE Fails Silently on sysfs

**What goes wrong:** User installs `SUBSYSTEM=="leds", KERNEL=="asus::kbd_backlight", GROUP="plugdev", MODE="0664"` — the rule applies to the device node but NOT to the `kbd_rgb_mode` sysfs attribute file. The user is in the group, the rule loads, but `PermissionError` still occurs.

**Why it happens:** `GROUP=`/`MODE=` in udev rules applies to `/dev` device nodes, not sysfs virtual files. sysfs attribute permissions require explicit `chmod`.

**How to avoid:** Use `RUN+="/bin/chgrp plugdev /sys/class/leds/%k/kbd_rgb_mode"` and `RUN+="/bin/chmod g+w /sys/class/leds/%k/kbd_rgb_mode"`. Confirmed decision in STATE.md.

**Warning signs:** Rule loads without error (`udevadm control --reload-rules` succeeds) but `ls -la /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` still shows `--w-------`.

### Pitfall 2: sysfs Path Hardcoded — Breaks on Kernel Rename

**What goes wrong:** Path hardcoded as `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode`. After a kernel update, `asus-wmi` driver resolves a name collision by creating `asus::kbd_backlight_1`. App breaks with `FileNotFoundError`.

**Why it happens:** Path works during initial development, developer doesn't know about the rename behavior.

**How to avoid:** Always use `pathlib.Path("/sys/class/leds").glob("asus::kbd_backlight*/kbd_rgb_mode")`. Confirmed on this hardware: glob returns the path correctly.

**Warning signs:** Any string literal containing `asus::kbd_backlight` without a wildcard.

### Pitfall 3: cmd=1 During Live Preview Wears BIOS Flash

**What goes wrong:** Developer uses `"1 {mode} {r} {g} {b} {speed}"` for all writes (it's simpler). Every color slider drag writes to BIOS firmware. BIOS flash has limited write cycles.

**Why it happens:** Kernel source comment says cmd=1 = "save to BIOS" but developer may not notice this or not realize live preview will trigger thousands of writes per session.

**How to avoid:** `BacklightController.apply()` must have a `persist: bool = False` parameter. `persist=False` → cmd=0 (0xb3, set only). `persist=True` → cmd=1 (0xb4, BIOS save). All interactive/live calls use `persist=False`. Only "Save Profile" actions use `persist=True`.

**Warning signs:** No `persist` parameter; all writes use cmd=1; no code review flag on this distinction.

### Pitfall 4: Mode 3 (Strobe) May Not Work on This Hardware

**What goes wrong:** The llybin gist explicitly states "Mine doesn't have a Strobing mode." The hardware may silently ignore mode 3, or it may work. There is no pre-write way to know.

**Why it happens:** The kernel validates mode 0-11 (except 9) as "valid" — the kernel driver doesn't know which modes the specific hardware firmware supports. The firmware just ignores unsupported modes.

**How to avoid:** Write mode 3 to the hardware during Phase 1 verification. If the keyboard shows no visible change, document that strobe is unsupported on this unit and remove it from the UI in Phase 3. Do not fail — just test.

**Warning signs:** Untested assumption that all 4 modes work on this specific TUF F16 unit.

### Pitfall 5: PermissionError Surfaces as Python Traceback

**What goes wrong:** Without the udev rule, `self._path.write_text(payload)` raises `PermissionError`. If uncaught, this becomes a Python traceback with no actionable guidance.

**Why it happens:** Standard file I/O exceptions are raw.

**How to avoid:** Catch `PermissionError` in `BacklightController.apply()` and re-raise with an actionable message referencing the install step. This satisfies success criterion 2: "fails fast with a readable error if the path is missing (not a Python traceback)."

---

## Code Examples

Verified patterns from official and primary sources:

### Write Format (from kernel source `asus-wmi.c`)
```python
# Source: https://github.com/torvalds/linux/blob/master/drivers/platform/x86/asus-wmi.c
# sscanf(buf, "%d %d %d %d %d %d", &cmd, &mode, &r, &g, &b, &speed)
# cmd=0 → 0xb3 (set, no BIOS save); cmd=1 → 0xb4 (save to BIOS)
# mode 0-11 valid (except 9); speed 0/1/2 → 0xe1/0xeb/0xf5 internally

payload = f"{0 if not persist else 1} {MODES[mode]} {r} {g} {b} {speed}\n"
self._path.write_text(payload)
```

### Path Discovery (verified on this hardware)
```python
# Source: verified live on /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode
from pathlib import Path

matches = list(Path("/sys/class/leds").glob("asus::kbd_backlight*/kbd_rgb_mode"))
# Returns: [PosixPath('/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode')]
# Handles asus::kbd_backlight_1 rename variant via the * wildcard
```

### Mock Sysfs for Testing (verified working)
```python
# Source: verified with /tmp/mock_sysfs test on this machine
import tempfile
import os

def make_mock_sysfs() -> str:
    """Create a writable mock sysfs path for testing without hardware."""
    tmpdir = tempfile.mkdtemp()
    led_dir = os.path.join(tmpdir, "asus::kbd_backlight")
    os.makedirs(led_dir)
    mock_path = os.path.join(led_dir, "kbd_rgb_mode")
    Path(mock_path).touch()
    return mock_path

# Usage in tests:
def test_apply_static_mode():
    path = make_mock_sysfs()
    ctrl = BacklightController(sysfs_path=path)
    ctrl.apply("static", r=255, g=0, b=128, speed=0)
    assert Path(path).read_text() == "0 0 255 0 128 0\n"
```

### udev Rule (confirmed for this hardware)
```
# Source: PITFALLS.md research + verified KERNEL="asus::kbd_backlight" via udevadm
# /etc/udev/rules.d/99-kbd-backlight.rules
ACTION=="add", SUBSYSTEM=="leds", KERNEL=="asus::kbd_backlight*", \
  RUN+="/bin/chgrp plugdev /sys/class/leds/%k/kbd_rgb_mode", \
  RUN+="/bin/chmod g+w /sys/class/leds/%k/kbd_rgb_mode"
```

### Mode Value Reference (from llybin gist + kernel patch)
```python
# Source: https://gist.github.com/llybin/4740e423d8281d839ef013b6cc93db7f
# (primary community hardware source for this specific device type)
# Modes 0-3 confirmed; mode 3 (strobe) may not be available on all TUF units
MODES = {
    "static":      0,   # static color
    "breathing":   1,   # breathing/pulsing
    "color_cycle": 2,   # color cycle (not "disco" or "rainbow" — verified name)
    "strobe":      3,   # strobing — may be absent on some TUF models; NEEDS HARDWARE TEST
}
SPEEDS = {
    "slow":   0,   # → 0xe1 in firmware
    "medium": 1,   # → 0xeb in firmware
    "fast":   2,   # → 0xf5 in firmware
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `GROUP=`/`MODE=` in udev for sysfs | `RUN+chgrp/chmod` | Always been the case for sysfs; community learned the hard way | Must use RUN+ pattern — GROUP/MODE fails silently |
| Hardcoded sysfs path | Glob discovery `asus::kbd_backlight*` | After Red Hat BZ #1665505 documented the rename | Required for robustness across kernel versions |
| Subprocess/os.system writes | Direct `Path.write_text()` | — | Direct file write is simpler, faster, no subprocess overhead |

**Deprecated/outdated:**
- `os.system("tee /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode")`: Works for one-shot shell scripts; wrong for an app. Use direct Python file write.
- Running the GUI as `sudo python main.py`: Explicitly wrong for GTK apps (D-Bus session service incompatibility). Solve with udev.

---

## Open Questions

1. **Does mode 3 (strobe) work on this specific TUF F16 unit?**
   - What we know: Kernel accepts it (modes 0-11 are valid except 9); llybin gist says strobe "may vary"
   - What's unclear: Whether firmware on this model implements it or silently ignores it
   - Recommendation: First Phase 1 task — manually write `"0 3 255 0 0 0\n"` to the sysfs file (after udev rule is installed) and observe keyboard behavior. Document result; adjust MODES dict or UI if strobe is absent.

2. **Does cmd=0 vs cmd=1 produce visible behavioral difference on this hardware?**
   - What we know: Kernel source is definitive — cmd=0 (0xb3) = set without BIOS save; cmd=1 (0xb4) = save to BIOS. LWN confirms "settings revert on cold boot" for cmd=0.
   - What's unclear: Whether the keyboard visually shows the same result either way (likely yes) and whether cmd=0 survives suspend/resume (unknown — needs hardware test)
   - Recommendation: Use cmd=0 for all live preview by default. Test cmd=0 behavior across a suspend/resume cycle in Phase 1 to understand whether the app needs to re-apply on resume events.

3. **Should the install script add the user to plugdev?**
   - What we know: The user `hikami` is already in `plugdev`. Adding again is a no-op.
   - What's unclear: Whether future users will be in `plugdev` by default on Ubuntu 24.04
   - Recommendation: Include `sudo usermod -aG plugdev $USER` in the install script unconditionally — it's idempotent and documents the requirement.

---

## Hardware Facts (Confirmed on This Machine)

These are ground-truth observations from the actual hardware, not documentation:

| Fact | Observed Value | Source |
|------|---------------|--------|
| Sysfs path | `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` | `ls /sys/class/leds/` |
| Current permissions | `--w------- root root` | `stat` + `ls -la` |
| Real device path | `/sys/devices/platform/asus-nb-wmi/leds/asus::kbd_backlight` | `readlink -f` |
| Kernel name (KERNEL= in udev) | `asus::kbd_backlight` | `udevadm info --attribute-walk` |
| Subsystem (SUBSYSTEM= in udev) | `leds` | `udevadm info --attribute-walk` |
| Write format index | `cmd mode red green blue speed` | `cat kbd_rgb_mode_index` |
| User group membership | `plugdev` (yes), `video` (no) | `id hikami` |
| Python version | 3.12.3 | `python3 --version` |
| PyGObject version | 3.48.2 | `dpkg -l python3-gi` |
| GTK version | 4.14.2 | Runtime check |
| libadwaita version | 1.5.0 | `dpkg -l gir1.2-adw-1` |
| pytest availability | 7.4.4 (installable via apt; NOT currently installed) | `apt-cache policy python3-pytest` |
| `pathlib.glob` works | Yes — returns `[PosixPath('.../kbd_rgb_mode')]` | Verified live |
| Mock sysfs write works | Yes — regular temp file is sufficient | Verified live |
| Write without udev | `PermissionError: [Errno 13]` | Verified live |
| systemd-backlight service | Active (uses `asus::kbd_backlight` for brightness only) | `systemctl status` |

---

## Sources

### Primary (HIGH confidence)
- Linux kernel source `asus-wmi.c` — `kbd_rgb_mode_store()` function: confirms `sscanf` format, cmd=0→0xb3/cmd=1→0xb4, mode range 0-11 (not 9), speed encoding. https://github.com/torvalds/linux/blob/master/drivers/platform/x86/asus-wmi.c
- Live hardware verification — `ls -la`, `stat`, `udevadm info --attribute-walk`, `pathlib.glob()` test, mock write test, `PermissionError` confirmed. (This machine, 2026-02-21)
- llybin gist — ASUS TUF kbd modes 0=static, 1=breathing, 2=color_cycle, 3=strobe; cmd "nothing changes for me"; speed 0/1/2: https://gist.github.com/llybin/4740e423d8281d839ef013b6cc93db7f

### Secondary (MEDIUM confidence)
- LWN.net asus-wmi TUF RGB article — cmd=1 "save permanently to BIOS," cmd=0 "settings revert on cold boot": https://lwn.net/Articles/903564/
- guh.me ASUS TUF keyboard lighting blog (2024) — sysfs path, write format confirmed, cmd "appears functionally meaningless" (author tested visual result, not persistence): https://guh.me/posts/2024-09-15-manually-configuring-asus-tuf-keyboard-lighting-on-linux/
- PITFALLS.md (project research, 2026-02-21) — udev GROUP/MODE failure analysis, Red Hat BZ #1665505 rename behavior: `.planning/research/PITFALLS.md`
- STACK.md (project research, 2026-02-21) — udev rule pattern, PyGObject version table: `.planning/research/STACK.md`
- Arch Linux forums — udev backlight permission failure analysis: https://bbs.archlinux.org/viewtopic.php?id=262630

### Tertiary (LOW confidence)
- WebSearch results confirming `asus::kbd_backlight` udev rule patterns — multiple forum sources agree on `RUN+chgrp/chmod` approach; no single authoritative doc

---

## Metadata

**Confidence breakdown:**
- Hardware facts: HIGH — verified live on actual hardware
- Write format: HIGH — confirmed from kernel source
- udev rule syntax: HIGH — confirmed from udevadm attribute walk + kernel docs
- Mode values 0-2: HIGH — llybin gist + kernel source agree
- Mode 3 (strobe): MEDIUM — kernel accepts it; hardware behavior unverified
- cmd=0 vs cmd=1 persistence: HIGH — kernel source definitive; suspend/resume behavior LOW
- Test approach (mock sysfs): HIGH — verified live

**Research date:** 2026-02-21
**Valid until:** 2027-02-21 (stable: kernel sysfs interface, udev behavior, Python stdlib)

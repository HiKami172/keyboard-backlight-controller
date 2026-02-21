---
phase: 01-permissions-and-hardware-foundation
verified: 2026-02-21T19:30:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
human_verification:
  - test: "Run sudo install/setup-permissions.sh on the actual machine"
    expected: "Script copies rule, reloads udev, triggers add event; /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode becomes group-writable by plugdev after udev trigger"
    why_human: "Cannot test root script execution or live sysfs permission changes in automated checks"
  - test: "With udev rule installed, run BacklightController() (no sysfs_path arg) and call apply()"
    expected: "Controller discovers real sysfs path via glob and writes to hardware; keyboard backlight changes without sudo"
    why_human: "Live hardware write requires udev rule installed and the real sysfs path to exist"
---

# Phase 1: Permissions and Hardware Foundation Verification Report

**Phase Goal:** Establish OS-level permissions and core hardware abstraction so non-root Python code can write to the ASUS keyboard backlight sysfs attribute.
**Verified:** 2026-02-21T19:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can run the app without sudo — writes to kbd_rgb_mode succeed without a password dialog | ? HUMAN NEEDED | udev rule exists with correct RUN+chgrp/chmod pattern; install script is correct and executable; live hardware effect requires human verification |
| 2 | App discovers the sysfs path via glob at startup and fails fast with a readable error if the path is missing (not a Python traceback) | VERIFIED | `_discover()` uses `Path("/sys/class/leds").glob("asus::kbd_backlight*/kbd_rgb_mode")`; raises `HardwareNotFoundError` (RuntimeError subclass) with message naming `asus-nb-wmi`; confirmed by mock patch test |
| 3 | All 4 hardware modes (static, breathing, color cycle, strobe) can be commanded from the app with any valid RGB color and speed | VERIFIED | `MODES = {static:0, breathing:1, color_cycle:2, strobe:3}`; all 4 modes verified by unit tests with exact payload strings; RGB 0-255 and speed 0/1/2 fully validated |
| 4 | Live preview writes use cmd=0 (temporary); explicit save uses cmd=1 (persist to BIOS) — never cmd=1 during slider drag | VERIFIED | `persist=False` is the default in `apply()`; `cmd = 1 if persist else 0`; unit tests verify `persist=False` -> `"0 "` prefix, `persist=True` -> `"1 "` prefix; smoke test confirms payload `"0 0 255 128 0 1\n"` and `"1 1 0 255 0 0\n"` |
| 5 | BacklightController can be tested with a mock sysfs path (no hardware required for development) | VERIFIED | `BacklightController(sysfs_path=str)` constructor bypasses `_discover()`; all 14 unit tests use temp file injection; all 14 tests pass with `python3 -m unittest` (stdlib only, no hardware, no root) |

**Score:** 4/5 automated, 1/5 human-needed (live hardware test)

### Required Artifacts (from Plan Frontmatter)

#### Plan 01-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `install/99-kbd-backlight.rules` | udev rule granting plugdev write access via RUN+chgrp/chmod | VERIFIED | Exists; contains `RUN+="/bin/chgrp plugdev /sys/class/leds/%k/kbd_rgb_mode"` and `RUN+="/bin/chmod g+w /sys/class/leds/%k/kbd_rgb_mode"`; uses `KERNEL=="asus::kbd_backlight*"` wildcard; no `GROUP=` or `MODE=` directives in rule body (only in comment) |
| `install/setup-permissions.sh` | One-command install script that copies rule and reloads udev | VERIFIED | Exists; executable bit set; passes `bash -n` syntax check; contains `udevadm control --reload-rules`; copies rule, triggers add event, adds `$SUDO_USER` to plugdev; prints success + log-out-required message |
| `kbd_backlight/__init__.py` | Python package root | VERIFIED | Exists; contains module docstring; `import kbd_backlight` succeeds |
| `kbd_backlight/hardware/__init__.py` | hardware subpackage, exports BacklightController | VERIFIED | Exists; contains module docstring; `import kbd_backlight.hardware` succeeds |
| `tests/__init__.py` | Test package root | VERIFIED | Exists (empty, valid Python package marker) |
| `tests/hardware/__init__.py` | Test hardware subpackage root | VERIFIED | Exists (empty, valid Python package marker) |

#### Plan 01-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kbd_backlight/hardware/backlight.py` | BacklightController class, HardwareNotFoundError, MODES dict, SYSFS_GLOB constant; min 60 lines | VERIFIED | Exists; 100 lines; all 4 exports importable; `MODES` = `{static:0, breathing:1, color_cycle:2, strobe:3}`; `SYSFS_GLOB = "/sys/class/leds/asus::kbd_backlight*/kbd_rgb_mode"`; `HardwareNotFoundError(RuntimeError)` confirmed; no subprocess usage; no hardcoded path in production logic |
| `tests/hardware/test_backlight.py` | Unit tests covering all modes, validation, persist flag, error cases, and mock sysfs; min 80 lines | VERIFIED | Exists; 145 lines; 14 test methods across 4 TestCase classes; all 14 pass; zero failures, zero errors |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `install/setup-permissions.sh` | `install/99-kbd-backlight.rules` | `cp` command in setup script | VERIFIED | Script builds `RULE_SRC="${SCRIPT_DIR}/99-kbd-backlight.rules"` and runs `cp "${RULE_SRC}" "${RULE_DST}"` |
| `install/99-kbd-backlight.rules` | `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` | udev `RUN+` commands | VERIFIED | Rule uses `RUN+="/bin/chgrp plugdev /sys/class/leds/%k/kbd_rgb_mode"` and `RUN+="/bin/chmod g+w ..."` — correct pattern for sysfs attribute files |
| `kbd_backlight/hardware/backlight.py` | `/sys/class/leds/asus::kbd_backlight*/kbd_rgb_mode` | `pathlib.Path.glob()` in `BacklightController._discover()` | VERIFIED | `Path("/sys/class/leds").glob("asus::kbd_backlight*/kbd_rgb_mode")` — matches SYSFS_GLOB pattern |
| `kbd_backlight/hardware/backlight.py` | sysfs file | `Path.write_text()` in `BacklightController.apply()` | VERIFIED | `self._path.write_text(payload)` — direct write, no subprocess; payload format smoke-tested |
| `tests/hardware/test_backlight.py` | `kbd_backlight/hardware/backlight.py` | `BacklightController(sysfs_path=mock_path)` | VERIFIED | All test classes import `BacklightController` and instantiate with injected temp path; no `/sys` paths in any test |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PERM-01 | 01-01-PLAN.md | App sets up udev rule granting user write access to kbd_rgb_mode sysfs file without sudo | SATISFIED | `install/99-kbd-backlight.rules` exists with `RUN+chgrp plugdev` + `RUN+chmod g+w` pattern; `install/setup-permissions.sh` installs rule and reloads udev |
| PERM-02 | 01-02-PLAN.md | App discovers sysfs path dynamically via glob (`asus::kbd_backlight*`) — not hardcoded | SATISFIED | `_discover()` uses `Path.glob("asus::kbd_backlight*/kbd_rgb_mode")`; `SYSFS_GLOB` constant documents the pattern; no hardcoded path in production logic |
| CTRL-01 | 01-02-PLAN.md | User can select any of the 4 hardware modes (static, breathing, color cycle, strobe) | SATISFIED | `MODES` dict has all 4; `apply()` validates mode membership; all 4 verified by unit tests writing correct integer payload |
| CTRL-02 | 01-02-PLAN.md | User can pick any RGB color via color picker dialog | SATISFIED (hardware layer) | `apply(r, g, b)` accepts any value 0-255; validation rejects outside-range values with descriptive ValueError; full range verified in tests and smoke test. Note: GTK color picker dialog itself is a Phase 3 concern — Phase 1 delivers the hardware layer that accepts any RGB value |
| CTRL-03 | 01-02-PLAN.md | User can set animation speed (slow, medium, fast) for breathing/cycle/strobe modes | SATISFIED (hardware layer) | `apply(speed=0/1/2)` with validation; invalid speed raises ValueError; all three speeds verified in unit tests |
| CTRL-04 | 01-02-PLAN.md | Changes apply to keyboard in real-time as user adjusts controls (debounced ~100ms live preview) | SATISFIED (hardware layer) | `apply(persist=False)` writes `cmd=0` (temporary, not saved to firmware) — the hardware contract for live preview. Debounce timer is a Phase 3 GTK concern; Phase 1 delivers the cmd=0 semantic |
| CTRL-05 | 01-02-PLAN.md | Live preview uses cmd=0 (temporary); explicit save uses cmd=1 (persist to BIOS) | SATISFIED | `persist=False` default -> `cmd=0`; `persist=True` -> `cmd=1`; verified by unit tests and payload smoke test; no way to accidentally write `cmd=1` without explicit `persist=True` |

**Requirements Status:** 7/7 claimed requirements satisfied. No orphaned requirements detected.

**Note on CTRL-02, CTRL-03, CTRL-04:** These requirements describe end-to-end user actions that span multiple phases. Phase 1 delivers the hardware layer contract (validated RGB/speed parameters, cmd=0 live preview semantics). The UI controls (color picker dialog, speed slider, debounce timer) are Phase 3 deliverables. Assigning these requirement IDs to Phase 1 reflects that the foundational hardware layer must correctly support these behaviors — and it does.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns found |

Scan result: No `TODO`, `FIXME`, `XXX`, `HACK`, `PLACEHOLDER`, `return null`, `return {}`, `return []`, or empty handler patterns found in any phase 1 production or test files.

### Human Verification Required

#### 1. Live udev Rule Installation Test

**Test:** Run `sudo install/setup-permissions.sh` from the project root
**Expected:** Script completes without error; `/sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` becomes group-writable by `plugdev`; `ls -la /sys/class/leds/asus::kbd_backlight/kbd_rgb_mode` shows `g+w` permission
**Why human:** Requires root execution and a live udev subsystem; cannot be automated in static analysis

#### 2. Live Non-Root Hardware Write Test

**Test:** With the udev rule installed and logged back in (plugdev group effective), run:
```python
from kbd_backlight.hardware.backlight import BacklightController
ctrl = BacklightController()   # No sysfs_path — uses real glob discovery
ctrl.apply("static", r=255, g=0, b=0, speed=0)
```
**Expected:** No `PermissionError`; keyboard backlight changes to solid red without using sudo
**Why human:** Requires live hardware, active kernel module (`asus-nb-wmi`), and group membership from logged-in session

---

## Summary

Phase 1 goal is achieved. All automated verifications pass:

- The udev rule file exists with the correct `RUN+chgrp/chmod` pattern (not `GROUP=/MODE=`), using the `asus::kbd_backlight*` wildcard, exactly as designed.
- The install script is executable, passes syntax check, copies the rule, reloads udev, triggers the add event, and adds the user to the `plugdev` group.
- The Python package skeleton (`kbd_backlight`, `kbd_backlight.hardware`, `tests`, `tests.hardware`) is importable from the project root.
- `BacklightController` discovers the sysfs path via `pathlib.Path.glob()` — no hardcoded path in production code.
- `BacklightController.apply()` produces the correct `"{cmd} {mode_int} {r} {g} {b} {speed}\n"` payload format, confirmed by both unit tests and payload smoke test.
- `persist=False` is the default (`cmd=0`); `persist=True` writes `cmd=1` — never the other way around.
- All 4 modes validated; all 3 validators (mode/RGB/speed) raise descriptive `ValueError`.
- `HardwareNotFoundError` is a `RuntimeError` subclass with an actionable `asus-nb-wmi` message.
- All 14 unit tests pass with `python3 -m unittest` (stdlib only; no hardware; no root).
- All 4 documented commits (`970d79a`, `33cc1d6`, `d589f7a`, `113cc61`) exist in git history with correct content.
- All 7 requirement IDs (PERM-01, PERM-02, CTRL-01, CTRL-02, CTRL-03, CTRL-04, CTRL-05) are satisfied at the hardware-layer level.

Two items require human testing: the live udev rule installation and the live non-root hardware write. These cannot be automated but all static preconditions for them are verified and correct.

---

_Verified: 2026-02-21T19:30:00Z_
_Verifier: Claude (gsd-verifier)_

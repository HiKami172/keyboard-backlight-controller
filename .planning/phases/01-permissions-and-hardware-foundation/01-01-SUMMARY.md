---
phase: 01-permissions-and-hardware-foundation
plan: 01
subsystem: infra
tags: [udev, sysfs, plugdev, python-package, hardware-permissions]

# Dependency graph
requires: []
provides:
  - udev rule granting plugdev write access to asus::kbd_backlight sysfs attribute
  - install script that copies rule, reloads udev, triggers add event, adds user to plugdev
  - Python package skeleton (kbd_backlight, kbd_backlight.hardware, tests, tests.hardware)
affects:
  - 02-hardware-abstraction-layer
  - all subsequent phases (package root established here)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - udev RUN+chgrp/chmod for sysfs attribute permissions (not GROUP=/MODE=)
    - Python package skeleton with docstring-only __init__.py stubs

key-files:
  created:
    - install/99-kbd-backlight.rules
    - install/setup-permissions.sh
    - kbd_backlight/__init__.py
    - kbd_backlight/hardware/__init__.py
    - tests/__init__.py
    - tests/hardware/__init__.py
  modified: []

key-decisions:
  - "Use RUN+chgrp/chmod in udev rule (not GROUP=/MODE=) — GROUP/MODE unreliable for sysfs attribute files"
  - "Use plugdev group (not video) — user hikami is in plugdev; video group has no members on this machine"
  - "Include usermod -aG plugdev $SUDO_USER in install script for reproducibility, even though hikami is already in plugdev"
  - "Use asus::kbd_backlight* wildcard in KERNEL= match to handle asus::kbd_backlight_1 rename variant"

patterns-established:
  - "Pattern: udev RUN+chgrp/chmod for sysfs attribute files (the only reliable approach)"
  - "Pattern: Python __init__.py stubs with only docstrings — no imports until implementation exists"

requirements-completed: [PERM-01]

# Metrics
duration: 1min
completed: 2026-02-21
---

# Phase 1 Plan 01: Permissions and Hardware Foundation Summary

**udev rule with RUN+chgrp/chmod grants plugdev write access to asus::kbd_backlight sysfs attribute; Python package skeleton (kbd_backlight.hardware, tests.hardware) created**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-21T18:10:09Z
- **Completed:** 2026-02-21T18:11:32Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Python package skeleton importable from project root (kbd_backlight, kbd_backlight.hardware, tests, tests.hardware)
- udev rule using RUN+chgrp/chmod pattern (confirmed reliable approach for sysfs attribute files)
- Install script that handles full setup: copies rule, reloads udev, triggers add event immediately, adds SUDO_USER to plugdev

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project package skeleton** - `970d79a` (chore)
2. **Task 2: Create udev rule and install script** - `33cc1d6` (feat)

**Plan metadata:** (see final docs commit)

## Files Created/Modified
- `kbd_backlight/__init__.py` — Package root with module docstring
- `kbd_backlight/hardware/__init__.py` — Hardware subpackage stub
- `tests/__init__.py` — Empty test package init
- `tests/hardware/__init__.py` — Empty test subpackage init
- `install/99-kbd-backlight.rules` — udev rule: RUN+chgrp/chmod on KERNEL==asus::kbd_backlight* for plugdev write access
- `install/setup-permissions.sh` — Install script: copies rule, reloads udev, triggers add event, usermod plugdev

## Decisions Made
- RUN+chgrp/chmod pattern chosen over GROUP=/MODE= — GROUP/MODE only applies to /dev device nodes, not sysfs virtual attribute files (confirmed in research and live hardware verification)
- plugdev group used, not video — user hikami is in plugdev; video group has no members on this machine
- Wildcard KERNEL=="asus::kbd_backlight*" used to handle the asus::kbd_backlight_1 rename documented in Red Hat BZ #1665505

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

The install script requires manual execution with sudo (intentional — cannot be automated as it modifies /etc/udev/rules.d/ and system groups):

```bash
sudo install/setup-permissions.sh
```

Then log out and back in for plugdev group membership to take effect.

## Next Phase Readiness
- Package skeleton ready for Plan 02 to add BacklightController implementation in kbd_backlight/hardware/backlight.py
- tests/hardware/ directory ready for Plan 02 test files
- udev rule ready to install; no hardware changes needed before Plan 02 (Plan 02 uses mock sysfs path)

## Self-Check: PASSED

All files confirmed present:
- kbd_backlight/__init__.py - FOUND
- kbd_backlight/hardware/__init__.py - FOUND
- tests/__init__.py - FOUND
- tests/hardware/__init__.py - FOUND
- install/99-kbd-backlight.rules - FOUND
- install/setup-permissions.sh - FOUND
- 01-01-SUMMARY.md - FOUND

All commits confirmed:
- 970d79a (Task 1: package skeleton) - FOUND
- 33cc1d6 (Task 2: udev rule + install script) - FOUND

---
*Phase: 01-permissions-and-hardware-foundation*
*Completed: 2026-02-21*

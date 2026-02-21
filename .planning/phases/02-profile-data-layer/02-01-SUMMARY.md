---
phase: 02-profile-data-layer
plan: 01
subsystem: database
tags: [dataclass, validation, profile, stdlib, python]

# Dependency graph
requires:
  - phase: 01-permissions-and-hardware-foundation
    provides: BacklightController established sysfs path and validation patterns (mode, RGB, speed)
provides:
  - Profile dataclass with __post_init__ validation (name, mode, r/g/b, speed)
  - ProfileError(ValueError) public exception type
  - kbd_backlight.profiles subpackage with public API
  - 29-test unit suite covering all validation paths and serialization
affects:
  - 02-02-PLAN.md (ProfileManager consumes Profile as its data shape)
  - Phase 3 GTK window (Profile is the UI data model)
  - Phase 4 tray (Profile used for mode switching)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ClassVar fields on @dataclass excluded from dataclasses.asdict() output automatically — no manual field filtering needed"
    - "ProfileError(ValueError) subclass pattern — callers catch either ProfileError or ValueError"
    - "TDD: RED (failing tests) → GREEN (minimal implementation) → committed separately"

key-files:
  created:
    - kbd_backlight/profiles/__init__.py
    - kbd_backlight/profiles/profile.py
    - tests/profiles/__init__.py
    - tests/profiles/test_profile.py
  modified: []

key-decisions:
  - "ProfileError subclasses ValueError so callers can catch either — raises ProfileError from __post_init__ throughout"
  - "VALID_MODES as ClassVar[set[str]] on the dataclass — excluded from asdict() by Python dataclasses stdlib, verified Python 3.12"
  - "Intentional validation duplication vs BacklightController — Profile must be hardware-independent; no imports from hardware layer"
  - "ProfileManager NOT imported in __init__.py to avoid forward-ref error — added in Plan 02"

patterns-established:
  - "Profile validation pattern: match BacklightController rules but in profiles layer (name, mode, RGB, speed)"
  - "ClassVar pattern: use ClassVar for constants on @dataclass; stdlib excludes them from asdict"

requirements-completed: [PROF-01, PROF-03]

# Metrics
duration: 1min
completed: 2026-02-21
---

# Phase 2 Plan 01: Profile Dataclass Summary

**Profile @dataclass with __post_init__ validation and ProfileError(ValueError), 29-test TDD suite covering all error paths and asdict roundtrip**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-21T20:24:49Z
- **Completed:** 2026-02-21T20:25:53Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments

- Profile dataclass with 6 fields: name, mode, r, g, b, speed — all validated in __post_init__
- ProfileError(ValueError) custom exception — catchable as either type by callers
- VALID_MODES as ClassVar excludes from asdict(), giving exactly 6 serialization keys with roundtrip equality
- 29-test unit suite in 5 test classes covering all validation paths, serialization, and JSON roundtrip

## Task Commits

Each task was committed atomically:

1. **RED phase: failing tests for Profile dataclass** - `4a0b74f` (test)
2. **GREEN phase: implement Profile dataclass** - `e544b8f` (feat)

_Note: TDD tasks have two commits (test RED → feat GREEN)_

## Files Created/Modified

- `kbd_backlight/profiles/__init__.py` - Package init exporting Profile and ProfileError
- `kbd_backlight/profiles/profile.py` - Profile @dataclass with ClassVar, __post_init__ validation, ProfileError
- `tests/profiles/__init__.py` - Empty test package init
- `tests/profiles/test_profile.py` - 29-test suite: TestProfileValidName, TestProfileValidModes, TestProfileRGBValidation, TestProfileSpeedValidation, TestProfileSerialization

## Decisions Made

- ProfileError subclasses ValueError so callers can catch either — plan specified this approach explicitly
- VALID_MODES as ClassVar[set[str]] on the dataclass — Python stdlib excludes ClassVar from asdict() automatically; no manual filtering needed
- Intentional duplication of validation rules from BacklightController — Profile must remain hardware-independent with no imports from the hardware layer
- ProfileManager NOT added to __init__.py in this plan — deferred to Plan 02 to avoid forward-reference errors

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Profile dataclass ready for ProfileManager (Plan 02) to use as its data shape
- asdict() serialization confirmed working — ProfileManager can write/read JSON using this directly
- All 29 tests passing; hardware-free and stdlib-only

---
*Phase: 02-profile-data-layer*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: kbd_backlight/profiles/__init__.py
- FOUND: kbd_backlight/profiles/profile.py
- FOUND: tests/profiles/__init__.py
- FOUND: tests/profiles/test_profile.py
- FOUND: 02-01-SUMMARY.md
- FOUND commit: 4a0b74f (test RED phase)
- FOUND commit: e544b8f (feat GREEN phase)

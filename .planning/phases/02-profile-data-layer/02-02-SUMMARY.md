---
phase: 02-profile-data-layer
plan: 02
subsystem: database
tags: [json, pathlib, atomic-write, crud, profilemanager, tempfile, unittest, python, stdlib]

# Dependency graph
requires:
  - phase: 02-profile-data-layer/02-01
    provides: Profile dataclass and ProfileError(ValueError) — ProfileManager uses these as its data shape for serialization and deserialization

provides:
  - ProfileManager with atomic JSON CRUD over profiles.json envelope file
  - Atomic write pattern: tmp.write_text() + tmp.replace() (rename(2) — atomic on Linux)
  - _load() with no-cache guarantee — always reads from disk
  - _dict_to_profile() with unknown-key filtering via dataclasses.fields() introspection
  - get_all_profiles() single-load convenience method for Phase 3/4 bulk access
  - Updated kbd_backlight.profiles __init__.py exporting ProfileManager
  - 29-test integration suite covering all CRUD paths, persistence, rename edge cases, unknown keys

affects:
  - Phase 3 GTK window (imports ProfileManager for profile dropdown and save/load)
  - Phase 4 tray (imports ProfileManager for mode-switching menu)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Atomic JSON write: write to .json.tmp sibling, then Path.replace() — rename(2) syscall, atomic on Linux"
    - "_load() never caches — read from disk on every call; prevents stale state with multiple instances"
    - "_dict_to_profile() uses dataclasses.fields() to filter unknown JSON keys — hand-edited files safe"
    - "Envelope JSON: {last_profile, profiles{}} — single file, single atomic write for any mutation"
    - "TDD: RED (failing tests with ImportError) -> GREEN (minimal implementation passing all 29 tests)"

key-files:
  created:
    - kbd_backlight/profiles/manager.py
    - tests/profiles/test_manager.py
  modified:
    - kbd_backlight/profiles/__init__.py

key-decisions:
  - "Atomic write via tmp.replace(profiles_path) — not direct write_text(); prevents partial-write corruption"
  - "_load() never caches (no self._data) — reads disk on every call to prevent stale state"
  - "_dict_to_profile() silently filters unknown JSON keys — hand-edited JSON does not crash"
  - "delete_profile and rename_profile update last_profile in the same _save() call — no race window"
  - "get_all_profiles() added as single-_load() convenience for Phase 3/4 bulk iteration"

patterns-established:
  - "Atomic write pattern: tmp_path.write_text(); tmp_path.replace(target) — reusable for any JSON file"
  - "Unknown-key filtering: {f.name for f in dataclasses.fields(Cls)} — filter dict before dataclass construction"
  - "Injection-based testing: config_dir=pathlib.Path(tempfile.mkdtemp()) in setUp, shutil.rmtree in tearDown"

requirements-completed: [PROF-01, PROF-02, PROF-03, PROF-04]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 2 Plan 02: ProfileManager Summary

**ProfileManager with atomic JSON CRUD (tmp.replace pattern), no-cache _load(), unknown-key-safe _dict_to_profile(), and 29-test integration suite covering all CRUD/rename/persistence edge cases**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T20:28:29Z
- **Completed:** 2026-02-21T20:30:49Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments

- ProfileManager with 8-method public API: list_profiles, get_profile, get_all_profiles, save_profile, delete_profile, rename_profile, get_last_profile, set_last_profile
- Atomic write pattern using Path.replace() (rename(2)) — partial-write corruption impossible
- _load() always reads from disk (no caching) — safe with multiple ProfileManager instances
- _dict_to_profile() silently filters unknown JSON keys via dataclasses.fields() — hand-edited profiles.json cannot crash the app
- 29-test integration suite: 6 test classes, covers BasicCRUD, LastProfile tracking, Rename edge cases, Persistence across instances, UnknownKeys tolerance, GetAll convenience

## Task Commits

Each task was committed atomically:

1. **RED phase: failing integration tests for ProfileManager** - `0c237c0` (test)
2. **GREEN phase: implement ProfileManager with atomic JSON CRUD** - `6202f75` (feat)

_Note: TDD tasks have two commits (test RED -> feat GREEN)_

## Files Created/Modified

- `kbd_backlight/profiles/manager.py` - ProfileManager with full CRUD API and atomic write pattern
- `kbd_backlight/profiles/__init__.py` - Updated to export ProfileManager alongside Profile and ProfileError
- `tests/profiles/test_manager.py` - 29-test integration suite: 6 classes, all behaviors from plan spec

## Decisions Made

- Atomic write via `tmp.replace(profiles_path)` not direct `write_text()` — plan spec required this; prevents partial-write corruption on process kill mid-write
- `_load()` never caches (no `self._data` or `self._cache`) — reads disk on every call; plan spec required this; prevents stale state when two instances coexist (e.g. test + production, future multi-window)
- `_dict_to_profile()` silently filters unknown JSON keys using `dataclasses.fields()` — plan spec required this; user hand-edited JSON does not crash on load
- `delete_profile` and `rename_profile` update `last_profile` in the same `_save()` call — prevents stale reference causing `get_last_profile()` to return `None` for a deleted/renamed entry
- `get_all_profiles()` added as a single-`_load()` convenience — reduces N `_load()` calls to 1 for Phase 3/4 profile list rendering

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- ProfileManager complete and tested — ready for Phase 3 GTK window to import and use
- All 58 tests passing (29 profile unit + 29 manager integration) — full profiles test suite green
- `from kbd_backlight.profiles import Profile, ProfileError, ProfileManager` confirmed working
- Phase 3 can call `ProfileManager()` for production or `ProfileManager(config_dir=tmp)` for testing
- Phase 4 tray can call `get_all_profiles()` for efficient single-load menu rendering

---
*Phase: 02-profile-data-layer*
*Completed: 2026-02-21*

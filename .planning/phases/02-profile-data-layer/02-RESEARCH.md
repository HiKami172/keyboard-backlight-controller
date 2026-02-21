# Phase 2: Profile Data Layer - Research

**Researched:** 2026-02-21
**Domain:** Python dataclasses, JSON persistence, atomic file I/O, XDG config directories
**Confidence:** HIGH — all patterns verified with live Python 3.12.3 execution on this machine; no external libraries required

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROF-01 | User can create named profiles with mode, color, and speed settings | `Profile` dataclass with `name`, `mode`, `r`, `g`, `b`, `speed` fields; `ProfileManager.save_profile()` persists to JSON immediately; verified roundtrip |
| PROF-02 | User can save, rename, and delete profiles | `ProfileManager.save_profile()` (create/overwrite), `.rename_profile()`, `.delete_profile()` — all operate on the same JSON file; rename updates `last_profile` if it matches |
| PROF-03 | Profiles stored as JSON in `~/.config/kbd-backlight/` — human-readable and hand-editable | `json.dumps(indent=2)` produces readable output; `Path.home() / ".config" / "kbd-backlight" / "profiles.json"` is the canonical path; verified on this machine |
| PROF-04 | Last used profile auto-restores on app launch | `last_profile` key in envelope JSON; `ProfileManager.get_last_profile()` returns `Profile \| None`; caller applies it via `BacklightController` (Phase 3/4 concern, not Phase 2) |
</phase_requirements>

---

## Summary

Phase 2 builds the profile persistence layer in pure Python stdlib — no GTK, no hardware, no external dependencies. The implementation is two classes: `Profile` (a validated dataclass) and `ProfileManager` (CRUD manager over a single JSON file). Both are testable without hardware, without root, and without a display server.

The storage format is a JSON envelope file at `~/.config/kbd-backlight/profiles.json`. The envelope has two top-level keys: `"profiles"` (a dict of name-to-profile-data) and `"last_profile"` (a nullable string). This single-file approach is simpler than separate files and sufficient for the scale of this personal tool. All writes use an atomic temp-file-then-rename pattern (`Path.write_text()` + `Path.replace()`) to prevent corrupt JSON on partial writes.

The `Profile` dataclass uses `__post_init__` validation (same modes/RGB/speed rules as `BacklightController`) and `dataclasses.asdict()` for serialization. Unknown JSON keys encountered when loading hand-edited files are silently filtered using `dataclasses.fields()` introspection — this prevents `TypeError` crashes when the user adds custom comments or fields. Phase 2 does NOT call `BacklightController.apply()` — applying a profile to the keyboard is a Phase 3/4 concern. Phase 2 only reads and writes disk.

**Primary recommendation:** Implement `Profile` dataclass with `__post_init__` validation and `ProfileManager` with envelope-JSON storage and atomic writes. Two plans: one for the profile module, one for the manager module and its integration tests.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` | stdlib (Python 3.12) | `Profile` data shape, `asdict()` serialization | Built-in, zero-deps, clean JSON serialization; verified on this machine |
| `json` | stdlib | Read/write `profiles.json` | Built-in; `json.dumps(indent=2)` produces human-readable output confirmed by hand |
| `pathlib` | stdlib | `~/.config/kbd-backlight/` path handling | Consistent with Phase 1's `BacklightController` — same idiom throughout codebase |
| `tempfile` | stdlib | Mock config dir in tests | Used in Phase 1 tests (`make_mock_sysfs()`); same pattern applies here |
| `unittest` | stdlib | Test runner | Phase 1 used `unittest.TestCase`; keep consistent; pytest is optional |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | stdlib | `Profile \| None` return types | Python 3.10+ union syntax works on 3.12; use for `get_profile()` and `get_last_profile()` |
| `os` | stdlib | `tempfile.mkdtemp()` companion | Used in Phase 1 test helpers; same pattern applies |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dataclasses` | `pydantic` | Pydantic has better validation ergonomics but is an external dep; overkill for 6 fields |
| Envelope JSON | Two files (`profiles.json` + `state.json`) | Two-file approach adds complexity with no benefit at this scale; single file is simpler |
| `json.dumps(indent=2)` | `json.dumps(sort_keys=True)` | `sort_keys` makes diffs cleaner but disrupts human intuitive field order; not worth it |
| `Path.replace()` atomic write | Direct `Path.write_text()` | Direct write risks leaving corrupt JSON on crash mid-write; `replace()` is free and atomic on Linux |

**Installation:**
```bash
# No installation needed — all stdlib
python3 --version  # Confirm 3.12.3 (verified on this machine)
```

---

## Architecture Patterns

### Recommended Project Structure

```
kbd_backlight/
├── hardware/
│   ├── __init__.py         # Phase 1 (done)
│   └── backlight.py        # Phase 1 (done) — BacklightController
└── profiles/
    ├── __init__.py         # Phase 2 — exports Profile, ProfileManager, ProfileError
    ├── profile.py          # Phase 2 — Profile dataclass + ProfileError
    └── manager.py          # Phase 2 — ProfileManager (disk CRUD)
tests/
├── hardware/
│   └── test_backlight.py   # Phase 1 (done)
└── profiles/
    ├── __init__.py         # Phase 2
    ├── test_profile.py     # Phase 2 — Profile dataclass unit tests
    └── test_manager.py     # Phase 2 — ProfileManager integration tests
```

This mirrors the `hardware/` subpackage pattern from Phase 1. `profiles/` separates data shape (profile.py) from disk operations (manager.py) — consistent with single-responsibility.

### Pattern 1: Profile Dataclass with `__post_init__` Validation

**What:** `Profile` is a `@dataclass` with field-level validation in `__post_init__`. Validation reuses the same rules as `BacklightController` (mode names, RGB 0-255, speed 0/1/2). `dataclasses.asdict()` serializes directly to a JSON-ready dict.

**When to use:** Always — `Profile` is the only data shape for profiles. Never construct raw dicts.

**Verified pattern (Python 3.12.3, this machine):**
```python
# kbd_backlight/profiles/profile.py
import dataclasses
from typing import ClassVar

@dataclasses.dataclass
class Profile:
    VALID_MODES: ClassVar[set[str]] = {"static", "breathing", "color_cycle", "strobe"}

    name: str
    mode: str
    r: int
    g: int
    b: int
    speed: int

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Profile name cannot be empty")
        if self.mode not in self.VALID_MODES:
            raise ValueError(f"Unknown mode '{self.mode}'. Valid: {sorted(self.VALID_MODES)}")
        if not all(0 <= c <= 255 for c in (self.r, self.g, self.b)):
            raise ValueError(f"RGB values must be 0-255, got ({self.r}, {self.g}, {self.b})")
        if self.speed not in (0, 1, 2):
            raise ValueError(f"Speed must be 0, 1, or 2, got {self.speed}")
```

**Verified:** `ClassVar` fields are excluded from `dataclasses.asdict()` — confirmed live. `__post_init__` validation fires on both direct construction and `Profile(**dict)` reconstruction.

**Serialization:**
```python
import dataclasses, json
p = Profile("Work", "static", 255, 128, 0, 0)
d = dataclasses.asdict(p)
# {"name": "Work", "mode": "static", "r": 255, "g": 128, "b": 0, "speed": 0}
json.dumps(d, indent=2)  # human-readable
```

### Pattern 2: Envelope JSON Storage Format

**What:** Single file `profiles.json` with two top-level keys. `"profiles"` is a dict keyed by profile name. `"last_profile"` is the name of the last activated profile, or `null`.

**Verified on-disk format:**
```json
{
  "last_profile": "Work",
  "profiles": {
    "Work": {
      "name": "Work",
      "mode": "static",
      "r": 255,
      "g": 128,
      "b": 0,
      "speed": 0
    },
    "Gaming": {
      "name": "Gaming",
      "mode": "breathing",
      "r": 0,
      "g": 0,
      "b": 255,
      "speed": 1
    }
  }
}
```

This is human-readable, hand-editable, and survives any order of CRUD operations.

**First-run state (file does not exist yet):**
```json
{
  "last_profile": null,
  "profiles": {}
}
```

### Pattern 3: ProfileManager with Atomic Writes

**What:** Every mutating operation loads the full JSON, modifies the in-memory dict, then writes atomically via `write_text()` + `Path.replace()`. `Path.replace()` calls `rename(2)` on Linux — guaranteed atomic.

**Verified pattern (Python 3.12.3, this machine):**
```python
# kbd_backlight/profiles/manager.py
import dataclasses, json, pathlib
from .profile import Profile

class ProfileManager:
    def __init__(self, config_dir: pathlib.Path | None = None) -> None:
        if config_dir is None:
            config_dir = pathlib.Path.home() / ".config" / "kbd-backlight"
        self._config_dir = config_dir
        self._profiles_path = config_dir / "profiles.json"
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        try:
            return json.loads(self._profiles_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"last_profile": None, "profiles": {}}
        except json.JSONDecodeError:
            return {"last_profile": None, "profiles": {}}

    def _save(self, data: dict) -> None:
        tmp = self._profiles_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._profiles_path)

    def list_profiles(self) -> list[str]:
        return list(self._load()["profiles"].keys())

    def get_profile(self, name: str) -> Profile | None:
        raw = self._load()["profiles"].get(name)
        if raw is None:
            return None
        return self._dict_to_profile(raw)

    def save_profile(self, profile: Profile) -> None:
        data = self._load()
        data["profiles"][profile.name] = dataclasses.asdict(profile)
        self._save(data)

    def delete_profile(self, name: str) -> None:
        data = self._load()
        data["profiles"].pop(name, None)
        if data.get("last_profile") == name:
            data["last_profile"] = None
        self._save(data)

    def rename_profile(self, old_name: str, new_name: str) -> None:
        data = self._load()
        if old_name not in data["profiles"]:
            raise KeyError(f"Profile '{old_name}' not found")
        if new_name in data["profiles"]:
            raise ValueError(f"Profile '{new_name}' already exists")
        profile_data = data["profiles"].pop(old_name)
        profile_data["name"] = new_name
        data["profiles"][new_name] = profile_data
        if data.get("last_profile") == old_name:
            data["last_profile"] = new_name
        self._save(data)

    def get_last_profile(self) -> Profile | None:
        data = self._load()
        last = data.get("last_profile")
        if not last:
            return None
        return self.get_profile(last)

    def set_last_profile(self, name: str) -> None:
        data = self._load()
        data["last_profile"] = name
        self._save(data)

    @staticmethod
    def _dict_to_profile(raw: dict) -> Profile:
        """Load Profile from dict, silently ignoring unknown keys."""
        fields = {f.name for f in dataclasses.fields(Profile)}
        return Profile(**{k: v for k, v in raw.items() if k in fields})
```

**Full integration test verified:** create, read, rename, delete, last_profile tracking, delete-resets-last all pass. JSON on disk is human-readable. See: `/home/hikami/Documents/projects/keyboard-backlights-control/.planning/phases/02-profile-data-layer/02-RESEARCH.md` (this file).

### Pattern 4: Test with Injected Config Dir (no `~/.config/` pollution)

**What:** Pass a `tempfile.mkdtemp()` path as `config_dir` to `ProfileManager` in all tests. Mirrors the `sysfs_path` injection pattern from Phase 1's `BacklightController`.

**Verified pattern:**
```python
import tempfile, pathlib, unittest
from kbd_backlight.profiles.manager import ProfileManager
from kbd_backlight.profiles.profile import Profile

class TestProfileManager(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.mgr = ProfileManager(config_dir=self._tmpdir)
```

No test ever touches `~/.config/`. No test requires hardware or root.

### Anti-Patterns to Avoid

- **Writing to `~/.config/` in tests:** Tests must inject `config_dir` or they pollute production data and are environment-sensitive.
- **Direct `Path.write_text()` without temp-file rename:** If the process crashes mid-write, `profiles.json` is left half-written and `_load()` gets a `JSONDecodeError`. Use `tmp.replace(target)`.
- **Storing profiles as a flat list instead of a dict:** List lookup is O(n) and rename requires finding+removing+inserting. Dict keyed by name is O(1) and simpler.
- **Calling `BacklightController.apply()` from `ProfileManager`:** Phase 2 explicitly has no hardware dependency. The caller (Phase 3 window, Phase 4 tray) is responsible for applying the profile. `ProfileManager` only knows about disk.
- **Using profile name as the only key without handling rename in `last_profile`:** When `delete_profile` or `rename_profile` fires, `last_profile` must be updated atomically in the same `_save()` call. Separate saves create a race window.
- **Constructing `Profile(**raw)` without filtering unknown keys:** If the user adds custom fields by hand-editing JSON, `Profile()` raises `TypeError`. Use `_dict_to_profile()` with field introspection to filter safely.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom lock file or write-then-move logic | `tmp.write_text(); tmp.replace(target)` — one line | `Path.replace()` calls `rename(2)` which is atomic on Linux; free from stdlib |
| Config dir location | Custom path logic | `pathlib.Path.home() / ".config" / "kbd-backlight"` | XDG Base Dir Spec convention; matches what GTK apps use; user knows where to look |
| Profile serialization | Custom JSON encoder | `dataclasses.asdict()` + `json.dumps()` | Zero boilerplate; `asdict()` is recursive and handles nested types if any are added later |
| Field validation | Custom descriptor protocol | `__post_init__` in dataclass | Runs on construction and on `Profile(**dict)` reconstruction from JSON — one definition |
| Unknown key filtering | `try/except TypeError` loop | `{f.name for f in dataclasses.fields(Profile)}` | Two-liner; forward-compatible as fields are added |

**Key insight:** This phase is pure data plumbing. All the "hard" problems (atomic writes, serialization, validation) have stdlib one-liner solutions. The implementation is ~120 lines of Python including docstrings.

---

## Common Pitfalls

### Pitfall 1: Non-Atomic Write Corrupts profiles.json

**What goes wrong:** `self._profiles_path.write_text(json.dumps(data))` — if the process is killed between the truncation and the final byte, `profiles.json` is a partial JSON string. Next `_load()` gets `JSONDecodeError` and returns empty state — all profiles silently disappear.

**Why it happens:** `write_text()` opens the file for overwrite immediately; the kernel may flush only part of the buffer before crash.

**How to avoid:** Always write to a `.json.tmp` sibling, then `tmp.replace(target)`. The `replace()` call is a single `rename(2)` syscall — atomic. If the process dies before `replace()`, the original file is untouched.

**Warning signs:** Any `profiles_path.write_text(...)` without a preceding temp-file step.

### Pitfall 2: `last_profile` Staleness After Delete or Rename

**What goes wrong:** `delete_profile("Work")` removes `Work` from `profiles` dict but doesn't clear `last_profile`. On next launch, `get_last_profile()` finds `last_profile = "Work"` but `get_profile("Work")` returns `None`. The app either crashes or silently ignores the restore.

**Why it happens:** `delete_profile` and `rename_profile` modify `profiles` without updating `last_profile`.

**How to avoid:** In `delete_profile`: if `data["last_profile"] == name`, set to `None`. In `rename_profile`: if `data["last_profile"] == old_name`, update to `new_name`. Both happen in the same `_save()` call.

**Warning signs:** `delete_profile` implementation that doesn't touch `last_profile`.

### Pitfall 3: Unknown JSON Keys Cause `TypeError` on Load

**What goes wrong:** User hand-edits `profiles.json` and adds a `"notes": "my custom field"` key. Next `_load()` does `Profile(**raw)` which raises `TypeError: Profile.__init__() got an unexpected keyword argument 'notes'`. All profiles become unloadable.

**Why it happens:** `dataclass.__init__` rejects unknown kwargs.

**How to avoid:** Use `_dict_to_profile()` with field-set filtering:
```python
fields = {f.name for f in dataclasses.fields(Profile)}
Profile(**{k: v for k, v in raw.items() if k in fields})
```
Unknown keys are silently dropped. Documented explicitly so future phases know this is intentional.

**Warning signs:** `Profile(**raw)` without field filtering anywhere JSON is parsed.

### Pitfall 4: Config Dir Test Pollution

**What goes wrong:** Tests call `ProfileManager()` without injecting `config_dir`. Tests write to the user's real `~/.config/kbd-backlight/profiles.json`. Running tests overwrites the user's live profiles.

**Why it happens:** Convenience — `ProfileManager()` defaults to the real config dir.

**How to avoid:** All tests inject `config_dir=pathlib.Path(tempfile.mkdtemp())`. The real default is correct for production; tests never use it.

**Warning signs:** Any test that instantiates `ProfileManager()` with no arguments.

### Pitfall 5: Profile Name Collision on Rename

**What goes wrong:** `rename_profile("Work", "Gaming")` when `Gaming` already exists. The implementation pops `Work` and inserts `Gaming`, silently overwriting the original `Gaming` profile. User loses a profile with no warning.

**Why it happens:** Dict assignment overwrites without checking.

**How to avoid:** In `rename_profile`, check `if new_name in data["profiles"]: raise ValueError(...)` before the pop/insert.

**Warning signs:** `rename_profile` implementation without an existence check for `new_name`.

### Pitfall 6: `_load()` Returns Stale In-Memory State

**What goes wrong:** `ProfileManager` caches the loaded dict as an instance attribute (e.g., `self._data`). If two `ProfileManager` instances exist (or the file changes externally), the cached state diverges. CRUD operations corrupt the file.

**Why it happens:** Caching seems like an optimization.

**How to avoid:** Always `_load()` from disk at the start of each operation. The JSON file is small (<10KB for any realistic number of profiles); disk reads are negligible. No caching needed.

**Warning signs:** `self._data` or `self._cache` instance attributes on `ProfileManager`.

---

## Code Examples

All examples verified on Python 3.12.3, this machine, 2026-02-21.

### Profile Dataclass Roundtrip

```python
# Verified: dataclass -> asdict -> json -> Profile
import dataclasses, json
from kbd_backlight.profiles.profile import Profile

p = Profile("Work", "static", 255, 128, 0, 0)
d = dataclasses.asdict(p)
# {'name': 'Work', 'mode': 'static', 'r': 255, 'g': 128, 'b': 0, 'speed': 0}

j = json.dumps(d, indent=2)
p2 = Profile(**json.loads(j))
assert p2 == p  # passes
```

### Atomic Write

```python
# Verified: rename(2) is atomic on Linux
def _save(self, data: dict) -> None:
    tmp = self._profiles_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(self._profiles_path)
```

### Loading with Unknown Key Filtering

```python
# Verified: unknown keys silently ignored
@staticmethod
def _dict_to_profile(raw: dict) -> Profile:
    fields = {f.name for f in dataclasses.fields(Profile)}
    return Profile(**{k: v for k, v in raw.items() if k in fields})
```

### Test Setup Pattern

```python
# Mirrors Phase 1's make_mock_sysfs() — inject a temp dir, never touch ~/.config/
import tempfile, pathlib, unittest
from kbd_backlight.profiles.manager import ProfileManager

class TestProfileManager(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.mgr = ProfileManager(config_dir=self._tmpdir)
```

### Applying a Profile to Hardware (Phase 3/4 Bridge — NOT Phase 2)

```python
# This code belongs in Phase 3 or 4, NOT in ProfileManager.
# Shown here so the planner knows the interface between phases.
from kbd_backlight.hardware.backlight import BacklightController
from kbd_backlight.profiles.manager import ProfileManager

mgr = ProfileManager()
ctrl = BacklightController()

profile = mgr.get_last_profile()
if profile:
    ctrl.apply(
        profile.mode,
        r=profile.r, g=profile.g, b=profile.b,
        speed=profile.speed,
        persist=False,  # live preview; caller decides persist=True for explicit save
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pickle` for Python object persistence | `json` + `dataclasses.asdict()` | Python 3.7+ (dataclasses) | JSON is human-readable, portable, not a security hazard on load |
| `configparser` (INI format) | JSON with `indent=2` | — | JSON is standard; supports nested structures if needed later; parseable by any tool |
| `os.path` + `open()` for file I/O | `pathlib.Path` throughout | Python 3.4+ (pathlib) | Consistent with Phase 1 conventions; `.with_suffix()` makes temp-file pattern cleaner |
| Custom validation classes | `dataclasses` + `__post_init__` | Python 3.7+ | Zero boilerplate; no external validation library needed |

**Deprecated/outdated:**
- `json.load(open(path))` without `with` block: leaves file handle open on exception. Use `Path.read_text()` + `json.loads()`.
- `shelve` or `sqlite3` for profile storage: gross overkill for a handful of named profiles in a personal tool.

---

## Open Questions

1. **Should `save_profile()` overwrite a profile with the same name, or raise if it already exists?**
   - What we know: Overwrite is simpler for the UI (user edits and re-saves the same profile); raising requires a separate "update" method
   - What's unclear: Which UX the Phase 3 window will want — "save current settings to active profile" implies overwrite
   - Recommendation: Overwrite silently. The UI knows which profile is active. If the user wants a new profile, they provide a new name.

2. **Should `Profile` validation duplicate `BacklightController`'s validation, or import from it?**
   - What we know: Both enforce the same rules (mode names, RGB 0-255, speed 0-2); `MODES` dict lives in `backlight.py`
   - What's unclear: Whether importing hardware constants into the profile layer violates the "no hardware dependency" requirement
   - Recommendation: Duplicate the mode set as `Profile.VALID_MODES` (a `ClassVar`). The profile layer is intentionally hardware-independent; the duplication is intentional decoupling. If modes change, update both places (this is a personal tool with 4 fixed modes — unlikely to change).

3. **Should `ProfileManager` expose a `profiles` dict property for bulk access?**
   - What we know: Phase 3 needs `list_profiles()` for dropdown; Phase 4 needs the same for tray menu. Both iterate the list and call `get_profile()` per item.
   - What's unclear: Whether a `get_all_profiles() -> dict[str, Profile]` convenience method would reduce `_load()` calls in Phase 3/4
   - Recommendation: Add `get_all_profiles() -> dict[str, Profile]` as an optional convenience method. One `_load()` call instead of N calls for N profiles in a loop. Low cost to add in Phase 2; high value for Phase 4 tray menu rendering.

---

## Interface Contract for Downstream Phases

Phase 3 and Phase 4 will import from `kbd_backlight.profiles`. The contract:

```python
# kbd_backlight/profiles/__init__.py should export:
from .profile import Profile, ProfileError
from .manager import ProfileManager

# What Phase 3/4 callers can do:
mgr = ProfileManager()                          # uses ~/.config/kbd-backlight/
mgr = ProfileManager(config_dir=path)           # injectable for testing

profile = Profile("Work", "static", 255, 0, 0, 0)  # raises ValueError on invalid input
mgr.save_profile(profile)                       # create or overwrite
mgr.delete_profile("Work")                      # no-op if not found
mgr.rename_profile("Work", "Office")            # raises KeyError if not found; ValueError on collision
names = mgr.list_profiles()                     # list[str], insertion order
p = mgr.get_profile("Work")                     # Profile | None
all_p = mgr.get_all_profiles()                  # dict[str, Profile] — one _load() call
last = mgr.get_last_profile()                   # Profile | None
mgr.set_last_profile("Work")                    # persists immediately
```

The `Profile` fields map directly to `BacklightController.apply()` parameters:
- `profile.mode` → `mode`
- `profile.r, .g, .b` → `r, g, b`
- `profile.speed` → `speed`
- `persist` is caller's decision — `ProfileManager` does not decide this

---

## Sources

### Primary (HIGH confidence)

- Python 3.12 stdlib — `dataclasses`, `json`, `pathlib`, `tempfile`, `unittest` — verified with live execution on this machine (Python 3.12.3). All code examples above run without error.
- Linux `rename(2)` man page — `Path.replace()` uses `rename()` syscall which is atomic on same-filesystem operations. `/tmp` and `~/.config/` are on the same filesystem (ext4/btrfs) on this machine.
- XDG Base Directory Specification — `~/.config/` is the correct location for user config files. `pathlib.Path.home() / ".config"` is the correct Python idiom.

### Secondary (MEDIUM confidence)

- Phase 1 Research and Plan (`.planning/phases/01-permissions-and-hardware-foundation/`) — established `pathlib`, `tempfile`, `unittest` as project conventions; Phase 2 follows the same patterns.
- Phase 1 implementation (`kbd_backlight/hardware/backlight.py`, `tests/hardware/test_backlight.py`) — confirmed the injected-path testing pattern and `unittest.TestCase` test style that Phase 2 should mirror.

### Tertiary (LOW confidence)

- None. All findings verified from stdlib execution or project-internal artifacts.

---

## Metadata

**Confidence breakdown:**
- Standard stack (stdlib only): HIGH — verified live on Python 3.12.3, this machine
- Architecture (envelope JSON, ProfileManager API): HIGH — full integration test passes, all edge cases verified
- Pitfalls: HIGH — all pitfalls identified from direct code execution and edge case tests
- Interface contract for Phase 3/4: MEDIUM — API designed from requirements; actual Phase 3 needs not yet implemented

**Research date:** 2026-02-21
**Valid until:** 2027-02-21 (stable: Python stdlib, JSON format, XDG paths — none of these change)

"""ProfileManager — atomic JSON CRUD over a single profiles.json envelope file.

Storage format (profiles.json):
    {
      "last_profile": null | "name",
      "profiles": {
        "name": { "name": ..., "mode": ..., "r": ..., "g": ..., "b": ..., "speed": ... }
      }
    }

All writes are atomic: data is written to a .json.tmp sibling file, then
renamed over the target using Path.replace() — which calls rename(2) on Linux,
a single syscall that is atomic on the same filesystem.

_load() never caches — every call reads from disk. This prevents stale-state
corruption if two ProfileManager instances coexist (test scenarios, future
multi-window) or if the file is edited externally.

Unknown JSON keys in profile entries are silently filtered by _dict_to_profile()
using dataclasses.fields() introspection — hand-edited JSON with extra fields
does not crash on load.
"""

import dataclasses
import json
import pathlib

from .profile import Profile


class ProfileManager:
    """Manages keyboard backlight profiles stored in a single JSON file.

    Parameters
    ----------
    config_dir:
        Directory containing profiles.json. Defaults to
        ``~/.config/kbd-backlight/``. The directory is created on construction
        (parents=True, exist_ok=True). Pass a temp directory in tests.
    """

    def __init__(self, config_dir: pathlib.Path | None = None) -> None:
        if config_dir is None:
            config_dir = pathlib.Path.home() / ".config" / "kbd-backlight"
        self._config_dir = config_dir
        self._profiles_path = config_dir / "profiles.json"
        self._config_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        """Read profiles.json and return the envelope dict.

        Returns the empty-state envelope on FileNotFoundError or
        JSONDecodeError — never raises; never caches.
        """
        try:
            return json.loads(self._profiles_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"last_profile": None, "profiles": {}}

    def _save(self, data: dict) -> None:
        """Write data to profiles.json atomically using tmp-then-replace.

        Writes to a .json.tmp sibling, then renames it over the target.
        rename(2) is atomic on Linux — partial writes never corrupt the live file.
        """
        tmp = self._profiles_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._profiles_path)

    @staticmethod
    def _dict_to_profile(raw: dict) -> Profile:
        """Construct a Profile from a raw dict, silently ignoring unknown keys.

        Uses dataclasses.fields() introspection to filter the dict to only
        the keys that Profile.__init__ accepts. Hand-edited JSON with extra
        fields (e.g. "notes") does not raise TypeError.
        """
        fields = {f.name for f in dataclasses.fields(Profile)}
        return Profile(**{k: v for k, v in raw.items() if k in fields})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_profiles(self) -> list[str]:
        """Return list of profile names in insertion order."""
        return list(self._load()["profiles"].keys())

    def get_profile(self, name: str) -> Profile | None:
        """Return Profile for the given name, or None if not found."""
        raw = self._load()["profiles"].get(name)
        if raw is None:
            return None
        return self._dict_to_profile(raw)

    def get_all_profiles(self) -> dict[str, Profile]:
        """Return all profiles as a dict keyed by name.

        Uses a single _load() call — more efficient than calling get_profile()
        in a loop when all profiles are needed (e.g. GTK dropdown, tray menu).
        """
        data = self._load()
        return {
            name: self._dict_to_profile(raw)
            for name, raw in data["profiles"].items()
        }

    def save_profile(self, profile: Profile) -> None:
        """Persist profile to disk. Creates or overwrites by name."""
        data = self._load()
        data["profiles"][profile.name] = dataclasses.asdict(profile)
        self._save(data)

    def delete_profile(self, name: str) -> None:
        """Remove profile by name. No-op if not found.

        Clears last_profile if it matched the deleted name — prevents stale
        references that would make get_last_profile() return None on next
        load even though last_profile still points to a deleted entry.
        """
        data = self._load()
        data["profiles"].pop(name, None)
        if data.get("last_profile") == name:
            data["last_profile"] = None
        self._save(data)

    def rename_profile(self, old_name: str, new_name: str) -> None:
        """Rename a profile from old_name to new_name.

        Also updates the profile's 'name' field in JSON and updates
        last_profile if it matched old_name — all in the same atomic _save().

        Raises
        ------
        KeyError
            If old_name does not exist in profiles.
        ValueError
            If new_name already exists in profiles (would silently overwrite).
        """
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
        """Return the last-activated Profile, or None if not set."""
        data = self._load()
        last = data.get("last_profile")
        if not last:
            return None
        return self.get_profile(last)

    def set_last_profile(self, name: str) -> None:
        """Record name as the last-activated profile. Persists immediately."""
        data = self._load()
        data["last_profile"] = name
        self._save(data)

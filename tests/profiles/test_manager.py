"""Integration tests for ProfileManager.

All tests inject a tempfile.mkdtemp() config_dir — no test ever touches
~/.config/kbd-backlight/ and no test requires hardware or root access.

Test classes:
- TestProfileManagerBasicCRUD: save, list, get, overwrite, delete no-op
- TestProfileManagerLastProfile: set/get last_profile, delete clears it, rename updates it
- TestProfileManagerRename: success case, KeyError on missing source, ValueError on collision
- TestProfileManagerPersistence: save -> new instance at same dir -> get_profile still works
- TestProfileManagerUnknownKeys: manually write JSON with unknown key -> silently ignored
- TestProfileManagerGetAll: get_all_profiles() returns correct dict
"""

import dataclasses
import json
import pathlib
import shutil
import tempfile
import unittest

from kbd_backlight.profiles import Profile, ProfileError, ProfileManager


def _make_profile(name: str = "Work", mode: str = "static", r: int = 255,
                  g: int = 128, b: int = 0, speed: int = 0) -> Profile:
    """Helper to create a Profile with sensible defaults."""
    return Profile(name, mode, r, g, b, speed)


class TestProfileManagerBasicCRUD(unittest.TestCase):
    """Basic create, read, update, delete operations."""

    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.mgr = ProfileManager(config_dir=self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir)

    def test_list_profiles_empty_manager(self) -> None:
        """list_profiles() on empty manager returns []."""
        self.assertEqual(self.mgr.list_profiles(), [])

    def test_save_and_get_profile(self) -> None:
        """save_profile then get_profile returns the same Profile."""
        p = _make_profile("Work")
        self.mgr.save_profile(p)
        result = self.mgr.get_profile("Work")
        self.assertEqual(result, p)

    def test_list_profiles_after_two_saves(self) -> None:
        """save_profile x2 then list_profiles returns both names."""
        self.mgr.save_profile(_make_profile("Work"))
        self.mgr.save_profile(_make_profile("Gaming", "breathing", 0, 0, 255, 1))
        names = self.mgr.list_profiles()
        self.assertIn("Work", names)
        self.assertIn("Gaming", names)
        self.assertEqual(len(names), 2)

    def test_get_profile_missing_returns_none(self) -> None:
        """get_profile on a non-existent name returns None."""
        self.assertIsNone(self.mgr.get_profile("NoExist"))

    def test_save_profile_overwrites_same_name(self) -> None:
        """save_profile with same name overwrites without error."""
        p1 = _make_profile("Work", "static", 255, 0, 0, 0)
        p2 = _make_profile("Work", "breathing", 0, 255, 0, 1)
        self.mgr.save_profile(p1)
        self.mgr.save_profile(p2)
        result = self.mgr.get_profile("Work")
        self.assertEqual(result, p2)

    def test_delete_profile_removes_it(self) -> None:
        """delete_profile removes the profile from storage."""
        self.mgr.save_profile(_make_profile("Work"))
        self.mgr.delete_profile("Work")
        self.assertIsNone(self.mgr.get_profile("Work"))

    def test_delete_profile_noop_for_missing(self) -> None:
        """delete_profile on non-existent name raises no exception."""
        try:
            self.mgr.delete_profile("NoExist")
        except Exception as e:
            self.fail(f"delete_profile raised unexpectedly: {e}")

    def test_profiles_json_uses_indent2(self) -> None:
        """profiles.json is written with indent=2 (human-readable)."""
        self.mgr.save_profile(_make_profile("Test", "breathing", 0, 128, 255, 1))
        raw_text = (self._tmpdir / "profiles.json").read_text()
        self.assertIn("  ", raw_text, "Expected indent=2 formatting in profiles.json")


class TestProfileManagerLastProfile(unittest.TestCase):
    """Tests for set_last_profile, get_last_profile, and tracking through mutations."""

    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.mgr = ProfileManager(config_dir=self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir)

    def test_get_last_profile_initially_none(self) -> None:
        """get_last_profile() returns None when last_profile is null."""
        self.assertIsNone(self.mgr.get_last_profile())

    def test_set_and_get_last_profile(self) -> None:
        """set_last_profile then get_last_profile returns the stored Profile."""
        p = _make_profile("Work")
        self.mgr.save_profile(p)
        self.mgr.set_last_profile("Work")
        result = self.mgr.get_last_profile()
        self.assertEqual(result, p)

    def test_delete_profile_clears_last_profile(self) -> None:
        """delete_profile clears last_profile when it matches the deleted name."""
        self.mgr.save_profile(_make_profile("Work"))
        self.mgr.set_last_profile("Work")
        self.mgr.delete_profile("Work")
        self.assertIsNone(self.mgr.get_last_profile())
        # Also verify last_profile key is null in JSON
        raw = json.loads((self._tmpdir / "profiles.json").read_text())
        self.assertIsNone(raw["last_profile"])

    def test_delete_profile_preserves_last_profile_for_other_profile(self) -> None:
        """delete_profile does NOT clear last_profile when deleting a different profile."""
        self.mgr.save_profile(_make_profile("Work"))
        self.mgr.save_profile(_make_profile("Gaming", "breathing", 0, 0, 255, 1))
        self.mgr.set_last_profile("Gaming")
        self.mgr.delete_profile("Work")
        self.assertEqual(self.mgr.get_last_profile(), _make_profile("Gaming", "breathing", 0, 0, 255, 1))

    def test_rename_updates_last_profile(self) -> None:
        """rename_profile updates last_profile when old_name matched it."""
        self.mgr.save_profile(_make_profile("Work"))
        self.mgr.set_last_profile("Work")
        self.mgr.rename_profile("Work", "Office")
        # last_profile should now be "Office"
        raw = json.loads((self._tmpdir / "profiles.json").read_text())
        self.assertEqual(raw["last_profile"], "Office")
        # get_last_profile should return the renamed profile
        result = self.mgr.get_last_profile()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Office")


class TestProfileManagerRename(unittest.TestCase):
    """Tests for rename_profile success and error cases."""

    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.mgr = ProfileManager(config_dir=self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir)

    def test_rename_profile_success(self) -> None:
        """rename_profile renames a profile and its data is accessible under new name."""
        p = _make_profile("Work")
        self.mgr.save_profile(p)
        self.mgr.rename_profile("Work", "Office")
        self.assertIsNone(self.mgr.get_profile("Work"))
        result = self.mgr.get_profile("Office")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Office")

    def test_rename_profile_keyerror_on_missing_source(self) -> None:
        """rename_profile raises KeyError when old_name does not exist."""
        with self.assertRaises(KeyError):
            self.mgr.rename_profile("NoExist", "NewName")

    def test_rename_profile_valueerror_on_collision(self) -> None:
        """rename_profile raises ValueError when new_name already exists."""
        self.mgr.save_profile(_make_profile("Work"))
        self.mgr.save_profile(_make_profile("Gaming", "breathing", 0, 0, 255, 1))
        with self.assertRaises(ValueError):
            self.mgr.rename_profile("Work", "Gaming")

    def test_rename_preserves_other_profile_data(self) -> None:
        """rename_profile does not affect other profiles."""
        self.mgr.save_profile(_make_profile("Work"))
        p_gaming = _make_profile("Gaming", "breathing", 0, 0, 255, 1)
        self.mgr.save_profile(p_gaming)
        self.mgr.rename_profile("Work", "Office")
        self.assertEqual(self.mgr.get_profile("Gaming"), p_gaming)

    def test_rename_profile_name_field_updated_in_json(self) -> None:
        """After rename, the profile's 'name' field in JSON matches new_name."""
        self.mgr.save_profile(_make_profile("Work"))
        self.mgr.rename_profile("Work", "Office")
        raw = json.loads((self._tmpdir / "profiles.json").read_text())
        self.assertIn("Office", raw["profiles"])
        self.assertEqual(raw["profiles"]["Office"]["name"], "Office")


class TestProfileManagerPersistence(unittest.TestCase):
    """Tests that data survives creating a fresh ProfileManager on the same dir."""

    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir)

    def test_save_then_new_instance_get_profile(self) -> None:
        """save_profile -> new ProfileManager(same dir) -> get_profile returns same Profile."""
        mgr1 = ProfileManager(config_dir=self._tmpdir)
        p = _make_profile("Work")
        mgr1.save_profile(p)

        mgr2 = ProfileManager(config_dir=self._tmpdir)
        result = mgr2.get_profile("Work")
        self.assertEqual(result, p)

    def test_last_profile_persists_across_instances(self) -> None:
        """set_last_profile -> new ProfileManager -> get_last_profile returns same Profile."""
        mgr1 = ProfileManager(config_dir=self._tmpdir)
        p = _make_profile("Work")
        mgr1.save_profile(p)
        mgr1.set_last_profile("Work")

        mgr2 = ProfileManager(config_dir=self._tmpdir)
        last = mgr2.get_last_profile()
        self.assertEqual(last, p)

    def test_list_profiles_persists_across_instances(self) -> None:
        """Saved profiles appear in list_profiles() for a fresh manager instance."""
        mgr1 = ProfileManager(config_dir=self._tmpdir)
        mgr1.save_profile(_make_profile("Work"))
        mgr1.save_profile(_make_profile("Gaming", "breathing", 0, 0, 255, 1))

        mgr2 = ProfileManager(config_dir=self._tmpdir)
        names = mgr2.list_profiles()
        self.assertIn("Work", names)
        self.assertIn("Gaming", names)

    def test_atomic_write_uses_tmp_replace(self) -> None:
        """profiles.json is written atomically (no direct write to profiles_path)."""
        mgr = ProfileManager(config_dir=self._tmpdir)
        mgr.save_profile(_make_profile("Work"))
        # profiles.json must exist after save
        self.assertTrue((self._tmpdir / "profiles.json").exists())
        # No .json.tmp file should remain after successful write
        self.assertFalse((self._tmpdir / "profiles.json.tmp").exists())


class TestProfileManagerUnknownKeys(unittest.TestCase):
    """Tests that unknown JSON keys in profile entries are silently ignored."""

    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.mgr = ProfileManager(config_dir=self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir)

    def test_unknown_key_in_profile_entry_does_not_crash(self) -> None:
        """Manually writing JSON with an unknown key 'notes' does not crash _load."""
        raw = {
            "last_profile": None,
            "profiles": {
                "Work": {
                    "name": "Work",
                    "mode": "static",
                    "r": 255,
                    "g": 128,
                    "b": 0,
                    "speed": 0,
                    "notes": "my custom annotation",
                }
            }
        }
        (self._tmpdir / "profiles.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")

        # Should not raise TypeError
        try:
            result = self.mgr.get_profile("Work")
        except TypeError as e:
            self.fail(f"_load raised TypeError on unknown key: {e}")

        # The profile data should load correctly (without the unknown key)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Work")
        self.assertEqual(result.mode, "static")
        self.assertEqual(result.r, 255)

    def test_corrupted_json_returns_empty_state(self) -> None:
        """JSONDecodeError on load returns empty state (no crash)."""
        (self._tmpdir / "profiles.json").write_text("{ not valid json", encoding="utf-8")
        # Should not raise
        profiles = self.mgr.list_profiles()
        self.assertEqual(profiles, [])

    def test_missing_file_returns_empty_state(self) -> None:
        """Fresh manager with no profiles.json returns empty state."""
        # No file written — _load should handle FileNotFoundError
        profiles = self.mgr.list_profiles()
        self.assertEqual(profiles, [])


class TestProfileManagerGetAll(unittest.TestCase):
    """Tests for get_all_profiles() returning dict[str, Profile]."""

    def setUp(self) -> None:
        self._tmpdir = pathlib.Path(tempfile.mkdtemp())
        self.mgr = ProfileManager(config_dir=self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir)

    def test_get_all_profiles_empty(self) -> None:
        """get_all_profiles() on empty manager returns empty dict."""
        result = self.mgr.get_all_profiles()
        self.assertEqual(result, {})

    def test_get_all_profiles_returns_all_saved(self) -> None:
        """get_all_profiles() returns all saved profiles as dict[str, Profile]."""
        p1 = _make_profile("Work")
        p2 = _make_profile("Gaming", "breathing", 0, 0, 255, 1)
        self.mgr.save_profile(p1)
        self.mgr.save_profile(p2)
        result = self.mgr.get_all_profiles()
        self.assertEqual(len(result), 2)
        self.assertIn("Work", result)
        self.assertIn("Gaming", result)
        self.assertEqual(result["Work"], p1)
        self.assertEqual(result["Gaming"], p2)

    def test_get_all_profiles_is_dict_keyed_by_name(self) -> None:
        """get_all_profiles() keys are profile names, values are Profile objects."""
        p = _make_profile("Work")
        self.mgr.save_profile(p)
        result = self.mgr.get_all_profiles()
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["Work"], Profile)

    def test_get_all_profiles_single_load(self) -> None:
        """get_all_profiles() is consistent — one call returns all profiles."""
        profiles = [
            _make_profile("Alpha"),
            _make_profile("Beta", "breathing", 0, 100, 200, 1),
            _make_profile("Gamma", "color_cycle", 0, 0, 0, 2),
        ]
        for p in profiles:
            self.mgr.save_profile(p)
        result = self.mgr.get_all_profiles()
        self.assertEqual(len(result), 3)
        for p in profiles:
            self.assertIn(p.name, result)
            self.assertEqual(result[p.name], p)


if __name__ == "__main__":
    unittest.main()

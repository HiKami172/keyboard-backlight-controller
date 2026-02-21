"""Unit tests for Profile dataclass validation.

Covers: name validation, mode validation, RGB validation, speed validation,
serialization (asdict), roundtrip equality, ClassVar exclusion from asdict.

Run with: python3 -m unittest tests.profiles.test_profile -v
"""

import dataclasses
import unittest

from kbd_backlight.profiles.profile import Profile, ProfileError


class TestProfileValidName(unittest.TestCase):
    """Tests for Profile name field validation."""

    def test_valid_name_constructs_without_error(self) -> None:
        """Profile with a valid name should construct without raising."""
        p = Profile("Work", "static", 255, 128, 0, 0)
        self.assertEqual(p.name, "Work")

    def test_empty_name_raises_profile_error(self) -> None:
        """Profile with empty string name should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("", "static", 255, 0, 0, 0)

    def test_whitespace_only_name_raises_profile_error(self) -> None:
        """Profile with whitespace-only name should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("  ", "static", 255, 0, 0, 0)

    def test_profile_error_is_value_error_subclass(self) -> None:
        """ProfileError must be catchable as ValueError."""
        with self.assertRaises(ValueError):
            Profile("", "static", 0, 0, 0, 0)

    def test_single_character_name_is_valid(self) -> None:
        """Single non-whitespace character name should be valid."""
        p = Profile("X", "static", 0, 0, 0, 0)
        self.assertEqual(p.name, "X")


class TestProfileValidModes(unittest.TestCase):
    """Tests for Profile mode field validation."""

    def test_static_mode_is_valid(self) -> None:
        """Mode 'static' should be accepted."""
        p = Profile("X", "static", 0, 0, 0, 0)
        self.assertEqual(p.mode, "static")

    def test_breathing_mode_is_valid(self) -> None:
        """Mode 'breathing' should be accepted."""
        p = Profile("X", "breathing", 0, 0, 0, 0)
        self.assertEqual(p.mode, "breathing")

    def test_color_cycle_mode_is_valid(self) -> None:
        """Mode 'color_cycle' should be accepted."""
        p = Profile("X", "color_cycle", 0, 0, 0, 2)
        self.assertEqual(p.mode, "color_cycle")

    def test_strobe_mode_is_valid(self) -> None:
        """Mode 'strobe' should be accepted."""
        p = Profile("X", "strobe", 0, 0, 0, 0)
        self.assertEqual(p.mode, "strobe")

    def test_unknown_mode_raises_profile_error(self) -> None:
        """Unknown mode 'disco' should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("X", "disco", 255, 0, 0, 0)

    def test_empty_mode_raises_profile_error(self) -> None:
        """Empty string mode should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("X", "", 0, 0, 0, 0)

    def test_valid_modes_classvar_contains_all_four_modes(self) -> None:
        """VALID_MODES ClassVar should contain exactly 4 modes."""
        self.assertEqual(
            Profile.VALID_MODES,
            {"static", "breathing", "color_cycle", "strobe"},
        )


class TestProfileRGBValidation(unittest.TestCase):
    """Tests for Profile r, g, b field validation (0-255 inclusive)."""

    def test_r_at_upper_bound_255_is_valid(self) -> None:
        """r=255 (upper bound) should be accepted."""
        p = Profile("X", "static", 255, 0, 0, 0)
        self.assertEqual(p.r, 255)

    def test_r_at_lower_bound_0_is_valid(self) -> None:
        """r=0 (lower bound) should be accepted."""
        p = Profile("X", "static", 0, 0, 0, 0)
        self.assertEqual(p.r, 0)

    def test_r_out_of_range_256_raises_profile_error(self) -> None:
        """r=256 (above range) should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("X", "static", 256, 0, 0, 0)

    def test_g_negative_raises_profile_error(self) -> None:
        """g=-1 (below range) should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("X", "static", 0, -1, 0, 0)

    def test_b_value_128_is_valid(self) -> None:
        """b=128 (mid-range) should be accepted."""
        p = Profile("X", "static", 0, 0, 128, 0)
        self.assertEqual(p.b, 128)

    def test_all_rgb_at_255_is_valid(self) -> None:
        """Full white (255, 255, 255) should be accepted."""
        p = Profile("X", "static", 255, 255, 255, 0)
        self.assertEqual((p.r, p.g, p.b), (255, 255, 255))


class TestProfileSpeedValidation(unittest.TestCase):
    """Tests for Profile speed field validation (must be 0, 1, or 2)."""

    def test_speed_0_is_valid(self) -> None:
        """speed=0 should be accepted."""
        p = Profile("X", "static", 0, 0, 0, 0)
        self.assertEqual(p.speed, 0)

    def test_speed_1_is_valid(self) -> None:
        """speed=1 should be accepted."""
        p = Profile("X", "static", 0, 0, 0, 1)
        self.assertEqual(p.speed, 1)

    def test_speed_2_is_valid(self) -> None:
        """speed=2 should be accepted."""
        p = Profile("X", "color_cycle", 0, 0, 0, 2)
        self.assertEqual(p.speed, 2)

    def test_speed_3_raises_profile_error(self) -> None:
        """speed=3 (above range) should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("X", "static", 0, 0, 0, 3)

    def test_speed_negative_raises_profile_error(self) -> None:
        """speed=-1 (below range) should raise ProfileError."""
        with self.assertRaises(ProfileError):
            Profile("X", "static", 0, 0, 0, -1)


class TestProfileSerialization(unittest.TestCase):
    """Tests for Profile serialization via dataclasses.asdict()."""

    def test_asdict_returns_exactly_6_keys(self) -> None:
        """dataclasses.asdict(profile) must return exactly 6 keys."""
        p = Profile("Work", "static", 255, 128, 0, 0)
        d = dataclasses.asdict(p)
        self.assertEqual(len(d), 6, f"Expected 6 keys, got {len(d)}: {list(d.keys())}")

    def test_asdict_contains_expected_keys(self) -> None:
        """asdict output must contain name, mode, r, g, b, speed."""
        p = Profile("Work", "static", 255, 128, 0, 0)
        d = dataclasses.asdict(p)
        self.assertEqual(set(d.keys()), {"name", "mode", "r", "g", "b", "speed"})

    def test_valid_modes_classvar_not_in_asdict(self) -> None:
        """VALID_MODES ClassVar must not appear in asdict output."""
        p = Profile("X", "static", 0, 0, 0, 0)
        d = dataclasses.asdict(p)
        self.assertNotIn("VALID_MODES", d)

    def test_asdict_values_are_json_serializable(self) -> None:
        """All asdict values must be JSON-serializable (str, int)."""
        import json

        p = Profile("Work", "static", 255, 128, 0, 0)
        d = dataclasses.asdict(p)
        # Should not raise
        json.dumps(d)

    def test_roundtrip_equality(self) -> None:
        """Profile(**asdict(p)) == p must hold."""
        p = Profile("X", "static", 0, 0, 0, 0)
        d = dataclasses.asdict(p)
        p2 = Profile(**d)
        self.assertEqual(p, p2)

    def test_roundtrip_with_all_fields(self) -> None:
        """Roundtrip must hold for a fully populated profile."""
        p = Profile("Gaming", "breathing", 200, 100, 50, 1)
        d = dataclasses.asdict(p)
        self.assertEqual(Profile(**d), p)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for BacklightController.

All tests run without hardware or root privileges by injecting a temp-file path
at construction time (BacklightController(sysfs_path=...)).  No test writes to
/sys or requires any kernel module.
"""

import os
import tempfile
import unittest
from pathlib import Path

from kbd_backlight.hardware.backlight import (
    BacklightController,
    HardwareNotFoundError,
    MODES,
)


def make_mock_sysfs() -> str:
    """Create a writable temp file simulating the sysfs attribute."""
    tmpdir = tempfile.mkdtemp()
    mock_path = os.path.join(tmpdir, "kbd_rgb_mode")
    Path(mock_path).touch()
    return mock_path


class TestBacklightControllerModes(unittest.TestCase):
    """Verify that each mode produces the correct integer payload."""

    def setUp(self) -> None:
        self.mock_path = make_mock_sysfs()
        self.ctrl = BacklightController(sysfs_path=self.mock_path)

    def _read_payload(self) -> str:
        return Path(self.mock_path).read_text()

    def test_apply_static_mode(self) -> None:
        """apply(static) writes cmd=0, mode=0."""
        self.ctrl.apply("static", r=255, g=0, b=128, speed=0)
        self.assertEqual(self._read_payload(), "0 0 255 0 128 0\n")

    def test_apply_breathing_mode(self) -> None:
        """apply(breathing) writes cmd=0, mode=1."""
        self.ctrl.apply("breathing", r=0, g=255, b=0, speed=1)
        self.assertEqual(self._read_payload(), "0 1 0 255 0 1\n")

    def test_apply_color_cycle_mode(self) -> None:
        """apply(color_cycle) writes cmd=0, mode=2."""
        self.ctrl.apply("color_cycle", r=0, g=0, b=0, speed=2)
        self.assertEqual(self._read_payload(), "0 2 0 0 0 2\n")

    def test_apply_strobe_mode(self) -> None:
        """apply(strobe) writes cmd=0, mode=3 (hardware behavior untested here)."""
        self.ctrl.apply("strobe", r=128, g=128, b=128, speed=0)
        self.assertEqual(self._read_payload(), "0 3 128 128 128 0\n")

    def test_all_modes_produce_correct_mode_integer(self) -> None:
        """Each mode name maps to the correct integer at payload position 1."""
        for mode_name, mode_int in MODES.items():
            with self.subTest(mode=mode_name):
                ctrl = BacklightController(sysfs_path=make_mock_sysfs())
                ctrl.apply(mode_name, r=0, g=0, b=0, speed=0)
                payload = Path(ctrl.path).read_text()
                parts = payload.strip().split()
                self.assertEqual(int(parts[1]), mode_int)


class TestBacklightControllerPersist(unittest.TestCase):
    """Verify the persist flag maps correctly to cmd=0 / cmd=1."""

    def setUp(self) -> None:
        self.mock_path = make_mock_sysfs()
        self.ctrl = BacklightController(sysfs_path=self.mock_path)

    def _read_payload(self) -> str:
        return Path(self.mock_path).read_text()

    def test_persist_false_uses_cmd_0(self) -> None:
        """persist=False (default) writes cmd=0 (live preview)."""
        self.ctrl.apply("static", r=1, g=2, b=3, speed=0, persist=False)
        self.assertTrue(self._read_payload().startswith("0 "))

    def test_persist_true_uses_cmd_1(self) -> None:
        """persist=True writes cmd=1 (saved to firmware)."""
        self.ctrl.apply("static", r=1, g=2, b=3, speed=0, persist=True)
        self.assertTrue(self._read_payload().startswith("1 "))


class TestBacklightControllerValidation(unittest.TestCase):
    """Verify that invalid inputs raise ValueError with descriptive messages."""

    def setUp(self) -> None:
        self.ctrl = BacklightController(sysfs_path=make_mock_sysfs())

    def test_invalid_mode_raises(self) -> None:
        """Unknown mode raises ValueError mentioning the invalid name and valid modes."""
        with self.assertRaisesRegex(ValueError, r"rainbow") as ctx:
            self.ctrl.apply("rainbow", r=0, g=0, b=0, speed=0)
        self.assertIn("Valid modes", str(ctx.exception))

    def test_invalid_rgb_low(self) -> None:
        """r=-1 raises ValueError."""
        with self.assertRaises(ValueError):
            self.ctrl.apply("static", r=-1, g=0, b=0, speed=0)

    def test_invalid_rgb_high(self) -> None:
        """r=256 raises ValueError."""
        with self.assertRaises(ValueError):
            self.ctrl.apply("static", r=256, g=0, b=0, speed=0)

    def test_invalid_speed(self) -> None:
        """speed=3 raises ValueError."""
        with self.assertRaises(ValueError):
            self.ctrl.apply("static", r=0, g=0, b=0, speed=3)


class TestBacklightControllerMisc(unittest.TestCase):
    """Miscellaneous tests: HardwareNotFoundError type, path property."""

    def test_hardware_not_found_is_runtime_error_subclass(self) -> None:
        """HardwareNotFoundError must be a RuntimeError subclass."""
        self.assertTrue(issubclass(HardwareNotFoundError, RuntimeError))

    def test_hardware_not_found_message_contains_asus_nb_wmi(self) -> None:
        """HardwareNotFoundError message contains the kernel module name."""
        try:
            raise HardwareNotFoundError(
                "Could not find ASUS keyboard backlight device at "
                "/sys/class/leds/asus::kbd_backlight*/kbd_rgb_mode. "
                "Is the asus-nb-wmi kernel module loaded?"
            )
        except HardwareNotFoundError as exc:
            self.assertIn("asus-nb-wmi", str(exc))

    def test_path_property(self) -> None:
        """ctrl.path returns a Path instance equal to the injected mock path."""
        mock_path = make_mock_sysfs()
        ctrl = BacklightController(sysfs_path=mock_path)
        self.assertIsInstance(ctrl.path, Path)
        self.assertEqual(ctrl.path, Path(mock_path))


if __name__ == "__main__":
    unittest.main()

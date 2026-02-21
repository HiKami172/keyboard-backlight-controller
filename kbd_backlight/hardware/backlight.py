"""BacklightController — hardware abstraction for the ASUS keyboard backlight sysfs interface.

Writes validated backlight commands to /sys/class/leds/asus::kbd_backlight*/kbd_rgb_mode.
Discovers the sysfs path at init time via pathlib glob; no hardcoded paths in production code.
"""

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


class BacklightController:
    """Controls the ASUS keyboard RGB backlight via direct sysfs writes.

    Usage (production — auto-discovers sysfs path):
        ctrl = BacklightController()
        ctrl.apply("static", r=255, g=0, b=128, speed=0)

    Usage (testing — inject a mock sysfs path):
        ctrl = BacklightController(sysfs_path="/tmp/mock_kbd_rgb_mode")
        ctrl.apply("breathing", r=0, g=255, b=0, speed=1)
    """

    def __init__(self, sysfs_path: str | None = None) -> None:
        if sysfs_path is None:
            sysfs_path = self._discover()
        self._path = Path(sysfs_path)

    @staticmethod
    def _discover() -> str:
        """Glob for the sysfs attribute file; raise HardwareNotFoundError if absent."""
        matches = list(Path("/sys/class/leds").glob("asus::kbd_backlight*/kbd_rgb_mode"))
        if matches:
            return str(matches[0])
        raise HardwareNotFoundError(
            "Could not find ASUS keyboard backlight device at "
            "/sys/class/leds/asus::kbd_backlight*/kbd_rgb_mode. "
            "Is the asus-nb-wmi kernel module loaded?"
        )

    def apply(
        self,
        mode: str,
        r: int,
        g: int,
        b: int,
        speed: int,
        persist: bool = False,
    ) -> None:
        """Write a backlight command to the sysfs attribute file.

        Args:
            mode:    One of "static", "breathing", "color_cycle", "strobe".
            r:       Red component, 0–255.
            g:       Green component, 0–255.
            b:       Blue component, 0–255.
            speed:   Animation speed — 0 (slow), 1 (medium), 2 (fast).
            persist: False (default) writes cmd=0 (live preview, lost on reboot).
                     True writes cmd=1 (saved to firmware, survives reboot).
        """
        if mode not in MODES:
            raise ValueError(
                f"Unknown mode '{mode}'. Valid modes: {list(MODES)}"
            )
        if not all(0 <= c <= 255 for c in (r, g, b)):
            raise ValueError(
                f"RGB values must be 0\u2013255, got ({r}, {g}, {b})"
            )
        if speed not in (0, 1, 2):
            raise ValueError(
                f"Speed must be 0, 1, or 2, got {speed}"
            )

        cmd = 1 if persist else 0
        payload = f"{cmd} {MODES[mode]} {r} {g} {b} {speed}\n"

        try:
            self._path.write_text(payload)
        except PermissionError:
            raise PermissionError(
                f"Cannot write to {self._path}. "
                "Is the udev rule installed? Run: sudo install/setup-permissions.sh"
            )

    @property
    def path(self) -> Path:
        """Return the sysfs attribute Path (useful for testing and debugging)."""
        return self._path

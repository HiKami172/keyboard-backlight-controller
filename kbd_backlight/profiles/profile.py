"""Profile dataclass with __post_init__ validation.

Profile is the shared data shape used by ProfileManager, the GTK window,
and the tray. Validation here prevents bad data from reaching disk or hardware.

All validation uses ProfileError (a ValueError subclass) so callers can
catch either ProfileError specifically or ValueError broadly.
"""

import dataclasses
from typing import ClassVar


class ProfileError(ValueError):
    """Raised when Profile data is invalid."""


@dataclasses.dataclass
class Profile:
    """Keyboard backlight profile: name, animation mode, colour, and speed.

    Fields
    ------
    name  : Human-readable label (non-empty, non-whitespace-only).
    mode  : Animation mode — one of VALID_MODES.
    r     : Red channel, 0-255 inclusive.
    g     : Green channel, 0-255 inclusive.
    b     : Blue channel, 0-255 inclusive.
    speed : Animation speed — 0 (slow), 1 (medium), or 2 (fast).

    Serialization
    -------------
    Use ``dataclasses.asdict(profile)`` to get a JSON-serialisable dict
    with exactly 6 keys (VALID_MODES ClassVar is excluded automatically).
    Roundtrip: ``Profile(**dataclasses.asdict(p)) == p`` is guaranteed.
    """

    VALID_MODES: ClassVar[set[str]] = {"static", "breathing", "color_cycle", "strobe"}

    name: str
    mode: str
    r: int
    g: int
    b: int
    speed: int

    def __post_init__(self) -> None:
        """Validate all fields after dataclass construction."""
        if not self.name or not self.name.strip():
            raise ProfileError("Profile name cannot be empty")

        if self.mode not in self.VALID_MODES:
            raise ProfileError(
                f"Unknown mode '{self.mode}'. Valid: {sorted(self.VALID_MODES)}"
            )

        if not all(0 <= c <= 255 for c in (self.r, self.g, self.b)):
            raise ProfileError(
                f"RGB values must be 0-255, got ({self.r}, {self.g}, {self.b})"
            )

        if self.speed not in (0, 1, 2):
            raise ProfileError(f"Speed must be 0, 1, or 2, got {self.speed}")

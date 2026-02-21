"""kbd_backlight.profiles — Profile data layer.

Public API
----------
Profile        : Keyboard backlight profile dataclass.
ProfileError   : Raised when Profile data is invalid (ValueError subclass).
ProfileManager : Atomic JSON CRUD manager over ~/.config/kbd-backlight/profiles.json.
"""

from .profile import Profile, ProfileError
from .manager import ProfileManager

__all__ = ["Profile", "ProfileError", "ProfileManager"]

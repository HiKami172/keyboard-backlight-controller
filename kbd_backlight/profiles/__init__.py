"""kbd_backlight.profiles — Profile data layer.

Public API
----------
Profile       : Keyboard backlight profile dataclass.
ProfileError  : Raised when Profile data is invalid (ValueError subclass).

ProfileManager is added in Plan 02 to avoid forward-reference errors.
"""

from .profile import Profile, ProfileError

__all__ = ["Profile", "ProfileError"]

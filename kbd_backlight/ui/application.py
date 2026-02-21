import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw

from kbd_backlight.hardware.backlight import BacklightController, HardwareNotFoundError
from kbd_backlight.profiles.manager import ProfileManager


class Application(Adw.Application):
    """Main application — owns BacklightController and ProfileManager.

    One instance lives for the full process lifetime. The window and
    (in Phase 4) the tray both share these objects via the application.
    """

    APPLICATION_ID = "io.github.hikami.KbdBacklight"

    def __init__(self):
        super().__init__(application_id=self.APPLICATION_ID)
        self.connect('activate', self._on_activate)
        self._controller: BacklightController | None = None
        self._manager: ProfileManager = ProfileManager()
        self._window = None

    def _on_activate(self, app):
        # Lazy-init controller so HardwareNotFoundError surfaces at activate time
        # with a user-visible error, not at import time.
        if self._controller is None:
            try:
                self._controller = BacklightController()
            except HardwareNotFoundError as e:
                # Show error dialog then quit
                dialog = Adw.AlertDialog.new(
                    "Hardware Not Found",
                    str(e),
                )
                dialog.add_response("quit", "Quit")
                dialog.connect("response", lambda *_: self.quit())
                # Present requires a parent window — create a minimal one
                win = Adw.ApplicationWindow(application=app)
                win.present()
                dialog.present(win)
                return

        if self._window is None:
            # Import here to avoid circular at module level
            from .window import MainWindow
            self._window = MainWindow(
                application=app,
                controller=self._controller,
                manager=self._manager,
            )

        self._window.present()
        self._restore_last_profile()

    def _restore_last_profile(self):
        """Apply last-used profile to hardware on startup (PROF-04)."""
        # get_last_profile() returns a Profile object (or None), not a name string
        profile = self._manager.get_last_profile()
        if profile is None:
            return
        try:
            self._controller.apply(
                profile.mode, profile.r, profile.g, profile.b,
                profile.speed, persist=False,  # cmd=0 — restore display only
            )
        except Exception:
            pass  # Hardware unavailable; don't block startup

    def show_window(self):
        """Restore the main window from hidden state (called by Phase 4 tray icon)."""
        if self._window is not None:
            self._window.present()

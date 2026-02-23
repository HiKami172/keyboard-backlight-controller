import os
import sys
import json
import subprocess as subproc
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Adw, Gio, GLib

from kbd_backlight.hardware.backlight import BacklightController, HardwareNotFoundError
from kbd_backlight.profiles.manager import ProfileManager


class Application(Adw.Application):
    """Main application — owns BacklightController and ProfileManager.

    One instance lives for the full process lifetime. The window and
    the tray both share these objects via the application.
    """

    APPLICATION_ID = "io.github.hikami.KbdBacklight"

    def __init__(self):
        super().__init__(application_id=self.APPLICATION_ID)
        self.connect('activate', self._on_activate)
        self._controller: BacklightController | None = None
        self._manager: ProfileManager = ProfileManager()
        self._window = None
        self._tray_proc = None
        self._tray_buf = b''
        self._tray_only = '--tray-only' in sys.argv
        self._activated_once = False

    def _on_activate(self, app):
        # On re-activation (second+ launch attempt), just show the window.
        if self._activated_once:
            self.show_window()
            return

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

        # Hold the application alive when window is hidden (TRAY-05)
        self.hold()
        self._activated_once = True
        self._start_tray()

        if not self._tray_only:
            self._window.present()
            self._restore_last_profile()

    def _start_tray(self):
        """Launch tray.py as a subprocess with piped stdin/stdout.

        Uses subprocess.Popen + GLib.io_add_watch on the raw stdout fd — the
        same pattern tray.py uses to watch its own stdin.  This avoids the
        Gio.DataInputStream.read_line_async path which does not reliably fire
        its callback in all PyGObject environments.
        """
        tray_script = os.path.join(os.path.dirname(__file__), 'tray.py')
        self._tray_proc = subproc.Popen(
            [sys.executable, tray_script],
            stdin=subproc.PIPE,
            stdout=subproc.PIPE,
            bufsize=0,  # unbuffered — each write immediately visible to reader
        )
        GLib.io_add_watch(
            self._tray_proc.stdout.fileno(),
            GLib.IO_IN | GLib.IO_HUP,
            self._on_tray_data,
        )

    def _on_tray_data(self, fd, condition):
        """Read available bytes from tray stdout and dispatch complete lines."""
        if condition & GLib.IO_HUP:
            return False  # Subprocess exited — deregister watcher
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            return False
        if not chunk:
            return False
        self._tray_buf += chunk
        while b'\n' in self._tray_buf:
            line_bytes, self._tray_buf = self._tray_buf.split(b'\n', 1)
            self._dispatch_tray_line(line_bytes.decode('utf-8', errors='replace'))
        return True  # Keep watcher active

    def _dispatch_tray_line(self, line: str):
        """Dispatch a single decoded JSON line from the tray subprocess."""
        try:
            msg = json.loads(line)
            action = msg.get('action')
            if action == 'select_profile':
                self._apply_profile_by_name(msg['name'])
            elif action == 'show':
                self.show_window()
            elif action == 'quit':
                self._shutdown_tray()
                self.release()
                self.quit()
        except (json.JSONDecodeError, KeyError):
            pass

    def _apply_profile_by_name(self, name: str):
        """Apply a named profile to hardware and update last_profile. Called from tray."""
        profile = self._manager.get_profile(name)
        if profile is None:
            return
        try:
            self._controller.apply(
                profile.mode, profile.r, profile.g, profile.b,
                profile.speed, persist=True,  # cmd=1 — tray switch is an explicit action
            )
        except Exception:
            pass
        self._manager.set_last_profile(name)
        # Also update MainWindow controls if window exists and is visible
        if self._window is not None:
            self._window.load_profile_from_tray(profile)

    def _send_tray(self, message: str):
        """Write a newline-terminated message to tray subprocess stdin."""
        if self._tray_proc is None or self._tray_proc.stdin is None:
            return
        try:
            self._tray_proc.stdin.write((message + '\n').encode())
            self._tray_proc.stdin.flush()
        except OSError:
            pass

    def notify_tray_refresh(self):
        """Called by MainWindow after profile save/delete to rebuild tray menu."""
        self._send_tray('REFRESH')

    def _shutdown_tray(self):
        """Send QUIT to tray subprocess and wait for it to exit."""
        self._send_tray('QUIT')
        if self._tray_proc is not None:
            try:
                self._tray_proc.wait(timeout=2)
            except subproc.TimeoutExpired:
                self._tray_proc.kill()
            self._tray_proc = None

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
        """Restore the main window from hidden state (called by tray icon)."""
        if self._window is not None:
            self._window.present()

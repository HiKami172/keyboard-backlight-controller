"""GTK3 tray subprocess for keyboard backlight controller.

This module runs as a SEPARATE PROCESS — it MUST NOT import GTK4 or Adw.
AyatanaAppIndicator3 hard-links against libgtk-3.so.0, which cannot coexist
with GTK 4.0 in the same Python process.

Communication protocol (stdin/stdout JSON):
  Parent -> subprocess:
    "REFRESH\n"          — rebuild menu from disk
    "QUIT\n"             — exit Gtk.main() and return False from stdin watcher

  Subprocess -> parent:
    {"action": "select_profile", "name": "<name>"}  — user clicked a profile
    {"action": "show"}                                — user clicked Open Settings
    {"action": "quit"}                                — user clicked Quit
"""

import sys
import os
import json
import pathlib

import gi
gi.require_version('AyatanaAppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import AyatanaAppIndicator3, Gtk, GdkPixbuf, GLib

# ProfileManager only uses stdlib (json, pathlib, dataclasses) — safe to import here.
# Insert project root so we can import kbd_backlight.profiles.manager regardless of cwd.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from kbd_backlight.profiles.manager import ProfileManager


class TrayProcess:
    """GTK3 AppIndicator tray for the keyboard backlight controller.

    Lifecycle:
      1. __init__ creates the indicator and registers the stdin watcher.
      2. Caller invokes Gtk.main() — the event loop runs until Gtk.main_quit().
      3. When the parent sends "QUIT\n", _on_stdin calls Gtk.main_quit() and
         returns False (deregisters the GLib watch).
    """

    def __init__(self) -> None:
        self._manager = ProfileManager()

        # Create AyatanaAppIndicator3 indicator in the HARDWARE category.
        self._indicator = AyatanaAppIndicator3.Indicator.new(
            'kbd-backlight',
            'input-keyboard',
            AyatanaAppIndicator3.IndicatorCategory.HARDWARE,
        )
        self._indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)

        # Build initial menu and watch stdin for commands from parent.
        self._build_menu()
        GLib.io_add_watch(sys.stdin.fileno(), GLib.IO_IN, self._on_stdin)

    # ------------------------------------------------------------------
    # Menu construction
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        """Build (or rebuild) the tray right-click menu from disk profiles."""
        menu = Gtk.Menu()

        profiles = self._manager.get_all_profiles()
        if profiles:
            for name, profile in sorted(profiles.items()):
                item = self._make_profile_item(name, profile.r, profile.g, profile.b)
                menu.append(item)
        else:
            placeholder = Gtk.MenuItem(label='(no profiles)')
            placeholder.set_sensitive(False)
            menu.append(placeholder)

        menu.append(Gtk.SeparatorMenuItem())

        # "Open Settings" — tells parent to raise the main window.
        settings_item = Gtk.MenuItem(label='Open Settings')
        settings_item.connect('activate', lambda _: self._send(json.dumps({'action': 'show'})))
        menu.append(settings_item)

        # "Quit" — tells parent to quit, then exits this subprocess.
        quit_item = Gtk.MenuItem(label='Quit')
        quit_item.connect(
            'activate',
            lambda _: (self._send(json.dumps({'action': 'quit'})), Gtk.main_quit()),
        )
        menu.append(quit_item)

        # CRITICAL: show_all() MUST be called before set_menu() — AppIndicator spec.
        menu.show_all()
        self._indicator.set_menu(menu)

        # Keep a reference to prevent garbage collection before GTK is done.
        self._menu = menu

    def _make_profile_item(self, name: str, r: int, g: int, b: int) -> Gtk.MenuItem:
        """Create a Gtk.MenuItem with a 16x16 color swatch and profile label.

        For color_cycle profiles (r=g=b=0 — hardware cycles colors, no fixed RGB),
        a neutral gray swatch (128, 128, 128) is displayed instead of black.
        """
        item = Gtk.MenuItem()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Build the color swatch pixbuf.
        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 16, 16)
        if r == 0 and g == 0 and b == 0:
            # Gray swatch for color_cycle profiles — otherwise swatch is invisible black.
            packed = (128 << 24) | (128 << 16) | (128 << 8) | 0xFF
        else:
            # RGBA packing: (r<<24)|(g<<16)|(b<<8)|0xFF — alpha=0xFF=fully opaque.
            packed = (r << 24) | (g << 16) | (b << 8) | 0xFF
        pixbuf.fill(packed)

        image = Gtk.Image.new_from_pixbuf(pixbuf)
        label = Gtk.Label(label=name)
        label.set_xalign(0)  # Left-align label text inside the menu item.

        box.pack_start(image, False, False, 0)
        box.pack_start(label, True, True, 0)
        item.add(box)
        item.connect('activate', lambda _, n=name: self._on_profile_clicked(n))
        return item

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_profile_clicked(self, name: str) -> None:
        """Send profile-selection action to parent process via stdout."""
        self._send(json.dumps({'action': 'select_profile', 'name': name}))

    def _on_stdin(self, fd: int, condition: GLib.IOCondition) -> bool:
        """Read one command line from stdin and dispatch.

        Returns True to keep the GLib watch active.
        Returns False only on QUIT — deregisters the watch and quits Gtk.main().
        """
        line = sys.stdin.readline().strip()
        if line == 'REFRESH':
            self._build_menu()
        elif line == 'QUIT':
            Gtk.main_quit()
            return False  # Deregister the GLib.io_add_watch watcher.
        return True  # Keep watching stdin for further commands.

    # ------------------------------------------------------------------
    # IPC helpers
    # ------------------------------------------------------------------

    def _send(self, message: str) -> None:
        """Write a JSON message line to stdout for the parent process to read.

        flush=True is mandatory — without it, output is buffered and the parent
        would never see the message until the buffer fills or the process exits.
        """
        print(message, flush=True)


if __name__ == '__main__':
    TrayProcess()
    Gtk.main()

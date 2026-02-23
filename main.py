#!/usr/bin/env python3
"""ASUS TUF F16 Keyboard Backlight Controller — entry point."""
import sys

from kbd_backlight.ui.application import Application


def main():
    app = Application()
    # Strip --tray-only before passing argv to GLib; Application reads it
    # directly from sys.argv before app.run() is called.
    argv = [a for a in sys.argv if a != '--tray-only']
    sys.exit(app.run(argv))


if __name__ == '__main__':
    main()

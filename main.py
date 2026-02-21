#!/usr/bin/env python3
"""ASUS TUF F16 Keyboard Backlight Controller — entry point."""
import sys

from kbd_backlight.ui.application import Application


def main():
    app = Application()
    sys.exit(app.run(sys.argv))


if __name__ == '__main__':
    main()

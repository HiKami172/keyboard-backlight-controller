#!/usr/bin/env bash
# install-autostart.sh — installs XDG autostart entry for kbd-backlight
# Run from anywhere; resolves paths dynamically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MAIN_PY="$PROJECT_DIR/main.py"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/kbd-backlight.desktop"
PYTHON3="$(command -v python3)"

if [[ ! -f "$MAIN_PY" ]]; then
    echo "ERROR: main.py not found at $MAIN_PY" >&2
    exit 1
fi

mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Keyboard Backlight Controller
Comment=Keyboard backlight controller — runs in system tray
Exec=$PYTHON3 $MAIN_PY --tray-only
Icon=input-keyboard
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

chmod 644 "$DESKTOP_FILE"
echo "Installed: $DESKTOP_FILE"
echo "Exec: $PYTHON3 $MAIN_PY --tray-only"
echo "The app will start automatically in tray-only mode on next login."

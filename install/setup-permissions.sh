#!/usr/bin/env bash
# setup-permissions.sh — Install udev rule for ASUS TUF keyboard backlight access.
#
# Usage: sudo install/setup-permissions.sh
#
# What this script does:
#   1. Copies 99-kbd-backlight.rules to /etc/udev/rules.d/
#   2. Reloads udev rules
#   3. Triggers the add event to apply permissions immediately (no reboot needed)
#   4. Adds the original user to the plugdev group
#
# After running, log out and back in for group membership to take effect.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULE_FILE="99-kbd-backlight.rules"
RULE_SRC="${SCRIPT_DIR}/${RULE_FILE}"
RULE_DST="/etc/udev/rules.d/${RULE_FILE}"

# --- Root check ---
if [[ "${EUID}" -ne 0 ]]; then
    echo "Error: This script must be run as root." >&2
    echo "Usage: sudo ${BASH_SOURCE[0]}" >&2
    exit 1
fi

# --- Copy udev rule ---
echo "Copying ${RULE_FILE} to ${RULE_DST} ..."
cp "${RULE_SRC}" "${RULE_DST}"
echo "Done."

# --- Reload udev rules ---
echo "Reloading udev rules ..."
udevadm control --reload-rules
echo "Done."

# --- Trigger add event to apply permissions immediately ---
echo "Triggering add event for asus::kbd_backlight ..."
udevadm trigger --action=add /sys/class/leds/asus::kbd_backlight
echo "Done."

# --- Add user to plugdev group ---
if [[ -n "${SUDO_USER:-}" ]]; then
    echo "Adding ${SUDO_USER} to the plugdev group ..."
    usermod -aG plugdev "${SUDO_USER}"
    echo "Done."
else
    echo "Warning: SUDO_USER is not set; could not determine the original user." >&2
    echo "Manually run: sudo usermod -aG plugdev \$USER" >&2
fi

# --- Success message ---
echo ""
echo "Setup complete."
echo ""
echo "IMPORTANT: Log out and back in for the plugdev group membership to take effect."
echo "After logging back in, the keyboard backlight control will be available without sudo."

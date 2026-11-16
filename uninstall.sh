#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Removes the helper's service and command. Keeps ~/.config/dsf-bridge (pairings) unless --purge.
# Never touches the game; to remove DS Forever's add-ons delete Interface/AddOns/WowCompanion* yourself.
set -u
case "${1:-}" in ""|--purge) ;; *) echo "usage: $0 [--purge]"; exit 1;; esac
systemctl --user disable --now dsf-bridge.service 2>/dev/null
rm -f "$HOME/.config/systemd/user/dsf-bridge.service" "$HOME/.local/bin/dsf-bridge"
systemctl --user daemon-reload
[ "${1:-}" = "--purge" ] && rm -rf "$HOME/.config/dsf-bridge" "$HOME/.cache/dsf-bridge"
echo "DS Forever helper removed."

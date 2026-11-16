#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# DS Forever helper for Linux: one-command install. No root needed.
# Sets up a Python venv here, the `dsf-bridge` command in ~/.local/bin and a systemd user service.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CFG="$HOME/.config/dsf-bridge"
echo "== DS Forever helper for Linux"
command -v python3 >/dev/null || { echo "python3 is missing: install it with your package manager"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || { echo "Python 3.10 or newer needed"; exit 1; }

python3 -c 'import venv, ensurepip' 2>/dev/null || { echo "Python's venv module is missing: install python3-venv (Debian/Ubuntu) or python3-virtualenv, then run this again"; exit 1; }
for t in pgrep ss ip; do command -v $t >/dev/null || echo "note: '$t' is missing (procps / iproute2); WoW detection needs it"; done
echo "-- Python environment"
python3 -m venv --clear "$HERE/.venv"
"$HERE/.venv/bin/pip" install -q --disable-pip-version-check -r "$HERE/requirements.txt"

echo "-- dsf-bridge command"
mkdir -p "$HOME/.local/bin" "$CFG"
cat > "$HOME/.local/bin/dsf-bridge" <<EOS
#!/bin/sh
exec "$HERE/.venv/bin/python" "$HERE/dsf_bridge.py" "\$@"
EOS
chmod +x "$HOME/.local/bin/dsf-bridge"
[ -f "$CFG/env" ] || cp "$HERE/env.example" "$CFG/env"
chmod 600 "$CFG/env"

echo "-- service"
mkdir -p "$HOME/.config/systemd/user"
sed "s|@HERE@|$HERE|g" "$HERE/dsf-bridge.service" > "$HOME/.config/systemd/user/dsf-bridge.service"
systemctl --user daemon-reload
systemctl --user enable --now dsf-bridge.service
systemctl --user restart dsf-bridge.service
sleep 3

echo
"$HOME/.local/bin/dsf-bridge" doctor || true
echo
"$HOME/.local/bin/dsf-bridge" code || true
echo "On the Thor: DS Forever → Streaming → enter that code. Full guide: $HERE/README.md"

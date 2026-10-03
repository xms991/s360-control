#!/usr/bin/env bash
# Set up MSI MEG CoreLiquid S360 control (fan curves + temperature feed)
# from scratch on a fresh Linux install.  Idempotent: safe to re-run.
#
# Requires: git, curl, python3, and sudo (only for the udev rule).

set -euo pipefail
cd "$(dirname "$0")"

PIP="python3 -m pip"
PIP_FLAGS="--user --break-system-packages"

echo "==> Ensuring pip"
if ! $PIP --version >/dev/null 2>&1; then
    curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py --user --break-system-packages
fi

echo "==> Installing Python dependencies"
$PIP install $PIP_FLAGS colorlog crcmod==1.7 docopt hidapi pyusb pillow smbus2

# liquidctl imports `from smbus import SMBus`; smbus2 is a drop-in replacement.
if ! python3 -c "from smbus import SMBus" >/dev/null 2>&1; then
    SITE=$(python3 -m site --user-site)
    mkdir -p "$SITE"
    printf 'from smbus2 import SMBus  # noqa: F401\n' > "$SITE/smbus.py"
fi

echo "==> Fetching liquidctl with S360 support"
if [ ! -d liquidctl ]; then
    git clone https://github.com/liquidctl/liquidctl.git liquidctl
    cd liquidctl
    # PR #784 (closed unmerged): adds USB ID 0db0:6a05 to the MSI driver
    git fetch origin pull/784/head
    git checkout -b s360-fixes FETCH_HEAD
    git apply ../patches/s360-fixes.patch
    cd ..
fi

echo "==> Installing liquidctl (editable, user site)"
(cd liquidctl && $PIP install $PIP_FLAGS --no-deps -e .)

echo "==> Installing udev rule (sudo required)"
sudo install -m644 udev/72-liquidctl-s360.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger

echo "==> Installing systemd user service"
mkdir -p "$HOME/.config/systemd/user"
cp s360-fancontrol.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now s360-fancontrol
loginctl enable-linger "$USER" || echo "    (enable-linger failed; service will only run while logged in)"

echo "==> Done. Verify with:  ~/.local/bin/liquidctl status"

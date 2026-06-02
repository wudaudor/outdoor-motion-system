#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/outdoor_monitor}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"

say() {
    printf '\n==> %s\n' "$*"
}

if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required. Please install sudo or run the apt steps as root."
    exit 1
fi

sudo() {
    if [ -n "${SUDO_PASSWORD:-}" ]; then
        printf '%s\n' "$SUDO_PASSWORD" | command sudo -S -p '' "$@"
    else
        command sudo "$@"
    fi
}

say "Host check"
echo "Machine: $(uname -m)"
if [ "$(uname -m)" != "riscv64" ]; then
    echo "Warning: this script is intended for VisionFive 2 Debian on riscv64."
fi
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "OS: ${PRETTY_NAME:-unknown}"
fi

say "Updating apt package indexes"
sudo apt-get update

say "Installing required runtime packages"
ESSENTIAL_PACKAGES=(
    python3
    python3-pip
    python3-venv
    python3-opencv
    libopencv-dev
    libhdf5-103-1
    libvtk9.1
    libvtk9.1-qt
    libqt5test5
    libqt5opengl5
    libtesseract5
    libgdal32
    python3-numpy
    python3-requests
    python3-flask
    v4l-utils
    ffmpeg
    gpiod
    usbutils
    curl
    wget
    ca-certificates
    screen
    vim
    unzip
    locales
    fontconfig
)
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${ESSENTIAL_PACKAGES[@]}"

say "Installing Chinese locale, fonts, and input method packages"
CHINESE_PACKAGES=(
    fonts-noto-cjk
    fonts-wqy-zenhei
    fonts-wqy-microhei
    fcitx5
    fcitx5-chinese-addons
    fcitx5-pinyin
    im-config
)
if [ "${INSTALL_FULL_CHINESE_TASK:-0}" = "1" ]; then
    CHINESE_PACKAGES+=(task-chinese-s)
fi

AVAILABLE_CHINESE_PACKAGES=()
for pkg in "${CHINESE_PACKAGES[@]}"; do
    if apt-cache show "$pkg" >/dev/null 2>&1; then
        AVAILABLE_CHINESE_PACKAGES+=("$pkg")
    else
        echo "Optional package not found in current apt sources: $pkg"
    fi
done

if [ "${#AVAILABLE_CHINESE_PACKAGES[@]}" -gt 0 ]; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${AVAILABLE_CHINESE_PACKAGES[@]}"
fi

say "Enabling zh_CN.UTF-8"
if ! grep -Eq '^zh_CN\.UTF-8 UTF-8' /etc/locale.gen; then
    echo "zh_CN.UTF-8 UTF-8" | sudo tee -a /etc/locale.gen >/dev/null
fi
sudo locale-gen zh_CN.UTF-8
sudo update-locale LANG=zh_CN.UTF-8 LC_CTYPE=zh_CN.UTF-8 || echo "Warning: update-locale failed; zh_CN.UTF-8 was still generated."
sudo localectl set-locale LANG=zh_CN.UTF-8 2>/dev/null || true
fc-cache -fv >/dev/null 2>&1 || true
if command -v im-config >/dev/null 2>&1; then
    im-config -n fcitx5 || true
fi

say "Adding current user to useful hardware groups when they exist"
for group in video gpio i2c; do
    if getent group "$group" >/dev/null 2>&1; then
        sudo usermod -aG "$group" "$USER"
    fi
done

say "Preparing application directory"
mkdir -p "$APP_DIR/data/snapshots" "$APP_DIR/data/videos" "$APP_DIR/data/logs"

say "Creating Python virtual environment"
python3 -m venv --system-site-packages "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install --upgrade requests flask

say "Installing VisionFive.gpio"
"$VENV_DIR/bin/python" - <<'PY'
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request

PACKAGE = "VisionFive.gpio"
PYPI_JSON = f"https://pypi.org/pypi/{PACKAGE}/json"
PLATFORM_TAG = "linux_riscv64"
abi_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"

print(f"Python ABI: {abi_tag}")
print(f"Machine: {platform.machine()}")

with urllib.request.urlopen(PYPI_JSON, timeout=30) as response:
    metadata = json.load(response)

latest = metadata["info"]["version"]
versions = [latest] + [v for v in metadata["releases"] if v != latest]
candidate = None

for version in versions:
    for item in metadata["releases"].get(version, []):
        filename = item.get("filename", "")
        if not filename.endswith(".whl"):
            continue
        if abi_tag not in filename:
            continue
        if PLATFORM_TAG in filename or filename.endswith("-any.whl"):
            candidate = item
            break
    if candidate:
        break

if not candidate:
    raise SystemExit(
        f"No {PACKAGE} wheel found for {abi_tag}. "
        "Try upgrading the VisionFive Debian image or Python version."
    )

wheel_name = candidate["filename"]
install_name = wheel_name.replace("-any.whl", f"-{PLATFORM_TAG}.whl")

with tempfile.TemporaryDirectory() as tmpdir:
    wheel_path = os.path.join(tmpdir, install_name)
    print(f"Downloading: {wheel_name}")
    urllib.request.urlretrieve(candidate["url"], wheel_path)
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        wheel_path,
    ])

import VisionFive.gpio  # noqa: F401
print("VisionFive.gpio import OK")
PY

say "Verifying Python modules"
"$VENV_DIR/bin/python" - <<'PY'
import cv2
import flask
import numpy
import requests

print("cv2:", cv2.__version__)
print("numpy:", numpy.__version__)
print("requests:", requests.__version__)
print("flask:", flask.__version__)
PY

cat <<EOF

Done.

App dir: $APP_DIR
Python:  $VENV_DIR/bin/python

Please log out and log back in, or reboot once, so Chinese locale and hardware
group changes take effect.
EOF

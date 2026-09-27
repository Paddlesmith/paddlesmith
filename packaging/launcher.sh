#!/bin/sh
# Paddlesmith launcher (becomes Contents/MacOS/paddlesmith in the app).
# Code lives in Contents/Resources/app; the Python environment with PyQt5
# and the backups live in ~/Library/Application Support/Paddlesmith.
APP="$(cd "$(dirname "$0")/../Resources/app" && pwd)"
SUPPORT="$HOME/Library/Application Support/Paddlesmith"
VENV="$SUPPORT/venv"

alert() {
  osascript -e "display alert \"Paddlesmith\" message \"$1\"" >/dev/null 2>&1
}

# /usr/bin/python3 is only a stub until Apple's Command Line Tools are
# installed. Offer to install them instead of failing obscurely.
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install >/dev/null 2>&1
  alert "Paddlesmith needs Apple's free Command Line Tools. An installer window has opened: click Install, wait for it to finish, then open Paddlesmith again."
  exit 0
fi

# Script apps can be started under Rosetta; force native arch on Apple silicon
# so Python matches the PyQt5 build installed for it.
ARCH=""
[ "$(sysctl -n hw.optional.arm64 2>/dev/null)" = "1" ] && ARCH="arch -arm64"

mkdir -p "$SUPPORT"
if ! $ARCH "$VENV/bin/python" -c "import PyQt5.QtWidgets" 2>/dev/null; then
  osascript -e 'display notification "First launch: downloading components (about a minute)…" with title "Paddlesmith"' >/dev/null 2>&1
  { rm -rf "$VENV" \
    && $ARCH /usr/bin/python3 -m venv "$VENV" \
    && $ARCH "$VENV/bin/python" -m pip install -q --upgrade pip \
    && $ARCH "$VENV/bin/python" -m pip install -q PyQt5; } > "$SUPPORT/setup.log" 2>&1 || {
    alert "First-time setup failed. Check your internet connection and try again. Details: ~/Library/Application Support/Paddlesmith/setup.log"
    exit 1; }
fi

cd "$APP" || exit 1
exec $ARCH "$VENV/bin/python" ./flydigi-gui

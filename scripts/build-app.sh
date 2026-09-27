#!/bin/sh
# Build dist/Paddlesmith.app and a zip ready to attach to a GitHub release.
#
#   scripts/build-app.sh [version]
#
# Needs a Python with PyQt5 only to draw the icon (uses .venv if present).
set -e
cd "$(dirname "$0")/.."
VERSION="${1:-0.1.0}"
APP="dist/Paddlesmith.app"

rm -rf dist && mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/app"

rsync -a --exclude __pycache__ --exclude 'assets/*.png' \
  flydigi flydigi-cli flydigi-gui LICENSE NOTICE.md README.md \
  "$APP/Contents/Resources/app/"
cp packaging/launcher.sh "$APP/Contents/MacOS/paddlesmith"
chmod +x "$APP/Contents/MacOS/paddlesmith"
sed "s/@VERSION@/$VERSION/" packaging/Info.plist > "$APP/Contents/Info.plist"

# Icon: drawn by tools/make-icon.py (original artwork).
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
SET="$(mktemp -d)/icon.iconset"; mkdir -p "$SET"
QT_QPA_PLATFORM=offscreen "$PY" - "$SET" <<'EOF' 2>/dev/null
import sys, importlib.util as u
from PyQt5.QtWidgets import QApplication
app = QApplication([])
s = u.spec_from_file_location("mi", "tools/make-icon.py")
m = u.module_from_spec(s); s.loader.exec_module(m)
out = sys.argv[1]
for n in (16, 32, 128, 256, 512):
    m.draw(n).save(f"{out}/icon_{n}x{n}.png")
    m.draw(n * 2).save(f"{out}/icon_{n}x{n}@2x.png")
EOF
iconutil -c icns "$SET" -o "$APP/Contents/Resources/icon.icns"

# Ad-hoc signature: not notarized, but keeps the bundle consistent.
codesign --force --deep -s - "$APP" 2>/dev/null || true

ditto -c -k --keepParent "$APP" "dist/Paddlesmith-$VERSION.zip"
echo "Built $APP and dist/Paddlesmith-$VERSION.zip"

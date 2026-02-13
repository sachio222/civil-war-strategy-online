#!/usr/bin/env bash
# Build CWS: Civil War Strategy as a standalone desktop app.
# Usage: ./build.sh
# Output: dist/CWS Civil War Strategy (.exe on Windows, .app on Mac)

set -e

echo "=== CWS Desktop App Builder ==="
echo ""

# Install build dependencies
echo "Installing dependencies..."
pip install pyinstaller pygame-ce

# Build
echo ""
echo "Building..."
pyinstaller cws.spec --clean

echo ""
echo "=== Build complete! ==="
echo "Output is in the dist/ folder."

if [ "$(uname)" = "Darwin" ]; then
    echo "  Mac app:  dist/CWS Civil War Strategy.app"
else
    echo "  Binary:   dist/CWS Civil War Strategy"
fi

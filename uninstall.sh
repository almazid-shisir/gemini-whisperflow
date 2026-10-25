#!/bin/bash
# ==============================================================================
# Gemini WhisperFlow Linux Uninstaller
# Clean removal of background services, virtual environment, and CLI tools
# ==============================================================================

set -e

INSTALL_DIR="$HOME/.local/share/gemini-voice-flow"
CONFIG_DIR="$HOME/.config/gemini-voice-flow"
BIN_DIR="$HOME/.local/bin"
SERVICE_FILE="$HOME/.config/systemd/user/gemini-voice-flow.service"
AUTOSTART_FILE="$HOME/.config/autostart/gemini-whisperflow.desktop"
APP_FILE="$HOME/.local/share/applications/gemini-whisperflow.desktop"

echo ""
echo "======================================================================"
echo "🗑️  Uninstalling Gemini WhisperFlow"
echo "======================================================================"
echo ""

# 1. Stop and disable systemd service
if command -v systemctl &>/dev/null && [ -d /run/user/"$(id -u)" ]; then
  echo "[1/4] Stopping and disabling background service..."
  systemctl --user stop gemini-voice-flow.service 2>/dev/null || true
  systemctl --user disable gemini-voice-flow.service 2>/dev/null || true
  rm -f "$SERVICE_FILE"
  systemctl --user daemon-reload 2>/dev/null || true
fi

# Kill any lingering background process
pkill -f "gemini_flow.py" 2>/dev/null || true

# 2. Remove desktop autostart & launcher entries
echo "[2/4] Removing autostart and desktop application shortcuts..."
rm -f "$AUTOSTART_FILE"
rm -f "$APP_FILE"

# 3. Remove CLI binary and virtual environment
echo "[3/4] Removing CLI binary and Python runtime..."
rm -f "$BIN_DIR/gemini-flow"
rm -rf "$INSTALL_DIR"

# 4. Handle configuration & API keys
echo "[4/4] Configuration cleanup..."
if [ -d "$CONFIG_DIR" ]; then
  echo ""
  read -p "Would you like to delete your configuration & saved API key (~/.config/gemini-voice-flow)? [y/N]: " REMOVE_CONFIG
  case "$REMOVE_CONFIG" in
    [yY]|[yY][eE][sS])
      rm -rf "$CONFIG_DIR"
      echo "✅ Configuration directory removed."
      ;;
    *)
      echo "ℹ️  Preserved configuration at: $CONFIG_DIR"
      ;;
  esac
fi

echo ""
echo "======================================================================"
echo "✅ Gemini WhisperFlow has been cleanly uninstalled from your system."
echo "======================================================================"
echo ""

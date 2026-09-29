#!/bin/bash
set -e

echo "=============================================="
echo "   Installing Gemini WhisperFlow for Linux    "
echo "=============================================="

# 1. System packages check
echo "[1/4] Checking required system tools..."
MISSING=""
for cmd in arecord xdotool xclip notify-send python3; do
  if ! command -v $cmd &>/dev/null; then
    MISSING="$MISSING $cmd"
  fi
done

if [ -n "$MISSING" ]; then
  echo "⚠️ Missing system packages:$MISSING"
  echo "Installing via apt..."
  sudo apt-get update && sudo apt-get install -y alsa-utils xdotool xclip libnotify-bin python3-venv
fi

# 2. Setup Python Virtual Environment
echo "[2/4] Setting up Python virtual environment..."
INSTALL_DIR="$HOME/.local/share/gemini-voice-flow"
mkdir -p "$INSTALL_DIR"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r requirements.txt

# 3. Setup Configuration
echo "[3/4] Initializing configuration..."
CONFIG_DIR="$HOME/.config/gemini-voice-flow"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
  cp config.example.json "$CONFIG_DIR/config.json"
  echo "📝 Created default config at: $CONFIG_DIR/config.json"
  echo "👉 Please edit $CONFIG_DIR/config.json and set your 'gemini_api_key'!"
fi

# 4. Install CLI command & Systemd service
echo "[4/4] Setting up CLI and autostart service..."
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
cp gemini-flow "$HOME/.local/bin/gemini-flow"
chmod +x "$HOME/.local/bin/gemini-flow"

sed "s|%h|$HOME|g" gemini-whisperflow.service > "$HOME/.config/systemd/user/gemini-voice-flow.service"
systemctl --user daemon-reload
systemctl --user enable gemini-voice-flow.service || true

echo ""
echo "=============================================="
echo "   ✅ Installation Completed Successfully!    "
echo "=============================================="
echo ""
echo "1. Set your Gemini API key in:"
echo "   nano ~/.config/gemini-voice-flow/config.json"
echo ""
echo "2. Start the service with:"
echo "   gemini-flow start"
echo ""
echo "3. Usage:"
echo "   Click [CapsLock] -> Speak -> Click [CapsLock] again to paste!"
echo "=============================================="

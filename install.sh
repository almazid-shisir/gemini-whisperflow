#!/bin/bash
set -e

echo "=== Installing Gemini WhisperFlow for Linux ==="

# 1. System packages check
echo "Checking required system dependencies..."
MISSING=""
for cmd in arecord xdotool xclip notify-send python3 ffmpeg; do
  if ! command -v "$cmd" &>/dev/null; then
    MISSING="$MISSING $cmd"
  fi
done

if [ -n "$MISSING" ]; then
  echo "Missing packages:$MISSING"
  echo "Installing via apt..."
  sudo apt-get update && sudo apt-get install -y alsa-utils xdotool xclip libnotify-bin python3-venv ffmpeg
fi

# 2. Setup Python Virtual Environment
echo "Setting up Python virtual environment..."
INSTALL_DIR="$HOME/.local/share/gemini-voice-flow"
mkdir -p "$INSTALL_DIR"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r requirements.txt

# 3. Setup Configuration
echo "Initializing configuration..."
CONFIG_DIR="$HOME/.config/gemini-voice-flow"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
  cp config.example.json "$CONFIG_DIR/config.json"
  echo "Created default configuration at: $CONFIG_DIR/config.json"
  echo "Please set your 'gemini_api_key' in $CONFIG_DIR/config.json."
fi

# 4. Install CLI command and systemd user service
echo "Setting up CLI command and systemd service..."
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"
cp gemini-flow "$HOME/.local/bin/gemini-flow"
chmod +x "$HOME/.local/bin/gemini-flow"

sed "s|%h|$HOME|g" gemini-whisperflow.service > "$HOME/.config/systemd/user/gemini-voice-flow.service"
systemctl --user daemon-reload
systemctl --user enable gemini-voice-flow.service || true

echo ""
echo "Installation complete."
echo "1. Configure your API key:"
echo "   nano ~/.config/gemini-voice-flow/config.json"
echo ""
echo "2. Start the daemon:"
echo "   gemini-flow start"
echo ""
echo "3. Usage:"
echo "   Press [CapsLock] to begin speaking, and press [CapsLock] again to paste."

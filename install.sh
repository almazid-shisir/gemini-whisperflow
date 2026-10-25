#!/bin/bash
set -e

echo "========================================================"
echo "🚀 Installing Gemini WhisperFlow (Ultra-Fast Edition)"
echo "========================================================"

# Determine if running with sudo / root
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo &>/dev/null; then
    SUDO="sudo"
  fi
fi

# 1. System packages installation
echo "[1/5] Detecting package manager and installing dependencies..."
if command -v apt-get &>/dev/null; then
  echo "Detected Debian/Ubuntu system."
  $SUDO apt-get update -qq || true
  $SUDO apt-get install -y --no-install-recommends \
    alsa-utils \
    xdotool \
    xclip \
    libnotify-bin \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    curl \
    tar \
    wl-clipboard || true
elif command -v dnf &>/dev/null; then
  echo "Detected Fedora/RHEL system."
  $SUDO dnf install -y alsa-utils xdotool xclip libnotify python3 python3-pip ffmpeg curl tar wl-clipboard || true
elif command -v pacman &>/dev/null; then
  echo "Detected Arch Linux system."
  $SUDO pacman -Sy --noconfirm alsa-utils xdotool xclip libnotify python ffmpeg curl tar wl-clipboard || true
elif command -v zypper &>/dev/null; then
  echo "Detected openSUSE system."
  $SUDO zypper install -y alsa-utils xdotool xclip libnotify-tools python3 python3-pip ffmpeg curl tar wl-clipboard || true
else
  echo "Notice: Non-standard package manager. Please ensure alsa-utils, xdotool, xclip, ffmpeg and python3 are installed."
fi

# 2. Check and Install Official Google Gemini API CLI
echo "[2/5] Checking Google Gemini API CLI (gemini-api)..."
if ! command -v gemini-api &>/dev/null && [ ! -f "/usr/local/bin/gemini-api" ]; then
  echo "Installing official gemini-api CLI via install script..."
  curl -fsSL https://raw.githubusercontent.com/google-gemini/gemini-api-cli/main/scripts/install.sh | bash || true
fi

if command -v gemini-api &>/dev/null || [ -f "/usr/local/bin/gemini-api" ]; then
  echo "✅ Gemini API CLI is ready."
else
  echo "⚠️ Note: gemini-api CLI install script skipped or failed; fallback direct API engine will be active."
fi

# 3. Setup Python Virtual Environment
echo "[3/5] Setting up isolated Python virtual environment..."
INSTALL_DIR="$HOME/.local/share/gemini-voice-flow"
mkdir -p "$INSTALL_DIR"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/venv/bin/pip" install -r requirements.txt --quiet

# 4. Setup Configuration
echo "[4/5] Initializing user configuration..."
CONFIG_DIR="$HOME/.config/gemini-voice-flow"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
  cp config.example.json "$CONFIG_DIR/config.json"
  echo "Created default configuration at: $CONFIG_DIR/config.json"
fi

# 5. Install CLI command & Systemd Service
echo "[5/5] Registering gemini-flow CLI command and desktop autostart..."
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user" "$HOME/.config/autostart" "$HOME/.local/share/applications"

# Copy CLI binary
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/gemini-flow" "$HOME/.local/bin/gemini-flow"
chmod +x "$HOME/.local/bin/gemini-flow"

# Write optimized systemd user service with exact path
cat << EOF_SERVICE > "$HOME/.config/systemd/user/gemini-voice-flow.service"
[Unit]
Description=Gemini WhisperFlow Daemon (Instant Linux Speech-to-Text)
After=graphical-session.target

[Service]
Type=simple
Environment="DISPLAY=:0"
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"
ExecStart=$INSTALL_DIR/venv/bin/python $SCRIPT_DIR/gemini_flow.py
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
EOF_SERVICE

# Enable systemd user service if systemctl is available
if command -v systemctl &>/dev/null && [ -d /run/user/"$(id -u)" ]; then
  systemctl --user daemon-reload || true
  systemctl --user enable gemini-voice-flow.service || true
fi

# Desktop autostart entry
cat << 'EOF_DESKTOP' > "$HOME/.config/autostart/gemini-whisperflow.desktop"
[Desktop Entry]
Type=Application
Name=Gemini WhisperFlow
Comment=Voice dictation daemon for Linux
Exec=bash -c "gemini-flow start"
Terminal=false
Categories=Utility;Accessibility;
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF_DESKTOP

# Application launcher entry
cat << 'EOF_APP' > "$HOME/.local/share/applications/gemini-whisperflow.desktop"
[Desktop Entry]
Type=Application
Name=Gemini WhisperFlow
Comment=Voice dictation daemon for Linux
Exec=bash -c "gemini-flow restart && notify-send 'WhisperFlow' 'Daemon started and running in background'"
Icon=audio-input-microphone
Terminal=false
Categories=Utility;Accessibility;
StartupNotify=false
EOF_APP

echo ""
echo "========================================================"
echo "🎉 Installation completed successfully!"
echo "========================================================"
echo "Next Steps:"
echo "1. Set your Gemini API key:"
echo "   nano ~/.config/gemini-voice-flow/config.json"
echo "   (or export GEMINI_API_KEY=\"your_key_here\")"
echo ""
echo "2. Start the daemon:"
echo "   gemini-flow start"
echo ""
echo "3. Dictate anywhere:"
echo "   Press [CapsLock] to talk, press [CapsLock] again to paste!"
echo "========================================================"

#!/bin/bash
# ==============================================================================
# Gemini WhisperFlow Linux Installer
# Single-Pass Ultra-Fast Voice Dictation Engine
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/gemini-voice-flow"
CONFIG_DIR="$HOME/.config/gemini-voice-flow"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
USER_UID="$(id -u)"

echo ""
echo "======================================================================"
echo "🚀 Installing Gemini WhisperFlow (Single-Pass Ultra-Fast Voice Engine)"
echo "======================================================================"
echo ""

# 1. Detect sudo / root
SUDO=""
if [ "$USER_UID" -ne 0 ]; then
  if command -v sudo &>/dev/null; then
    SUDO="sudo"
  fi
fi

# 2. System Packages Installation
echo "[1/4] Installing Linux system dependencies..."
if command -v apt-get &>/dev/null; then
  echo "Detected Debian/Ubuntu/Mint/Pop!_OS system."
  $SUDO apt-get update -qq || true
  $SUDO apt-get install -y --no-install-recommends \
    alsa-utils \
    pipewire \
    pipewire-audio \
    pipewire-pulse \
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
elif command -v pacman &>/dev/null; then
  echo "Detected Arch Linux / Manjaro system."
  $SUDO pacman -Sy --noconfirm alsa-utils pipewire pipewire-pulse xdotool xclip libnotify python ffmpeg curl tar wl-clipboard || true
elif command -v dnf &>/dev/null; then
  echo "Detected Fedora / RHEL system."
  $SUDO dnf install -y alsa-utils pipewire xdotool xclip libnotify python3 python3-pip ffmpeg curl tar wl-clipboard || true
elif command -v zypper &>/dev/null; then
  echo "Detected openSUSE system."
  $SUDO zypper install -y alsa-utils pipewire xdotool xclip libnotify-tools python3 python3-pip ffmpeg curl tar wl-clipboard || true
else
  echo "Notice: Non-standard package manager. Please ensure alsa-utils, pipewire, xdotool, xclip, ffmpeg and python3 are installed."
fi

# 3. Setup Python Virtual Environment
echo ""
echo "[2/4] Setting up isolated Python virtual environment..."
mkdir -p "$INSTALL_DIR"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "✅ Python environment ready."

# 4. Install Application Files, CLI Binary & Service definitions
echo ""
echo "[3/4] Installing gemini-flow CLI and systemd background service..."
mkdir -p "$BIN_DIR" "$CONFIG_DIR" "$HOME/.config/systemd/user" "$HOME/.config/autostart" "$HOME/.local/share/applications"

# Copy application script to permanent installation directory
cp -f "$SCRIPT_DIR/gemini_flow.py" "$INSTALL_DIR/gemini_flow.py"
cp -f "$SCRIPT_DIR/config.example.json" "$INSTALL_DIR/config.example.json"

# Copy CLI binary
cp -f "$SCRIPT_DIR/gemini-flow" "$BIN_DIR/gemini-flow"
chmod +x "$BIN_DIR/gemini-flow"

# Ensure ~/.local/bin is in PATH for future shells
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  if [ -f "$HOME/.bashrc" ] && ! grep -q "$BIN_DIR" "$HOME/.bashrc"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
  fi
  if [ -f "$HOME/.zshrc" ] && ! grep -q "$BIN_DIR" "$HOME/.zshrc"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
  fi
  if [ -f "$HOME/.zshenv" ] && ! grep -q "$BIN_DIR" "$HOME/.zshenv"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshenv"
  fi
fi

# Write systemd user service with concrete user runtime paths
cat << EOF_SERVICE > "$HOME/.config/systemd/user/gemini-voice-flow.service"
[Unit]
Description=Gemini WhisperFlow Daemon (Instant Linux Speech-to-Text)
After=graphical-session.target

[Service]
Type=simple
Environment="DISPLAY=:0"
Environment="PYTHONUNBUFFERED=1"
Environment="XDG_RUNTIME_DIR=/run/user/$USER_UID"
Environment="PATH=$BIN_DIR:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/gemini_flow.py
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
EOF_SERVICE

# Register desktop autostart entry
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

# Desktop application launcher icon
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

# 5. Interactive Configuration Wizard
echo ""
echo "[4/4] Configuring Gemini API Key and Trigger Key..."
# Run interactive setup wizard using installed python runtime
"$VENV_DIR/bin/python" "$INSTALL_DIR/gemini_flow.py" --setup

# 6. Start service
if command -v systemctl &>/dev/null && [ -d "/run/user/$USER_UID" ]; then
  systemctl --user daemon-reload || true
  systemctl --user enable gemini-voice-flow.service || true
  systemctl --user restart gemini-voice-flow.service || true
fi

echo ""
echo "======================================================================"
echo "🎉 Gemini WhisperFlow is fully installed and running in the background!"
echo "======================================================================"
echo ""
echo "Quick Management Commands:"
echo "  gemini-flow status    Check running status"
echo "  gemini-flow logs      Follow live logs"
echo "  gemini-flow test      Run audio & API self-test"
echo "  gemini-flow setup     Reconfigure API key or trigger"
echo "  gemini-flow restart   Restart daemon"
echo ""
echo "Note: If 'gemini-flow' command is not recognized in current terminal, run:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "======================================================================"
echo ""

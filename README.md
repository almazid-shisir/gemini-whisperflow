# Gemini WhisperFlow for Linux (Ultra-Fast Edition)

Native Linux voice dictation daemon that transcribes spoken audio using the official **Google Gemini API CLI** and pastes clean text directly into your active cursor position.

Designed as an ultra-fast, zero-bloat alternative to tools like Wispr Flow or Superwhisper on Linux desktop environments (**X11 & Wayland**).

## 🚀 Key Improvements & Features

- **Push-to-Talk (Hold Right Shift to Speak, Release to Paste)**:
  - Hold `Right Shift` (`shift_r`) while speaking.
  - Release `Right Shift` to immediately stop, transcribe, and paste.
  - Accidental quick taps (< 0.35s) are ignored, so standard typing is never interrupted.
- **Powered by Official Gemini API CLI (`gemini-api`)**:
  - Leverages Google's compiled Go binary for minimal latency, zero Base64 conversion overhead, and HTTP/2 streaming.
  - Automatic fallback to direct HTTPS API engine if the CLI binary is absent.
- **Ultra-Fast & Cleaned Transcripts**:
  - Automatically eliminates stutters, false starts, and filler words (*e.g.*, `um`, `uh`, `মানে`, `আসলে`, `ওই আর কি`).
  - Standardizes tech acronyms and units (e.g. `HD`, `Full HD`, `1080p`, `4K`, `MB`, `GB`, `fps`, `Python`).
  - Corrects mid-sentence self-corrections into clean, grammatically punctuated text.
- **Instant Pasting**:
  - Auto-detects Wayland (`wl-copy` / `wtype` / `ydotool`) and X11 (`xclip` / `xdotool`).
- **All-in-One Linux Auto-Installer**:
  - One-command setup with automatic package manager detection (`apt`, `dnf`, `pacman`, `zypper`).
  - Automatically fetches and sets up `gemini-api`, audio utilities, clipboard tools, and virtual environment.

## 📦 One-Command Installation

Run the installer:

```bash
git clone https://github.com/almazid-shisir/gemini-whisperflow.git
cd gemini-whisperflow
chmod +x install.sh
./install.sh
```

## ⚙️ Configuration

Edit `~/.config/gemini-voice-flow/config.json`:

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
  "model": "gemini-3.5-flash-lite",
  "trigger_key": "shift_r",
  "clean_transcript": true,
  "sound_feedback": false,
  "notify": true,
  "min_hold_seconds": 0.35
}
```

> **Tip:** You can also simply set `export GEMINI_API_KEY="your-api-key"` in your `~/.bashrc` or `~/.zshrc`.

### Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `gemini_api_key` | string | `""` | Gemini API key from Google AI Studio. |
| `model` | string | `"gemini-3.5-flash-lite"` | Recommended ultra-fast model for instant voice typing. |
| `trigger_key` | string | `"shift_r"` | Trigger key. Default is Right Shift (`shift_r`). |
| `min_hold_seconds` | float | `0.35` | Minimum hold time to trigger speech. Discards quick accidental taps. |
| `clean_transcript` | boolean | `true` | When true, cleans stutters, fillers, and punctuates. |
| `sound_feedback` | boolean | `false` | Play audio cues on record and completion. |
| `notify` | boolean | `true` | Display desktop notifications via `notify-send`. |

## 🎮 How to Use

Control the background daemon using `gemini-flow`:

```bash
gemini-flow start      # Start background service
gemini-flow stop       # Stop service
gemini-flow restart    # Restart service
gemini-flow status     # Check process status
gemini-flow logs       # Follow live logs
gemini-flow run        # Run directly in foreground
```

### Workflow:
1. Place your cursor in any application (VS Code, Browser, Telegram, Terminal).
2. **Press and hold Right Shift (`shift_r`)** and speak naturally.
3. **Release Right Shift** when you are done. The cleaned text will instantly paste at your cursor!

## 📄 License

MIT License.

# 🎙️ Gemini WhisperFlow for Linux

> **Ultra-fast, native Linux voice dictation daemon powered by Google Gemini Speech & Audio AI.**
> A lightweight, open-source alternative to Wispr Flow and Superwhisper. Works system-wide across all applications with a simple single-click toggle shortcut.

---

## ✨ Features

- ⚡ **Ultra-Fast Transcription:** Powered by Google's `gemini-3.5-flash-lite` model with ~1.5s average response time.
- 🎯 **Click-to-Start / Click-to-Stop:** Just click `CapsLock` once to start speaking, and click `CapsLock` again to finish and paste! (No need to hold keys down).
- ✍️ **Direct Cursor Typing:** Automatically injects and pastes transcribed text directly into wherever your active cursor is (Browser, VS Code, Slack, Terminal, etc.).
- 🌐 **Multilingual & Mixed Speech:** Flawlessly transcribes **Bengali**, **English**, and mixed **Banglish** verbatim with high accuracy.
- 🔇 **100% Silent Mode:** No distracting beeps or bells. Clean desktop notifications inform you when recording starts and when transcription is complete.
- 🛡️ **No Stuck CapsLock:** Automatically ensures the CapsLock uppercase toggle state stays off so your normal typing is never affected.
- 🐧 **Linux Native & Lightweight:** Pure Python daemon using standard Linux utilities (`arecord`, `xdotool`, `xclip`) with minimal RAM usage (<30MB).

---

## 📋 System Requirements

- **OS:** Linux (X11 environment: Ubuntu, Debian, Mint, Arch, Fedora, etc.)
- **Dependencies:**
  - `python3` & `python3-venv`
  - `alsa-utils` (`arecord` for microphone capture)
  - `xdotool` & `xclip` (for automated clipboard pasting)
  - `libnotify-bin` (`notify-send` for desktop notifications)

---

## 🚀 Quick Installation (1-Click)

Clone this repository and run the installer:

```bash
git clone https://github.com/almazid-shisir/gemini-whisperflow.git
cd gemini-whisperflow
chmod +x install.sh
./install.sh
```

---

## ⚙️ Configuration

Open your configuration file:

```bash
nano ~/.config/gemini-voice-flow/config.json
```

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
  "model": "gemini-3.5-flash-lite",
  "trigger_key": "caps_lock",
  "sound_feedback": false,
  "notify": true
}
```

### Options:
- **`gemini_api_key`**: Your Google Gemini API key from [Google AI Studio](https://aistudio.google.com/).
- **`model`**: 
  - `gemini-3.5-flash-lite` *(Default & Recommended for fastest speed ~1.5s)*
  - `gemini-3.5-transcribe` *(Google's specialized STT model)*
- **`trigger_key`**: 
  - `caps_lock` *(Default)*
  - `f8`, `f9`, `pause`, `scroll_lock`
- **`sound_feedback`**: `false` *(Silent, default)* or `true` *(Plays soft sounds on start/stop)*.
- **`notify`**: `true` *(Shows native desktop notifications)*.

---

## 🎮 How to Use

1. Focus on any text box or application where you want to write (Google Chrome, Telegram, VS Code, Terminal, etc.).
2. **Click `CapsLock` once** 🎙️
   - A subtle notification will appear: `🎙️ রেকর্ড হচ্ছে...`
   - Speak naturally in Bengali or English.
3. **Click `CapsLock` again** ⏹️
   - The daemon stops recording and sends the audio to Gemini.
   - Within 1–2 seconds, the text is automatically typed into your cursor position!

---

## 🛠️ CLI Management Commands

Manage the background service anytime using the `gemini-flow` command:

```bash
# Check service status:
gemini-flow status

# Start the daemon:
gemini-flow start

# Stop the daemon:
gemini-flow stop

# Restart after editing config:
gemini-flow restart

# Run in foreground (for live terminal debugging & logs):
gemini-flow run

# View live service logs:
gemini-flow logs
```

---

## 🔍 Architecture & How It Works

```
[ User clicks CapsLock ]
        │
        ▼
[ pynput GlobalHotKey Hook ]
        │
        ├──► Starts `arecord` (16kHz 16-bit WAV PCM)
        │
[ User speaks & clicks CapsLock again ]
        │
        ▼
[ Stops `arecord` & encodes audio to Base64 ]
        │
        ▼
[ Google Gemini Audio API (gemini-3.5-flash-lite) ]
        │
        ▼
[ Receives Verbatim Bengali/English Transcript ]
        │
        ▼
[ Injects text via `xclip` & `xdotool ctrl+v` into active window ]
```

---

## 🤝 Contributing

Contributions, feature suggestions, and bug reports are welcome! Feel free to open an issue or submit a pull request.

## 📄 License

MIT License. Free to use, modify, and distribute.

# 🎙️ Gemini WhisperFlow for Linux

> **Ultra-fast, native Linux voice dictation daemon powered by Google Gemini Speech & Audio AI.**
> A lightweight, open-source alternative to Wispr Flow and Superwhisper. Works system-wide across all applications with a simple single-click toggle shortcut and intelligent transcript cleanup engine.

---

## ✨ Features

- ⚡ **Ultra-Fast Transcription:** Powered by Google's `gemini-3.5-flash-lite` model with ~1.2s - 1.8s response time.
- 🧹 **Intelligent WisprFlow Cleanup:**
  - **Filler Word Removal:** Automatically strips fillers in English (`um`, `uh`, `like`, `you know`) and Bengali (`মানে`, `আসলে`, `ওই আর কি`, `এই ধরেন`).
  - **Self-Corrections:** Intelligently corrects on the fly (*e.g.* `"কালকে না... পরশু যাবো"` $\rightarrow$ `"পরশু যাবো"` / `"Thursday wait no Friday"` $\rightarrow$ `"Friday"`).
  - **Spoken Punctuation:** Converts spoken punctuation commands (`"comma"`, `"period"`, `"দাঁড়ি"`, `"কমা"`, `"নতুন লাইন"`) into actual symbols (`.`, `,`, `।`, `?`, line breaks).
  - **Dictation Protection:** Questions and commands spoken are strictly transcribed as document text, never answered or executed by AI.
- 🎯 **Click-to-Start / Click-to-Stop:** Just click `CapsLock` once to start speaking, and click `CapsLock` again to finish and paste! (No need to hold keys down).
- ✍️ **Direct Cursor Typing:** Automatically injects and pastes transcribed text directly into wherever your active cursor is (Browser, VS Code, Slack, Terminal, etc.).
- 🌐 **Multilingual & Mixed Speech:** Flawlessly transcribes **Bengali**, **English**, and mixed **Banglish** with high contextual accuracy.
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
  "clean_transcript": true,
  "sound_feedback": false,
  "notify": true
}
```

### Options:
| Key | Default | Description |
|---|---|---|
| `gemini_api_key` | Required | Your Google Gemini API Key from Google AI Studio. |
| `model` | `gemini-3.5-flash-lite` | Model to use. `gemini-3.5-flash-lite` is recommended for sub-2s latency. |
| `trigger_key` | `caps_lock` | Toggle key (`caps_lock`, `f8`, `pause`, `scroll_lock`, etc.). |
| `clean_transcript` | `true` | `true` for WisprFlow-style intelligent cleanup; `false` for raw verbatim output. |
| `sound_feedback` | `false` | Set `true` to play audio chimes on start and complete. |
| `notify` | `true` | Show native desktop notification alerts. |

### Custom Prompt Rules (Optional)
If you want to add your own custom dictation rules, vocabulary, or formatting instructions, simply create:
```bash
nano ~/.config/gemini-voice-flow/prompt.txt
```
Any text placed in this file will automatically override the default system prompt.

---

## 🎮 CLI Management

Use the `gemini-flow` CLI to control the daemon:

```bash
gemini-flow status     # Check if the service is running and view recent logs
gemini-flow restart    # Restart service after changing config
gemini-flow stop       # Temporarily stop the service
gemini-flow start      # Start the background daemon
gemini-flow logs       # View real-time live logs
```

---

## 🛠️ How It Works (Single-Pass Multimodal vs. WisprFlow)

Traditional dictation tools (like WisprFlow or Superwhisper) rely on a **two-step pipeline**:
1. Speech $\rightarrow$ Whisper API (Produces raw text full of fillers)
2. Raw text $\rightarrow$ LLM pass (Cleans the text)

This two-step process takes **3.0 to 5.0+ seconds**.

**Gemini WhisperFlow** uses Gemini's **Single-Pass Multimodal Audio architecture**:
Raw 16kHz audio and the system prompt are fed directly to Gemini simultaneously. Gemini listens directly to the audio, understands inflection and self-corrections, and outputs the cleaned transcript in **under 1.8 seconds**.

---

## 📄 License
MIT License. Open source and free for personal and commercial use.

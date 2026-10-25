# 🎙️ Gemini WhisperFlow for Linux

**Single-Pass Ultra-Fast Linux Voice Dictation & Code-Switching Engine**

Gemini WhisperFlow is a privacy-first, zero-bloat voice dictation daemon for Linux (**X11 & Wayland**). It acts as an open-source, ultra-accurate alternative to tools like Wispr Flow and Superwhisper.

Powered by a **Single-Pass Ultra-Fast Architecture**:
* **Sub-1.5s End-to-End Latency:** Single high-precision multimodal request to `gemini-3.5-flash-lite` with in-memory audio processing.
* **Zero Generative Hallucination:** Strict verbatim prompt retains natural colloquial phrasing (Bengali/English code-switching) without unauthorized summarizing, rewriting, or conversational drift.
* **Deterministic Tech Normalization:** Client-side regex engine instantly standardizes tech terms (`Vercel`, `GitHub`, `CEO`, `Python`, `Linux`).

---

## ✨ Features & Highlights

- **⚡ Blazing Fast Single-Pass Execution (<1.5s total):**
  - Eliminates the slow double-hop API bottleneck. Audio is processed directly in RAM and transcribed in a single hop.
  - In-memory pipe encoding eliminates local disk I/O latency.

- **🎯 Exact Verbatim Speech Fidelity (Zero Hallucination):**
  - What you speak is exactly what is transcribed. No rewriting, no invented connecting thoughts, no awkward formal tone shifts.
  - Automatically punctuates (।, ?, ,) and capitalizes English terms properly.

- **🕹️ Smart Multi-Trigger (Right Alt / Right Shift / Right Ctrl):**
  - **Hold-to-Talk (Push-to-Talk):** Hold `Right Alt` (AltGr) or `Right Shift`, speak, and release to paste immediately.
  - **Hands-Free Toggle:** Tap `Right Alt` once (<0.35s) to lock mic ON. Speak freely with relaxed hands for 5, 10, or 20+ minutes. Tap again (or press `Esc`) to finish and paste!
  - **Instant Visual Notification:** Prominent desktop popup appears the instant you trigger recording.

- **🛡️ 5ms In-Memory Silence Gate:**
  - Instant waveform peak detector (`silence_threshold_db: -45.0 dB`).
  - Discards room silence or background noise locally without hitting cloud quota.

- **📋 Safe Native Clipboard Paste:**
  - Automatically detects Wayland (`wl-copy` / `wtype` / `ydotool`) and X11 (`xclip` / `xdotool`).

- **🔍 Rich Terminal Logging & Diagnostics:**
  - Real-time colored terminal logs with precise millisecond latency breakdowns (`ASR`, `NLP`, `Comp`).
  - Detailed diagnostic error messages for network drops, invalid API keys, or quiet audio.

---

## 📦 Quick 1-Command Installation

Run the automated installer on any Linux distribution (Ubuntu, Debian, Mint, Pop!_OS, Arch, Manjaro, Fedora, openSUSE):

```bash
git clone https://github.com/almazid-shisir/gemini-whisperflow.git
cd gemini-whisperflow
chmod +x install.sh
./install.sh
```

### What the installer does:
1. Detects your package manager and installs all dependencies (`pipewire`, `alsa-utils`, `xclip`, `xdotool`, `ffmpeg`, `libnotify-bin`, `wl-clipboard`).
2. Creates an isolated Python virtual environment at `~/.local/share/gemini-voice-flow/venv`.
3. Launches the **Interactive Setup Wizard**:
   - Prompts for your Google Gemini API Key.
   - Instantly tests and validates the key against Google API servers.
   - Lets you choose your preferred trigger key (`ctrl_r` recommended).
4. Registers and starts the systemd background user service (`gemini-voice-flow.service`).
5. Adds the `gemini-flow` CLI command to your system path.

---

## 🔑 Obtaining a Gemini API Key

You need a Google Gemini API Key (generous free tier available):
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **Create API Key**.
3. Paste it when prompted during `./install.sh` or run `gemini-flow setup`.

> **Note:** Your API key is stored securely in `~/.config/gemini-voice-flow/config.json` with strict user permissions. No keys are ever stored or tracked in the Git repository.

---

## 🎮 How to Use

Place your text cursor in **any application** (VS Code, Chrome, Telegram, Terminal, Obsidian, Discord):

### Option 1: Push-to-Talk (Quick Thoughts)
1. **Hold down `Right Control` (`ctrl_r`)**.
2. Speak your thought.
3. **Release `Right Control`**.
4. The transcribed and polished text is instantly pasted at your cursor!

### Option 2: Hands-Free Dictation (Long Form / Paragraphs)
1. **Tap `Right Control` once quickly (<0.35s)**.
2. A desktop notification and terminal log will confirm: `🎙️ Hands-Free Mode Active`.
3. Speak as long as you want (5, 10, 15+ minutes) without holding any key down.
4. When finished, **tap `Right Control` once again** (or press `Esc`).
5. Your entire speech will be structured and pasted into your active window!

---

## 🛠️ CLI Management Commands

Manage the daemon easily using `gemini-flow`:

```bash
gemini-flow setup       # Launch interactive API key & trigger key wizard
gemini-flow test        # Run end-to-end microphone & API self-test diagnostics
gemini-flow status      # Check service health and running status
gemini-flow logs        # Stream live systemd logs in real time
gemini-flow start       # Start background daemon
gemini-flow stop        # Stop background daemon
gemini-flow restart     # Restart background daemon
gemini-flow run         # Run directly in foreground terminal
gemini-flow run --debug # Run in foreground with verbose debug logs
gemini-flow config      # Edit configuration file in terminal
```

---

## ⚙️ Configuration File

Configuration is stored at `~/.config/gemini-voice-flow/config.json`:

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "transcribe_model": "gemini-3.5-transcribe",
  "cleanup_model": "gemini-3.5-flash-lite",
  "trigger_key": "ctrl_r",
  "clean_transcript": true,
  "sound_feedback": false,
  "notify": true,
  "min_hold_seconds": 0.35,
  "silence_threshold_db": -38.0
}
```

### Configuration Options:

| Setting | Type | Default | Description |
|---|---|---|---|
| `gemini_api_key` | string | `""` | Google Gemini API key from AI Studio. |
| `transcribe_model` | string | `"gemini-3.5-transcribe"` | Stage 1 dedicated ASR transcription model. |
| `cleanup_model` | string | `"gemini-3.5-flash-lite"` | Stage 2 text clarifier and fluff removal model. |
| `trigger_key` | string | `"ctrl_r"` | Dictation trigger key (`ctrl_r`, `shift_r`, `alt_r`, `f9`, etc.). |
| `clean_transcript` | boolean | `true` | When `true`, removes filler words (*"মানে"*, *"আসলে"*) and punctuates. Set `false` for raw verbatim mode. |
| `min_hold_seconds` | float | `0.35` | Taps shorter than this toggle hands-free mode; holds longer than this behave as push-to-talk. |
| `silence_threshold_db` | float | `-38.0` | Peak volume dB gate. Audio below this volume is rejected locally as background noise. |
| `sound_feedback` | boolean | `false` | Play audio cues on record start and completion. |
| `notify` | boolean | `true` | Display desktop notifications via `notify-send`. |

---

## 🧠 Customizing the NLP Editor Prompt

You can customize the Stage 2 text clarifier instructions to match your personal writing style!
Create or edit `~/.config/gemini-voice-flow/prompt.txt`:

```bash
nano ~/.config/gemini-voice-flow/prompt.txt
```

If this file exists, Gemini WhisperFlow will use your custom prompt to format and polish your spoken text.

---

## 🔍 Troubleshooting & Diagnostic Logs

If you encounter any issues:

1. **Run Self-Test Diagnostics:**
   ```bash
   gemini-flow test
   ```
   This will test your microphone recording, verify API key authentication against both models, and verify audio compression.

2. **Run in Foreground with Debug Logs:**
   ```bash
   gemini-flow stop
   gemini-flow run --debug
   ```
   This displays every step in detail (exact peak dB volume, HTTP status codes, API latency, and paste actions).

3. **Check Live Background Service Logs:**
   ```bash
   gemini-flow logs
   ```

---

## 🇧🇩 বাংলা নির্দেশিকা (Quick Bengali Guide)

* **ইনস্টলেশন:** টার্মিনালে `./install.sh` রান করুন। ইনস্টলার স্বয়ংক্রিয়ভাবে সব ডিপেন্ডেন্সি সেটআপ করবে এবং আপনার কাছে Gemini API কি চাইবে।
* **API Key:** ইনপুট দেওয়ার সাথে সাথে সিস্টেম স্বয়ংক্রিয়ভাবে গুগল সার্ভারে কি ভেরিফাই করবে এবং `gemini-3.5-transcribe` ও `gemini-3.5-flash-lite` কনফিগার করে নিবে।
* **ব্যবহার:**
  * **Hold-to-Talk:** কিবোর্ডের `Right Control` (`ctrl_r`) চেপে ধরে কথা বলুন, ছেড়ে দিলে স্বয়ংক্রিয়ভাবে টেক্সট পেস্ট হয়ে যাবে।
  * **Hands-Free Mode:** `Right Control` একবার হালকা ট্যাপ করুন। মাইক চালু থাকবে, হাত ছেড়ে দিয়ে রিল্যাক্স হয়ে যতখুশি কথা বলুন। কথা শেষ হলে আবার `Right Control` (বা `Esc`) চাপলেই সম্পূর্ণ লেখা এডিট হয়ে পেস্ট হয়ে যাবে।

---

## 📄 License

MIT License. Open source and free for personal and commercial use.

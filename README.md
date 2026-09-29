# Gemini WhisperFlow for Linux

Native Linux voice dictation daemon that transcribes spoken audio and types the resulting text directly into the active cursor position.

Designed as a lightweight, low-latency alternative to tools like Wispr Flow or Superwhisper on Linux desktop environments (X11).

## Features

- **Low-latency transcription**: Streams compressed audio to Google Gemini API with typical response times of 1.2s - 2.5s even on long dictations.
- **Transcript cleanup**: Filters spoken filler words (`um`, `uh`, `মানে`, `আসলে`), handles verbal self-corrections (*e.g.*, "Thursday, wait no, Friday" -> "Friday"), and converts spoken punctuation commands (*e.g.*, "comma", "period", "দাঁড়ি", "new line") to proper typographical symbols.
- **Dictation isolation**: Spoken questions, prompts, or commands are transcribed verbatim into your document or editor rather than being executed by the model.
- **Push-to-toggle trigger**: A single tap on `CapsLock` (or a configured hotkey) starts recording, and a second tap stops and pastes the output. No need to hold keys down.
- **Automatic paste**: Inserts text directly at the active cursor position using `xclip` and `xdotool`.
- **Multilingual support**: Transcribes Bengali, English, and mixed Banglish without requiring manual language switching.
- **Caps Lock safety**: Automatically restores Caps Lock state so normal typing remains unaffected.
- **Resource efficient**: Written in Python with standard Linux system utilities (`arecord`, `ffmpeg`, `xdotool`, `xclip`), consuming under 35 MB resident memory.

## Prerequisites

- **OS**: Linux with X11 display server (Ubuntu, Debian, Fedora, Arch, Mint, etc.)
- **System packages**:
  - `python3` (with `python3-venv`)
  - `alsa-utils` (`arecord` for microphone capture)
  - `ffmpeg` (for fast audio compression)
  - `xdotool` and `xclip` (for clipboard interaction and keystroke simulation)
  - `libnotify-bin` (`notify-send` for desktop status hints)

## Installation

Clone the repository and run the setup script:

```bash
git clone https://github.com/almazid-shisir/gemini-whisperflow.git
cd gemini-whisperflow
chmod +x install.sh
./install.sh
```

Ensure `~/.local/bin` is in your `$PATH`.

## Configuration

Edit `~/.config/gemini-voice-flow/config.json`:

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
  "model": "gemini-flash-lite-latest",
  "trigger_key": "caps_lock",
  "clean_transcript": true,
  "sound_feedback": false,
  "notify": true
}
```

### Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `gemini_api_key` | string | `""` | Gemini API key from Google AI Studio. |
| `model` | string | `"gemini-flash-lite-latest"` | Target Gemini model. `gemini-flash-lite-latest` provides optimal latency. |
| `trigger_key` | string | `"caps_lock"` | Hotkey trigger. Options include `caps_lock`, `f8`, `scroll_lock`, `pause`. |
| `clean_transcript` | boolean | `true` | When true, applies transcript cleanup and punctuation conversion. Set to false for verbatim output. |
| `sound_feedback` | boolean | `false` | Play audio cues on recording start and completion. |
| `notify` | boolean | `true` | Display desktop notifications via `notify-send`. |

### Custom Prompt Rules

To define custom vocabulary, formatting preferences, or project-specific jargon, create a text file at:

```bash
~/.config/gemini-voice-flow/prompt.txt
```

If this file exists, its contents will be used as the system instruction for the dictation engine.

## Usage

Control the background daemon using `gemini-flow`:

```bash
gemini-flow start      # Start systemd user service
gemini-flow stop       # Stop the service
gemini-flow restart    # Restart after editing configuration
gemini-flow status     # Check process status and memory
gemini-flow logs       # Follow live daemon logs
gemini-flow run        # Run daemon in the foreground for debugging
```

### Basic Workflow

1. Place your text cursor in any application (editor, browser, terminal, Slack).
2. Tap `CapsLock` once to begin speaking.
3. Speak normally.
4. Tap `CapsLock` again when finished. The transcribed text will be pasted at your cursor.

## Architecture

Traditional voice dictation software typically uses a two-stage pipeline:
1. Speech-to-text model produces raw output containing fillers, repetitions, and spoken commands.
2. A separate LLM call cleans the output.

This two-stage approach introduces 3-5 seconds of latency.

Gemini WhisperFlow leverages Gemini's multimodal audio capabilities:
1. Raw audio is captured via `arecord` at 16kHz mono.
2. The audio is compressed to a 48kbps MP3 stream using `ffmpeg` (reducing payload size by ~85%).
3. The compressed audio and cleanup instructions are sent directly to the model in a single request.
4. The cleaned text is written to the X11 clipboard and pasted via simulated keystroke.

This single-pass design delivers clean text within 1.2s to 2.5s, even on 30-40 second recordings.

## License

MIT License.

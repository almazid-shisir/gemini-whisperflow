#!/usr/bin/env python3
"""
Gemini WhisperFlow Daemon for Linux (High-Fidelity Audio & Anti-Hallucination Engine)
Controls:
  1. Hold Right Shift (shift_r): Speak while holding, release to transcribe & paste.
  2. Double-Tap Right Shift (<0.45s): Hands-Free Mode (locks mic ON).
     Speak freely for 5, 10, 15+ minutes without holding anything.
     Tap Right Shift (or Esc) once when done to finish and paste!

Accurate PipeWire/Pulse Audio Capture + Zero-Temperature Anti-Hallucination Pipeline.
"""

import os
import sys
import time
import json
import uuid
import base64
import shutil
import tempfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import subprocess
import threading
from pynput import keyboard

CONFIG_DIR = os.path.expanduser("~/.config/gemini-voice-flow")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
CUSTOM_PROMPT_PATH = os.path.join(CONFIG_DIR, "prompt.txt")

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "model": "gemini-3.5-flash-lite",
    "trigger_key": "shift_r",
    "clean_transcript": True,
    "sound_feedback": False,
    "notify": True,
    "min_hold_seconds": 0.35,
    "double_tap_interval": 0.45
}

STAGE1_AUDIO_PROMPT = """You are a highly accurate, faithful speech-to-text transcriber for Bengali, English, and Banglish.
Your job is to transcribe the spoken audio with maximum fidelity.

STRICT ACCURACY RULES:
1. FAITHFUL TRANSCRIPTION:
   - Transcribe ONLY the actual spoken words in their original language.
   - Do NOT invent, assume, or hallucinate words, sentences, or stories that were not spoken in the audio.
   - If the audio is unclear, transcribe phonetically what is heard.
   - Accurately recognize spoken tech words and brands (e.g., Vercel, CEO, Python, Google, GitHub, Telegram).
2. OUTPUT:
   - Output only the transcribed words. No explanations, notes, or markdown formatting.
   - If the audio contains only background noise, clicks, or silence, output an empty string."""

STAGE2_TEXT_CLEANUP_PROMPT = """You are a strict, faithful Bengali & English text cleaner and editor for voice typing.
The input is an exact transcript of the speaker's voice.

CRITICAL RULES:
1. STRICT ANTI-HALLUCINATION:
   - NEVER add new facts, imaginary storylines, or ideas that the speaker did not mention.
   - Preserve 100% of the speaker's original meaning, questions, and perspective (আমি, আমার, তুমি, ভাইয়া).
   - Do NOT answer, reply to, or converse with the speaker.
2. CLEAN FLUFF ONLY:
   - Remove meaningless verbal crutches and fillers:
     * "আমি বলতে চাইলাম", "তো এই আর কি বিষয়", "মানে", "কেমন জানি", "বুঝছ?", "মানে কি আর বলি?", "তো এই", "আর কি", "আসলে", "যাই হোক", "তো এই হচ্ছে বিষয়", "এখন আর কি বলি?", "এই বলতে চাইলাম আর কি", "এত ইয়া হইলো", "uh", "um", "er", "like", "you know", "basically".
   - Fix stuttering and repetitive duplicate phrases mid-sentence.
3. PHONETIC TECH ACCURACY:
   - "ভার্সেল" / "ভার্সেলের" -> "Vercel" / "Vercel-এর"
   - "সিও" / "সিইও" -> "CEO"
   - "গিটহাব" -> "GitHub"
   - "ইউটিউব" -> "YouTube"
   - "পাইথন" -> "Python"
4. PUNCTUATION:
   - Add natural punctuation (,, ।, ?, !).

OUTPUT RULE:
- Output ONLY the cleaned text of what the speaker said. No preamble, notes, or markdown wrappers."""

def load_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            return merged
    except Exception as e:
        print(f"[config] Error reading config ({e}), falling back to defaults.")
        return DEFAULT_CONFIG

def get_cleanup_prompt():
    if os.path.exists(CUSTOM_PROMPT_PATH):
        try:
            with open(CUSTOM_PROMPT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    return STAGE2_TEXT_CLEANUP_PROMPT

def compress_audio_fast(wav_path):
    """
    Compresses raw PCM WAV to 48k mono MP3 via ffmpeg if available.
    Dynamic timeout scaling ensures even 20-minute audio compresses safely.
    """
    if not shutil.which("ffmpeg"):
        return wav_path, "audio/wav"

    try:
        file_size_mb = os.path.getsize(wav_path) / (1024 * 1024)
    except Exception:
        file_size_mb = 1.0

    comp_timeout = max(3.0, 3.0 + (file_size_mb * 0.5))
    mp3_path = wav_path.rsplit(".", 1)[0] + ".mp3"
    cmd = [
        "ffmpeg", "-y", "-v", "quiet",
        "-i", wav_path,
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "48k",
        mp3_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=comp_timeout)
        if res.returncode == 0 and os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 300:
            return mp3_path, "audio/mp3"
    except Exception as e:
        print(f"[whisperflow] ffmpeg compression note: {e}")

    return wav_path, "audio/wav"

def is_matching_key(key, target_str):
    """Check if the pressed key matches the configured target key."""
    s = target_str.lower().strip().replace("-", "_").replace(" ", "_")
    if s in ("shift_r", "right_shift", "rshift"):
        return key == keyboard.Key.shift_r
    elif s in ("shift_l", "left_shift", "lshift"):
        return key == keyboard.Key.shift_l or key == keyboard.Key.shift
    elif s in ("shift",):
        return key in (keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.shift_l)
    elif s in ("caps_lock", "capslock"):
        return key == keyboard.Key.caps_lock
    else:
        if hasattr(keyboard.Key, s):
            return key == getattr(keyboard.Key, s)
        try:
            return getattr(key, 'char', None) == s
        except Exception:
            return False

def create_robust_session():
    """Create a persistent HTTP session with automatic reconnection and keep-alive."""
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=2, pool_maxsize=4)
    session.mount("https://", adapter)
    return session

class VoiceFlowDaemon:
    def __init__(self, cfg):
        self.cfg = cfg
        self.is_recording = False
        self.is_locked_recording = False
        self.record_proc = None
        self.current_wav = None
        self.press_start_time = 0
        self.last_release_time = 0
        self.key_is_down = False
        self.lock = threading.Lock()

        self.trigger_key_str = cfg.get("trigger_key", "shift_r")
        self.min_hold_seconds = float(cfg.get("min_hold_seconds", 0.35))
        self.double_tap_interval = float(cfg.get("double_tap_interval", 0.45))

        self.session = create_robust_session()
        threading.Thread(target=self._prewarm_connection, daemon=True).start()

    def _prewarm_connection(self):
        """Pre-warm DNS and TLS handshake to Google API server on startup."""
        try:
            self.session.get("https://generativelanguage.googleapis.com", timeout=3.0)
        except Exception:
            pass

    def play_sound(self, sound_name):
        if not self.cfg.get("sound_feedback", False):
            return
        sound_path = f"/usr/share/sounds/freedesktop/stereo/{sound_name}.oga"
        player = shutil.which("paplay") or shutil.which("pw-play") or shutil.which("aplay")
        if player and os.path.exists(sound_path):
            try:
                subprocess.Popen([player, sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def show_notification(self, title, message, timeout_ms=2500):
        if not self.cfg.get("notify", True):
            return
        if not shutil.which("notify-send"):
            return
        env = os.environ.copy()
        env["DISPLAY"] = env.get("DISPLAY", ":0")
        def _notify():
            try:
                subprocess.run([
                    "notify-send",
                    "-t", str(timeout_ms),
                    "-u", "normal",
                    "-a", "WhisperFlow",
                    title,
                    message
                ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5)
            except Exception:
                pass
        threading.Thread(target=_notify, daemon=True).start()

    def on_press(self, key):
        if key == keyboard.Key.esc and self.is_locked_recording:
            with self.lock:
                if self.is_locked_recording:
                    self.is_locked_recording = False
                    hold_duration = time.time() - self.press_start_time
                    self._stop_recording_locked(hold_duration)
            return

        if not is_matching_key(key, self.trigger_key_str):
            return

        now = time.time()
        with self.lock:
            if self.is_locked_recording:
                self.is_locked_recording = False
                hold_duration = now - self.press_start_time
                self._stop_recording_locked(hold_duration)
                return

            if self.key_is_down:
                return
            self.key_is_down = True

            if now - self.last_release_time < self.double_tap_interval:
                self.is_locked_recording = True
                print("[whisperflow] 🔒 HANDS-FREE LOCKED ON! Speak freely. Tap Shift or Esc to finish.")
                self.show_notification("Hands-Free Mode Active", "Microphone locked ON. Speak as long as you want. Tap Shift or Esc to finish.")
                self.play_sound("bell")
                return

            self.press_start_time = now
            self._start_recording_locked()

    def on_release(self, key):
        if not is_matching_key(key, self.trigger_key_str):
            return

        now = time.time()
        with self.lock:
            if not self.key_is_down:
                return
            self.key_is_down = False
            self.last_release_time = now

            if self.is_locked_recording:
                return

            hold_duration = now - self.press_start_time
            self._stop_recording_locked(hold_duration)

    def _spawn_recorder(self, output_path):
        """
        High-fidelity audio recording.
        Prefers pw-record (native PipeWire with crystal-clear 16kHz capture)
        with fallback to ffmpeg pulse or arecord.
        """
        env = os.environ.copy()
        if "XDG_RUNTIME_DIR" not in env:
            uid = os.getuid()
            user_runtime = f"/run/user/{uid}"
            if os.path.exists(user_runtime):
                env["XDG_RUNTIME_DIR"] = user_runtime

        # 1. Native PipeWire recorder (Highest fidelity, exact system default mic)
        if shutil.which("pw-record"):
            try:
                p = subprocess.Popen([
                    "pw-record",
                    "--rate", "16000",
                    "--channels", "1",
                    output_path
                ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return p
            except Exception:
                pass

        # 2. FFmpeg pulse audio capture (direct connection to active PulseAudio/PipeWire sink)
        if shutil.which("ffmpeg"):
            try:
                p = subprocess.Popen([
                    "ffmpeg",
                    "-y", "-v", "quiet",
                    "-f", "pulse", "-i", "default",
                    "-ar", "16000", "-ac", "1",
                    output_path
                ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return p
            except Exception:
                pass

        # 3. ALSA arecord fallback
        if shutil.which("arecord"):
            try:
                p = subprocess.Popen([
                    "arecord",
                    "-f", "cd",
                    "-t", "wav",
                    "-r", "16000",
                    "-c", "1",
                    "-q",
                    output_path
                ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return p
            except Exception:
                pass

        return None

    def _start_recording_locked(self):
        if self.is_recording:
            return
        self.is_recording = True

        session_id = uuid.uuid4().hex[:8]
        self.current_wav = os.path.join(tempfile.gettempdir(), f"gwf_{os.getpid()}_{session_id}.wav")
        self.record_proc = self._spawn_recorder(self.current_wav)

        if not self.record_proc:
            print("[whisperflow] ERROR: No audio recorder found.")
            self.show_notification("Audio Error", "No recorder installed.")
            self.is_recording = False
            return

        key_label = self.trigger_key_str.replace("_", " ").title()
        print(f"[whisperflow] 🔴 Recording active: [{key_label}] (Hold to talk, or double-tap to lock)...")
        self.play_sound("bell")

    def _stop_recording_locked(self, hold_duration):
        if not self.is_recording:
            return
        self.is_recording = False
        self.is_locked_recording = False

        proc = self.record_proc
        wav_file = self.current_wav
        self.record_proc = None
        self.current_wav = None

        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()

        if hold_duration < self.min_hold_seconds:
            self._cleanup_files(wav_file)
            return

        mins = int(hold_duration // 60)
        secs = int(hold_duration % 60)
        dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        print(f"[whisperflow] ⚡ Processing audio ({dur_str})...")
        self.show_notification("Processing...", f"Transcribing & cleaning ({dur_str})...")
        threading.Thread(target=self._process_and_paste, args=(wav_file, hold_duration), daemon=True).start()

    def _resolve_api_key(self):
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if key and key != "YOUR_GEMINI_API_KEY_HERE":
            return key

        cfg_key = self.cfg.get("gemini_api_key", "").strip()
        if cfg_key and cfg_key != "YOUR_GEMINI_API_KEY_HERE":
            return cfg_key

        cli_conf = os.path.expanduser("~/.config/gemini-api/config.json")
        if os.path.exists(cli_conf):
            try:
                with open(cli_conf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    k = data.get("api_key") or data.get("gemini_api_key")
                    if k:
                        return k.strip()
            except Exception:
                pass

        return ""

    def _transcribe_audio_stage1(self, audio_file, mime_type, model, api_key, duration_sec):
        """
        Stage 1: High-accuracy audio transcription (Temperature 0.0 for zero hallucination).
        """
        with open(audio_file, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        api_timeout = max(15.0, min(180.0, 15.0 + (duration_sec * 0.15)))
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": STAGE1_AUDIO_PROMPT}]},
            "contents": [{"parts": [{"inline_data": {"mime_type": mime_type, "data": audio_b64}}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 16384}
        }

        try:
            resp = self.session.post(url, json=payload, timeout=api_timeout)
        except Exception:
            self.session = create_robust_session()
            resp = self.session.post(url, json=payload, timeout=api_timeout)

        if resp.status_code != 200:
            print(f"[whisperflow] Stage 1 API Error HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        candidates = resp.json().get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        return parts[0].get("text", "").strip() if parts else ""

    def _clean_text_stage2(self, raw_transcript, model, api_key):
        """
        Stage 2: Strict Fluff Removal & Tech Phonetic Alignment (Temperature 0.0).
        """
        prompt = get_cleanup_prompt()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": prompt}]},
            "contents": [{"parts": [{"text": raw_transcript}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 16384}
        }

        try:
            resp = self.session.post(url, json=payload, timeout=20.0)
        except Exception:
            self.session = create_robust_session()
            resp = self.session.post(url, json=payload, timeout=20.0)

        if resp.status_code != 200:
            print(f"[whisperflow] Stage 2 API Error HTTP {resp.status_code}. Using raw transcript.")
            return raw_transcript

        candidates = resp.json().get("candidates", [])
        if not candidates:
            return raw_transcript

        parts = candidates[0].get("content", {}).get("parts", [])
        clean_text = parts[0].get("text", "").strip() if parts else raw_transcript
        return clean_text

    def _process_and_paste(self, wav_path, hold_duration_sec):
        t0 = time.time()

        if not wav_path or not os.path.exists(wav_path) or os.path.getsize(wav_path) < 2500:
            print("[whisperflow] Audio input too short or silent.")
            self._cleanup_files(wav_path)
            return

        audio_file = wav_path
        try:
            t_c0 = time.time()
            audio_file, mime_type = compress_audio_fast(wav_path)
            t_compress = time.time() - t_c0

            api_key = self._resolve_api_key()
            if not api_key:
                print("[whisperflow] Error: Missing GEMINI_API_KEY in environment or config.json")
                self.show_notification("Configuration Error", "Please configure gemini_api_key in config.json")
                return

            model = self.cfg.get("model", "gemini-3.5-flash-lite")

            # Stage 1: Audio Transcription
            t_stg1 = time.time()
            raw_text = self._transcribe_audio_stage1(audio_file, mime_type, model, api_key, hold_duration_sec)
            t_stage1 = time.time() - t_stg1

            if not raw_text or raw_text in ("<noise>", "<silence>", "[noise]", "[silence]"):
                print("[whisperflow] No speech detected in audio.")
                self.show_notification("Notice", "No speech detected.")
                return

            # Stage 2: Deep Fluff Removal & Restructuring
            final_text = raw_text
            t_stage2 = 0.0
            if self.cfg.get("clean_transcript", True):
                t_stg2 = time.time()
                final_text = self._clean_text_stage2(raw_text, model, api_key)
                t_stage2 = time.time() - t_stg2

            elapsed = round(time.time() - t0, 2)
            file_kb = round(os.path.getsize(audio_file) / 1024, 1)
            print(f"[whisperflow] 🚀 Done in {elapsed}s (aud: {t_stage1:.2f}s, clean: {t_stage2:.2f}s, comp: {t_compress:.2f}s, {file_kb}KB):")
            print(f'              Raw   : "{raw_text}"')
            print(f'              Clean : "{final_text}"')

            self.play_sound("complete")
            self._paste_text(final_text)
            self.show_notification("Done", final_text[:60] + ("..." if len(final_text) > 60 else ""))

        except Exception as e:
            print(f"[whisperflow] Processing exception: {e}")
            self.show_notification("Error", str(e))
        finally:
            self._cleanup_files(wav_path, audio_file)

    def _cleanup_files(self, *paths):
        for p in paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    def _paste_text(self, text):
        """
        Safe non-blocking clipboard injection and paste.
        """
        env = os.environ.copy()
        env["DISPLAY"] = env.get("DISPLAY", ":0")
        raw_bytes = text.encode("utf-8")

        is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
        if is_wayland and shutil.which("wl-copy"):
            try:
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, env=env)
                p.communicate(input=raw_bytes, timeout=0.8)
            except Exception:
                pass
        elif shutil.which("xclip"):
            for sel in ("clipboard", "primary"):
                try:
                    p = subprocess.Popen(["xclip", "-selection", sel, "-quiet"], stdin=subprocess.PIPE, env=env)
                    p.communicate(input=raw_bytes, timeout=0.8)
                except Exception:
                    pass

        time.sleep(0.04)
        if shutil.which("xdotool"):
            try:
                subprocess.run(
                    ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=1.5
                )
            except Exception:
                pass
        elif is_wayland and shutil.which("wtype"):
            try:
                subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5)
            except Exception:
                pass
        elif shutil.which("ydotool"):
            try:
                subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5)
            except Exception:
                pass

def main():
    config = load_config()
    daemon = VoiceFlowDaemon(config)
    trigger = config.get("trigger_key", "shift_r")

    print("=" * 68)
    print("🚀 Gemini WhisperFlow (Hold Right Shift | Double-Tap to Lock ON)")
    print(f"Trigger : [Hold {trigger.replace('_', ' ').title()}] OR [Double-Tap to Lock]")
    print(f"Engine  : High-Fidelity PipeWire Capture + Anti-Hallucination Pipeline")
    print(f"Model   : {config.get('model', 'gemini-3.5-flash-lite')}")
    print(f"Mode    : {'Clean Dictation' if config.get('clean_transcript', True) else 'Verbatim'}")
    print(f"Config  : {CONFIG_PATH}")
    print("=" * 68 + "\n")

    with keyboard.Listener(on_press=daemon.on_press, on_release=daemon.on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nDaemon stopped.")

if __name__ == "__main__":
    main()

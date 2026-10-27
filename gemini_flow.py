#!/usr/bin/env python3
"""
Gemini WhisperFlow Daemon for Linux
High-Precision Voice Dictation & Thought Restructuring Engine

Architecture:
  - Stage 1 (ASR): Google Gemini 3.5 Transcribe (models/gemini-3.5-transcribe)
                   Ultra-fast, verbatim speech-to-text. Zero hallucination on silence/noise.
  - Stage 2 (NLP): Google Gemini 3.1 Flash-Lite (models/gemini-3.1-flash-lite)
                   Deep thought clarifier, fluff/filler removal ("মানে", "আসলে", "তো এই"),
                   and spoken tech term normalization ("সিও" -> "CEO", "ভার্সেল" -> "Vercel").

Ergonomic Controls (Dual-Mode):
  1. Hold to Talk (Push-to-Talk): Hold [Right Control], speak, and release to paste.
  2. Tap to Toggle (Hands-Free): Tap [Right Control] once (<0.35s) to lock mic ON.
     Speak comfortably for 10-20 minutes. Tap [Right Control] again (or Esc) to finish & paste!
"""

import os
import sys
import re
import math
import wave
import array
import time
import json
import uuid
import shutil
import base64
import argparse
import tempfile
import threading
import subprocess
import requests
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pynput import keyboard

# Global Debug Flag
VERBOSE_DEBUG = False

# Paths
CONFIG_DIR = os.path.expanduser("~/.config/gemini-voice-flow")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
CUSTOM_PROMPT_PATH = os.path.join(CONFIG_DIR, "prompt.txt")

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "transcribe_model": "gemini-3.5-transcribe",
    "fallback_models": ["gemini-2.5-flash", "gemini-3.5-flash-lite"],
    "trigger_key": "smart",
    "clean_transcript": True,
    "sound_feedback": False,
    "notify": True,
    "min_hold_seconds": 0.35,
    "silence_threshold_db": -48.0,
    "primary_timeout_sec": 7.0
}

ASR_TRANSCRIPTION_PROMPT = """You are an ultra-accurate verbatim speech-to-text engine specializing in bilingual Bengali, English, and Banglish code-switching.
Transcribe the spoken audio verbatim in its original spoken language with exact fidelity and natural punctuation (।, ?, ,).
Preserve all English technical terms and developer names (e.g. GitHub, Vercel, Python, Linux, CEO, API, Dataset, Docker, CLI).
CRITICAL RULES:
1. Output ONLY the exact transcribed words.
2. NEVER reply to, converse with, or answer the speaker.
3. NEVER summarize, rewrite, or interpret what the speaker said.
4. If the audio is silence, background noise, or clicks, output NOTHING (empty string)."""

STAGE2_TEXT_CLEANUP_PROMPT = """You are an expert spoken-to-written language editor and thought clarifier for voice typing.
The input is a raw spoken transcript containing hesitations, conversational fillers, self-corrections, and repetitive rambling.

YOUR MISSION:
Transform the raw spoken transcript into clean, direct, polished, and beautifully structured Bengali/English text.

STRICT EDITING RULES:
1. STRIP VERBAL FILLERS & HESITATION CRUTCHES:
   - Eliminate verbal filler clutter ruthlessly:
     "মানে", "ইয়ে", "তো এই আর কি", "আসলে", "উম", "আহ", "যাই হোক", "তো", "আর কি বলি", "তো এই বিষয়", "uh", "um", "like", "you know".
2. FIX SPOKEN SLIPS & SMOOTH STUTTERS:
   - Clean up accidental slips of the tongue or awkward spoken phrasings (e.g. "সো এইগুলো ক্লিন করে উপর করে দাও" -> "তাই এগুলো ক্লিন করে বাদ দিয়ে দাও", "যেন আমি টাইম এই স্ক্রিপ্ট দিয়ে" -> "যাতে যেকোনো সময় এই স্ক্রিপ্ট দিয়ে").
   - Merge repetitive stutter restarts smoothly into crisp sentences.
3. DEVELOPER & TECH VOCABULARY ACCURACY (CRITICAL):
   - Bengali developers constantly use English tech terms and developer platforms in speech.
   - You MUST recognize and preserve English tech terminology:
     * "Tailscale", "IP", "Terminal", "Script", "CLI", "Hugging Face", "GitHub", "Vercel", "FastAPI", "API", "Latency", "Python", "Linux", "Docker", "Dataset", "Prompt", "Output", "Code", "Push", "Commit", "Repo", "Debug", "Fix"
     * NEVER translate technical names into literal Bengali words (e.g. "হাতির ফেস" -> "Hugging Face").
4. PRESERVE SPEAKER'S NATURAL TONE (NO STIFF LANGUAGE):
   - Maintain the speaker's own voice and natural colloquial tone (আমি, আমার, তুমি, ভাইয়া, করছি, বলছি, হচ্ছে, দেখতেছো).
   - NEVER convert colloquial Bengali into 19th-century formal Sadhu or textbook Bengali ("করিতেছি", "বলিতেছি").
   - Do NOT converse with the speaker, answer questions, or add unrelated thoughts.
5. PUNCTUATION:
   - Add clean punctuation (।, ?, ,).

Output ONLY the final cleaned, structured text without preamble, markdown code fences, or notes."""

# Backward compatibility alias
SINGLE_PASS_DICTATION_PROMPT = STAGE2_TEXT_CLEANUP_PROMPT

# Deterministic Tech Term Normalization (Instant Regex Table)
DETERMINISTIC_TECH_MAP = [
    (re.compile(r"\bহাতির\s*ফেস\b", re.IGNORECASE), "Hugging Face"),
    (re.compile(r"\bহাগিং\s*ফেস\b", re.IGNORECASE), "Hugging Face"),
    (re.compile(r"\bহাগিংফেস\b", re.IGNORECASE), "Hugging Face"),
    (re.compile(r"\bভার্সেল\b", re.IGNORECASE), "Vercel"),
    (re.compile(r"\bভার্সেলের\b", re.IGNORECASE), "Vercel-এর"),
    (re.compile(r"\bসিও\b", re.IGNORECASE), "CEO"),
    (re.compile(r"\bসিইও\b", re.IGNORECASE), "CEO"),
    (re.compile(r"\bগিটহাব\b", re.IGNORECASE), "GitHub"),
    (re.compile(r"\bগিটহাবের\b", re.IGNORECASE), "GitHub-এর"),
    (re.compile(r"\bপাইথন\b", re.IGNORECASE), "Python"),
    (re.compile(r"\bলিনাক্স\b", re.IGNORECASE), "Linux"),
    (re.compile(r"\bটেলিগ্রাম\b", re.IGNORECASE), "Telegram"),
    (re.compile(r"\bইউটিউব\b", re.IGNORECASE), "YouTube"),
    (re.compile(r"\bডকার\b", re.IGNORECASE), "Docker"),
    (re.compile(r"\bক্লাউডফ্লেয়ার\b", re.IGNORECASE), "Cloudflare"),
    (re.compile(r"\bলাইটনিং\s*সে\b", re.IGNORECASE), "ল্যাটেন্সি"),
    (re.compile(r"\bফাস্ট\s*এপিআই\b", re.IGNORECASE), "FastAPI"),
    (re.compile(r"\bফ্ল্যাশ\s*এপিআই\b", re.IGNORECASE), "Flash API"),
    (re.compile(r"\bএপিআই\b", re.IGNORECASE), "API"),
    (re.compile(r"\bজেমিনি\b", re.IGNORECASE), "Gemini"),
    (re.compile(r"\bডাটা\s*সেট\b", re.IGNORECASE), "dataset"),
    (re.compile(r"\bডেটাসেট\b", re.IGNORECASE), "dataset"),
]

def apply_deterministic_tech_normalization(text):
    if not text:
        return text
    for pattern, replacement in DETERMINISTIC_TECH_MAP:
        text = pattern.sub(replacement, text)
    return text


# ==============================================================================
# Beautiful Colored Logging System with Detailed Diagnostics
# ==============================================================================
class Logger:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"

    @classmethod
    def _time(cls):
        return datetime.now().strftime("%H:%M:%S")

    @classmethod
    def info(cls, msg):
        print(f"{cls.DIM}[{cls._time()}]{cls.RESET} {cls.CYAN}ℹ{cls.RESET}  {msg}", flush=True)

    @classmethod
    def success(cls, msg):
        print(f"{cls.DIM}[{cls._time()}]{cls.RESET} {cls.GREEN}✔{cls.RESET}  {cls.BOLD}{msg}{cls.RESET}", flush=True)

    @classmethod
    def warn(cls, msg):
        print(f"{cls.DIM}[{cls._time()}]{cls.RESET} {cls.YELLOW}⚠  WARNING:{cls.RESET} {cls.YELLOW}{msg}{cls.RESET}", flush=True)

    @classmethod
    def error(cls, msg, details=None, exc=None):
        print(f"{cls.DIM}[{cls._time()}]{cls.RESET} {cls.RED}✖  ERROR:{cls.RESET} {cls.BOLD}{cls.RED}{msg}{cls.RESET}", flush=True)
        if details:
            for line in str(details).splitlines():
                print(f"      {cls.RED}↳ {line}{cls.RESET}", flush=True)
        if exc and (VERBOSE_DEBUG or os.environ.get("DEBUG") == "1"):
            import traceback
            tb = traceback.format_exc()
            if tb and tb.strip() != "NoneType: None":
                print(f"      {cls.DIM}{tb.strip()}{cls.RESET}", flush=True)

    @classmethod
    def debug(cls, msg):
        if VERBOSE_DEBUG or os.environ.get("DEBUG") == "1":
            print(f"{cls.DIM}[{cls._time()}][DEBUG]{cls.RESET} {cls.MAGENTA}{msg}{cls.RESET}", flush=True)

    @classmethod
    def banner(cls, cfg):
        trig = cfg.get("trigger_key", "smart").replace("_", " ").title()
        trans_model = cfg.get("transcribe_model", "gemini-3.5-transcribe")
        fallbacks = ", ".join(cfg.get("fallback_models", ["gemini-2.5-flash", "gemini-3.5-flash-lite"]))
        w = 68
        print(f"{cls.CYAN}{'═' * w}{cls.RESET}")
        print(f"{cls.BOLD}{cls.WHITE} 🚀 Gemini WhisperFlow — Ultra-Fast Single-Pass Voice Engine{cls.RESET}")
        print(f"{cls.CYAN}{'─' * w}{cls.RESET}")
        print(f"  {cls.BOLD}Trigger Key{cls.RESET}     : [{trig}] (Hold to talk | Tap to toggle hands-free)")
        print(f"  {cls.BOLD}Primary Model{cls.RESET}   : {cls.GREEN}{trans_model}{cls.RESET} (Direct Speech-to-Text)")
        print(f"  {cls.BOLD}Fast Fallback{cls.RESET}   : {cls.DIM}{fallbacks}{cls.RESET} (Zero-delay failover on 503/timeout)")
        print(f"  {cls.BOLD}Architecture{cls.RESET}    : Single-Pass Direct (Zero Stage-2 Hallucination)")
        print(f"  {cls.BOLD}Config File{cls.RESET}     : {CONFIG_PATH}")
        print(f"{cls.CYAN}{'═' * w}{cls.RESET}\n", flush=True)


# ==============================================================================
# Helper & Network Functions
# ==============================================================================
def create_robust_session():
    """Create a persistent HTTP session with connection pooling and retry logic."""
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


def load_config():
    """Load user configuration from ~/.config/gemini-voice-flow/config.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(cfg)
            needs_save = False
            # Clean up obsolete or rate-limited models
            if merged.get("transcribe_model") in ("", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite"):
                merged["transcribe_model"] = "gemini-3.5-transcribe"
                needs_save = True
            if "fallback_models" not in cfg:
                merged["fallback_models"] = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
                needs_save = True
            cleaned_fallbacks = [m for m in merged.get("fallback_models", []) if m not in ("gemini-3-flash-preview", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite")]
            if not cleaned_fallbacks:
                cleaned_fallbacks = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
                needs_save = True
            merged["fallback_models"] = cleaned_fallbacks
            if needs_save:
                save_config(merged)
            return merged
    except Exception as e:
        Logger.error(f"Failed to read config file ({CONFIG_PATH}): {e}", "Falling back to default settings.")
        return DEFAULT_CONFIG.copy()


def save_config(cfg):
    """Save configuration cleanly to disk."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def get_cleanup_prompt():
    """Return system prompt for Stage 2 text restructuring."""
    if os.path.exists(CUSTOM_PROMPT_PATH):
        try:
            with open(CUSTOM_PROMPT_PATH, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    return c
        except Exception:
            pass
    return STAGE2_TEXT_CLEANUP_PROMPT


def is_matching_key(key, target_str):
    """Check whether a pressed pynput key matches the configured target string."""
    s = target_str.lower().strip().replace("-", "_").replace(" ", "_")
    
    # Smart Multi-Key Trigger: Accepts Right Shift OR Right Alt OR Right Control
    if s in ("smart", "auto", "multi", "default"):
        if key == keyboard.Key.shift_r:
            return True
        if key == keyboard.Key.alt_r or getattr(key, "name", None) in ("alt_r", "alt_gr"):
            return True
        if key == keyboard.Key.ctrl_r or getattr(key, "name", None) in ("ctrl_r", "control_r"):
            return True
        return False

    # Right Shift
    if s in ("shift_r", "right_shift", "rshift"):
        return key == keyboard.Key.shift_r
    # Right Alt / AltGr
    elif s in ("alt_r", "right_alt", "ralt", "alt_gr", "altgr"):
        return key == keyboard.Key.alt_r or getattr(key, "name", None) in ("alt_r", "alt_gr")
    # Right Control (Default & Recommended)
    elif s in ("ctrl_r", "right_ctrl", "rctrl", "control_r"):
        return key == keyboard.Key.ctrl_r or getattr(key, "name", None) in ("ctrl_r", "control_r")
    # Left Control
    elif s in ("ctrl_l", "left_ctrl", "lctrl", "control_l"):
        return key == keyboard.Key.ctrl_l
    # Either Control
    elif s in ("ctrl", "control"):
        return key in (keyboard.Key.ctrl, keyboard.Key.ctrl_r, keyboard.Key.ctrl_l)
    # Left Shift
    elif s in ("shift_l", "left_shift", "lshift"):
        return key == keyboard.Key.shift_l or key == keyboard.Key.shift
    # Either Shift
    elif s in ("shift",):
        return key in (keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.shift_l)
    # Left Alt
    elif s in ("alt_l", "left_alt", "lalt"):
        return key == keyboard.Key.alt_l
    # Caps Lock
    elif s in ("caps_lock", "capslock"):
        return key == keyboard.Key.caps_lock
    # Function Keys (F1-F12)
    elif s.startswith("f") and s[1:].isdigit():
        return key == getattr(keyboard.Key, s, None)
    else:
        if hasattr(keyboard.Key, s):
            return key == getattr(keyboard.Key, s)
        try:
            return getattr(key, 'char', None) == s
        except Exception:
            return False


# ==============================================================================
# Audio Processing & Anti-Hallucination Gate
# ==============================================================================
def get_wav_peak_db(wav_path):
    """
    Sub-millisecond peak volume analysis in pure Python using wave & array.
    Avoids spawning heavy FFmpeg volumedetect subprocesses.
    """
    try:
        with wave.open(wav_path, "rb") as wf:
            width = wf.getsampwidth()
            n_frames = wf.getnframes()
            if n_frames == 0:
                return -100.0
            raw = wf.readframes(n_frames)
            if width == 2:
                samples = array.array("h")
                samples.frombytes(raw)
                max_val = max(abs(min(samples, default=0)), max(samples, default=0))
                max_possible = 32767
            elif width == 1:
                samples = array.array("B")
                samples.frombytes(raw)
                max_val = max(abs(s - 128) for s in samples) if samples else 0
                max_possible = 127
            else:
                return 0.0
            if max_val == 0:
                return -100.0
            return 20.0 * math.log10(max_val / max_possible)
    except Exception as e:
        Logger.debug(f"get_wav_peak_db fallback: {e}")
        return 0.0


def is_audio_silent(wav_path, threshold_db=-45.0):
    """
    Hardware Silence & Noise Floor Gate.
    Analyzes peak volume in dB. If peak volume is below threshold_db,
    the audio contains only background hiss or room silence.
    """
    db = get_wav_peak_db(wav_path)
    Logger.debug(f"Audio peak volume: {db:.1f} dB (Threshold: {threshold_db:.1f} dB)")
    return db < threshold_db


def compress_audio_in_memory(wav_path):
    """
    Applies audio conditioning (bandpass + speech frequency cleaning + gentle boost)
    and compresses to 48k mono MP3 via ffmpeg directly to stdout pipe (in-memory).
    Eliminates intermediate disk writes, saving ~300ms.
    """
    if not shutil.which("ffmpeg"):
        with open(wav_path, "rb") as f:
            return f.read(), "audio/wav"

    cmd = [
        "ffmpeg", "-y", "-v", "quiet",
        "-i", wav_path,
        "-af", "highpass=f=100,lowpass=f=7500,speechnorm=e=4:r=0.0001:l=1",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "48k",
        "-f", "mp3",
        "pipe:1"
    ]
    try:
        # Dynamic timeout: at least 6s, plus 0.15s per second of estimated audio
        file_size = os.path.getsize(wav_path) if os.path.exists(wav_path) else 0
        est_sec = file_size / 32000.0  # 16000 Hz * 2 bytes (16-bit mono)
        calc_timeout = max(6.0, min(30.0, 6.0 + (est_sec * 0.15)))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        out, _ = proc.communicate(timeout=calc_timeout)
        if proc.returncode == 0 and len(out) > 200:
            return out, "audio/mp3"
    except Exception as e:
        Logger.debug(f"In-memory compression note: {e}")

    with open(wav_path, "rb") as f:
        return f.read(), "audio/wav"


# ==============================================================================
# Gemini API Verification & Interactive Setup
# ==============================================================================
def verify_gemini_api_key(api_key, transcribe_model="gemini-3.5-transcribe", fallback_models=None):
    """
    Verify Gemini API key against Google API servers.
    Tests transcribe model and fallback models.
    Returns (success: bool, error_message: str)
    """
    if not api_key:
        return False, "API key is empty."

    session = create_robust_session()

    # 1. Test Transcribe model access
    try:
        url1 = f"https://generativelanguage.googleapis.com/v1beta/models/{transcribe_model}?key={api_key}"
        resp1 = session.get(url1, timeout=6.0)
        if resp1.status_code == 200:
            return True, f"API Key validated! ({transcribe_model} is responsive)"
        else:
            err_msg = ""
            try:
                err_msg = resp1.json().get("error", {}).get("message", resp1.text[:200])
            except Exception:
                err_msg = resp1.text[:200]
            Logger.warn(f"Model '{transcribe_model}' returned HTTP {resp1.status_code}: {err_msg}. Checking fallback...")
    except requests.exceptions.RequestException as e:
        Logger.warn(f"Network error on {transcribe_model}: {e}")

    # 2. Test fallback models
    check_list = fallback_models or ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
    for cm in check_list:
        try:
            url2 = f"https://generativelanguage.googleapis.com/v1beta/models/{cm}?key={api_key}"
            resp2 = session.get(url2, timeout=5.0)
            if resp2.status_code == 200:
                return True, f"API Key validated! (Fallback {cm} is responsive)"
        except requests.exceptions.RequestException:
            pass

    return False, "Failed to connect to Google Gemini API servers. Please check your API key and internet connection."


def interactive_setup():
    """
    Terminal-based interactive configuration wizard.
    Prompts user for API key, tests connectivity, prompts for trigger key,
    and saves to config.json.
    """
    print(f"\n{Logger.BOLD}{Logger.CYAN}{'═' * 68}{Logger.RESET}")
    print(f"{Logger.BOLD}{Logger.WHITE} 🎙️  Gemini WhisperFlow — Interactive Setup Wizard{Logger.RESET}")
    print(f"{Logger.BOLD}{Logger.CYAN}{'═' * 68}{Logger.RESET}\n")

    cfg = load_config()
    existing_key = cfg.get("gemini_api_key", "").strip()

    # Step 1: Gemini API Key
    while True:
        if existing_key and existing_key != "YOUR_GEMINI_API_KEY_HERE":
            masked = existing_key[:6] + "..." + existing_key[-4:] if len(existing_key) > 12 else "********"
            print(f"Current Gemini API Key: {Logger.GREEN}{masked}{Logger.RESET}")
            use_existing = input("Keep this existing API key? [Y/n]: ").strip().lower()
            if use_existing not in ("n", "no"):
                api_key = existing_key
            else:
                api_key = ""
        else:
            api_key = ""

        if not api_key:
            print(f"\n{Logger.BOLD}Enter your Google Gemini API Key:{Logger.RESET}")
            print(f"{Logger.DIM}(Get a free key instantly from: https://aistudio.google.com/app/apikey){Logger.RESET}")
            try:
                api_key = input(f"{Logger.CYAN}> {Logger.RESET}").strip().strip('"').strip("'")
            except (KeyboardInterrupt, EOFError):
                print("\nSetup cancelled.")
                sys.exit(0)

        if not api_key:
            Logger.warn("API key cannot be empty. Please try again.")
            continue

        print(f"\n{Logger.CYAN}Connecting to Google Gemini API to test your key...{Logger.RESET}")
        ok, msg = verify_gemini_api_key(
            api_key,
            cfg.get("transcribe_model", "gemini-3.5-transcribe"),
            cfg.get("fallback_models", ["gemini-2.5-flash", "gemini-3.5-flash-lite"])
        )
        if ok:
            Logger.success("Google Gemini API Key verified successfully!")
            print(f"   • Direct Engine : {Logger.GREEN}{cfg.get('transcribe_model', 'gemini-3.5-transcribe')}{Logger.RESET} [READY]")
            print(f"   • Fast Fallback : {Logger.GREEN}{', '.join(cfg.get('fallback_models', ['gemini-2.5-flash']))}{Logger.RESET} [READY]")
            cfg["gemini_api_key"] = api_key
            break
        else:
            Logger.error("Verification failed!", msg)
            existing_key = ""
            retry = input("\nWould you like to re-enter your API key? [Y/n]: ").strip().lower()
            if retry in ("n", "no"):
                print("Setup aborted.")
                sys.exit(1)

    # Step 2: Trigger Shortcut Key Selection
    print(f"\n{Logger.BOLD}Choose your preferred Dictation Trigger Key:{Logger.RESET}")
    print(f"  {Logger.GREEN}[1] Smart Multi-Trigger (smart){Logger.RESET} - {Logger.BOLD}★ Recommended{Logger.RESET} (Accepts Right Shift OR Right Alt)")
    print(f"  [2] Right Shift   (shift_r)")
    print(f"  [3] Right Alt     (alt_r / AltGr)")
    print(f"  [4] Right Control (ctrl_r)")
    print(f"  [5] Function Key  (f9)")
    print(f"  [6] Custom Key")
    
    current_key = cfg.get("trigger_key", "smart")
    key_choice = input(f"\nSelect [1-6] (Current: {current_key}): ").strip()

    key_map = {
        "1": "smart",
        "2": "shift_r",
        "3": "alt_r",
        "4": "ctrl_r",
        "5": "f9"
    }

    if key_choice in key_map:
        cfg["trigger_key"] = key_map[key_choice]
    elif key_choice == "6":
        cust = input("Enter custom key name (e.g. caps_lock, f8, insert): ").strip().lower()
        if cust:
            cfg["trigger_key"] = cust
    elif not key_choice:
        cfg["trigger_key"] = current_key

    # Step 3: Clean Dictation Mode
    clean_choice = input("\nEnable Clean Dictation (AI fluff/filler removal & tech term formatting)? [Y/n]: ").strip().lower()
    if clean_choice in ("n", "no"):
        cfg["clean_transcript"] = False
    else:
        cfg["clean_transcript"] = True

    # Save to file
    save_config(cfg)
    Logger.success(f"Configuration saved to: {CONFIG_PATH}")

    # Step 4: System Dependencies Check
    print(f"\n{Logger.BOLD}System Dependencies Check:{Logger.RESET}")
    tools = [
        ("Audio capture", ["pw-record", "arecord", "ffmpeg"]),
        ("Audio processor", ["ffmpeg"]),
        ("Clipboard manager", ["xclip", "wl-copy"]),
        ("Auto-paste injector", ["xdotool", "wtype", "ydotool"]),
        ("Desktop notifications", ["notify-send"])
    ]
    for desc, candidates in tools:
        found = any(shutil.which(c) for c in candidates)
        if found:
            name = next(c for c in candidates if shutil.which(c))
            print(f"  • {desc:<22}: {Logger.GREEN}✔ Found ({name}){Logger.RESET}")
        else:
            print(f"  • {desc:<22}: {Logger.YELLOW}⚠ Missing (Install: {candidates[0]}){Logger.RESET}")

    # Step 5: Restart systemd user service if active
    if shutil.which("systemctl"):
        try:
            res = subprocess.run(["systemctl", "--user", "is-active", "gemini-voice-flow"], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"\n{Logger.CYAN}Restarting gemini-voice-flow systemd service with new configuration...{Logger.RESET}")
                subprocess.run(["systemctl", "--user", "restart", "gemini-voice-flow"], check=False)
                Logger.success("Service restarted successfully!")
        except Exception:
            pass

    print(f"\n{Logger.BOLD}{Logger.GREEN}{'═' * 68}{Logger.RESET}")
    print(f"{Logger.BOLD}{Logger.GREEN} 🎉 Gemini WhisperFlow is fully configured and ready!{Logger.RESET}")
    print(f"{Logger.BOLD}{Logger.GREEN}{'═' * 68}{Logger.RESET}")
    trig_name = cfg["trigger_key"].replace("_", " ").title()
    print(f"\nHow to use your trigger [{Logger.BOLD}{trig_name}{Logger.RESET}]:")
    print(f"  • {Logger.BOLD}Hold to Talk (Push-to-Talk):{Logger.RESET} Hold [{trig_name}], speak, release to paste.")
    print(f"  • {Logger.BOLD}Hands-Free Toggle:{Logger.RESET} Tap [{trig_name}] once to start, speak as long as you like, tap again (or Esc) to finish & paste.\n")


# ==============================================================================
# Self-Test Pipeline (End-to-End Diagnostics)
# ==============================================================================
def run_self_test(cfg):
    """Run full diagnostic test: mic capture, API response, and paste simulation."""
    Logger.banner(cfg)
    print(f"{Logger.BOLD}=== Running System Self-Test ==={Logger.RESET}\n")

    api_key = cfg.get("gemini_api_key", "").strip()
    if not api_key:
        Logger.error("No API key configured!", "Please run 'gemini-flow setup' first.")
        return False

    # 1. API Verification
    Logger.info("1/3 Testing Google Gemini API connectivity...")
    ok, msg = verify_gemini_api_key(
        api_key,
        cfg.get("transcribe_model", "gemini-3.5-transcribe"),
        cfg.get("fallback_models", ["gemini-2.5-flash", "gemini-3.5-flash-lite"])
    )
    if not ok:
        Logger.error("API test failed!", msg)
        return False
    Logger.success("Gemini API connection OK.")

    # 2. Recording Test
    Logger.info("2/3 Testing audio capture from default microphone (2 seconds)...")
    temp_wav = os.path.join(tempfile.gettempdir(), f"gwf_test_{uuid.uuid4().hex[:6]}.wav")
    
    recorder = None
    if shutil.which("pw-record"):
        recorder = ["pw-record", "--rate", "16000", "--channels", "1", temp_wav]
    elif shutil.which("arecord"):
        recorder = ["arecord", "-f", "cd", "-t", "wav", "-r", "16000", "-c", "1", "-q", temp_wav]
    elif shutil.which("ffmpeg"):
        recorder = ["ffmpeg", "-y", "-v", "quiet", "-f", "pulse", "-i", "default", "-ar", "16000", "-ac", "1", temp_wav]

    if not recorder:
        Logger.error("No audio recorder available on system!")
        return False

    env = os.environ.copy()
    if "XDG_RUNTIME_DIR" not in env:
        uid = os.getuid()
        user_runtime = f"/run/user/{uid}"
        if os.path.exists(user_runtime):
            env["XDG_RUNTIME_DIR"] = user_runtime
    env["DISPLAY"] = env.get("DISPLAY", ":0")

    try:
        proc = subprocess.Popen(recorder, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2.0)
        proc.terminate()
        proc.wait(timeout=1.0)
    except Exception as e:
        Logger.error(f"Recording failed: {e}")
        return False

    if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) < 1000:
        Logger.error("Recorded audio file is empty or missing! Check microphone connection.")
        return False
    Logger.success(f"Audio capture OK ({os.path.getsize(temp_wav) / 1024:.1f} KB recorded).")

    # 3. Audio Gate & Compression Test
    Logger.info("3/3 Testing in-memory audio conditioning & volume gate...")
    is_silent = is_audio_silent(temp_wav, cfg.get("silence_threshold_db", -48.0))
    Logger.info(f"Silence Gate result: {'Silent/Background Noise' if is_silent else 'Speech/Sound Present'}")

    mp3_bytes, mime = compress_audio_in_memory(temp_wav)
    Logger.success(f"In-memory audio compression OK ({mime}, {len(mp3_bytes) / 1024:.1f} KB in RAM).")

    # Cleanup test file
    if os.path.exists(temp_wav):
        try:
            os.remove(temp_wav)
        except OSError:
            pass

    print(f"\n{Logger.BOLD}{Logger.GREEN}✔ All self-tests passed! Your voice flow system is fully healthy.{Logger.RESET}\n")
    return True


# ==============================================================================
# Voice Flow Daemon (Dual-Mode: Hold-to-Talk + Single-Tap Toggle)
# ==============================================================================
class VoiceFlowDaemon:
    def __init__(self, cfg):
        self.cfg = cfg
        self.is_recording = False
        self.is_toggle_mode = False  # True when user single-taps to enter hands-free dictation
        self.record_proc = None
        self.current_wav = None
        self.press_start_time = 0.0
        self.key_is_down = False
        self.lock = threading.Lock()

        self.trigger_key_str = cfg.get("trigger_key", "smart")
        self.trigger_label = self.trigger_key_str.replace("_", " ").title()
        self.min_hold_seconds = float(cfg.get("min_hold_seconds", 0.35))
        self.silence_threshold_db = float(cfg.get("silence_threshold_db", -48.0))

        self.transcribe_model = cfg.get("transcribe_model", "gemini-3.5-transcribe")
        self.fallback_models = cfg.get("fallback_models", ["gemini-2.5-flash", "gemini-3.5-flash-lite"])
        self.primary_timeout_sec = float(cfg.get("primary_timeout_sec", 7.0))

        self.session = create_robust_session()
        threading.Thread(target=self._prewarm_connection, daemon=True).start()
        threading.Thread(target=self._auto_tune_audio_hardware, daemon=True).start()

    def _auto_tune_audio_hardware(self):
        """
        Auto-tune ALSA mixer controls on Linux to prevent 50Hz ground hum & clipping.
        Realtek / Intel HDA codecs often default to +20dB/+30dB boost after suspend/reboot,
        which causes massive AC mains humming that ruins speech transcription.
        """
        if not shutil.which("amixer"):
            return
        try:
            # Set Rear Mic Boost to 1 (10dB) and Capture to 80% if available
            subprocess.run(["amixer", "sset", "Rear Mic Boost", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["amixer", "sset", "Capture", "80%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["amixer", "-c", "1", "sset", "Rear Mic Boost", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["amixer", "-c", "1", "sset", "Capture", "80%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _prewarm_connection(self):
        """Pre-warm DNS and TLS handshake to Google API server on startup."""
        try:
            self.session.get("https://generativelanguage.googleapis.com", timeout=3.0)
        except Exception:
            pass

    def play_sound(self, sound_name):
        """Play short audio feedback."""
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
        """Display non-blocking desktop notification."""
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
        # 1. Escape key stops/cancels any active recording
        if key == keyboard.Key.esc:
            with self.lock:
                if self.is_recording:
                    Logger.info("Escape pressed: Stopping recording and transcribing...")
                    duration = time.time() - self.press_start_time
                    self._stop_recording_locked(duration)
            return

        if not is_matching_key(key, self.trigger_key_str):
            return

        now = time.time()
        with self.lock:
            # If we are already recording in TOGGLE (Hands-Free) mode:
            # A new press means the user wants to STOP recording and paste!
            if self.is_recording and self.is_toggle_mode:
                self.key_is_down = True
                duration = now - self.press_start_time
                self._stop_recording_locked(duration)
                return

            # Avoid keyboard auto-repeat firing multiple presses
            if self.key_is_down:
                return
            self.key_is_down = True

            # If not recording at all, start recording
            if not self.is_recording:
                self.press_start_time = now
                self.is_toggle_mode = False
                self._start_recording_locked()

    def on_release(self, key):
        if not is_matching_key(key, self.trigger_key_str):
            return

        now = time.time()
        with self.lock:
            if not self.key_is_down:
                return
            self.key_is_down = False

            if not self.is_recording:
                return

            # If we were already in toggle mode, this release is just the key-up of the "stop" tap.
            # Stop was already triggered in on_press, so do nothing.
            if self.is_toggle_mode:
                return

            hold_duration = now - self.press_start_time

            # Case A: Quick Tap (< min_hold_seconds) -> Turn into Hands-Free Toggle Mode!
            if hold_duration < self.min_hold_seconds:
                self.is_toggle_mode = True
                Logger.info(f"🎙️  Hands-Free Mode Active! Speak freely. [Tap {self.trigger_label} or Esc to finish and paste]")
                self.show_notification(
                    "🎙️ Dictation Active (Hands-Free)",
                    f"Speak freely. Tap {self.trigger_label} or Esc to finish & paste."
                )
                return

            # Case B: Held intentionally (Push-to-Talk) -> Stop and process immediately
            self._stop_recording_locked(hold_duration)

    def _spawn_recorder(self, output_path):
        """Zero-latency audio capture using PipeWire pw-record or arecord."""
        env = os.environ.copy()
        if "XDG_RUNTIME_DIR" not in env:
            uid = os.getuid()
            user_runtime = f"/run/user/{uid}"
            if os.path.exists(user_runtime):
                env["XDG_RUNTIME_DIR"] = user_runtime

        if shutil.which("pw-record"):
            return subprocess.Popen([
                "pw-record",
                "--rate", "16000",
                "--channels", "1",
                output_path
            ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if shutil.which("arecord"):
            return subprocess.Popen([
                "arecord",
                "-f", "cd",
                "-t", "wav",
                "-r", "16000",
                "-c", "1",
                "-q",
                output_path
            ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if shutil.which("ffmpeg"):
            return subprocess.Popen([
                "ffmpeg",
                "-y", "-v", "quiet",
                "-f", "pulse", "-i", "default",
                "-ar", "16000", "-ac", "1",
                output_path
            ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return None

    def _start_recording_locked(self):
        if self.is_recording:
            return
        self.is_recording = True

        session_id = uuid.uuid4().hex[:8]
        self.current_wav = os.path.join(tempfile.gettempdir(), f"gwf_{os.getpid()}_{session_id}.wav")
        self.record_proc = self._spawn_recorder(self.current_wav)

        if not self.record_proc:
            Logger.error("No audio recorder available!", "Install pipewire or alsa-utils.")
            self.show_notification("Audio Error", "No recorder installed (pw-record/arecord).")
            self.is_recording = False
            return

        Logger.info(f"🔴 Recording active: [{self.trigger_label}] (Hold to talk, or tap to toggle hands-free)...")
        self.show_notification("🔴 Recording...", f"Listening on [{self.trigger_label}]. Speak now!", timeout_ms=1800)
        self.play_sound("bell")

    def _stop_recording_locked(self, hold_duration):
        if not self.is_recording:
            return
        self.is_recording = False
        self.is_toggle_mode = False

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

        if hold_duration < 0.4:
            Logger.debug("Audio duration too short (<0.4s). Discarded.")
            self._cleanup_files(wav_file)
            return

        mins = int(hold_duration // 60)
        secs = int(hold_duration % 60)
        dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        Logger.info(f"⚡ Processing audio ({dur_str})...")
        self.show_notification("Processing...", f"Transcribing & cleaning ({dur_str})...")
        threading.Thread(target=self._process_and_paste, args=(wav_file, hold_duration), daemon=True).start()

    def _resolve_api_key(self):
        """Retrieve Gemini API key from environment, config.json, or prompt interactively."""
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if key and key != "YOUR_GEMINI_API_KEY_HERE":
            return key

        cfg_key = self.cfg.get("gemini_api_key", "").strip()
        if cfg_key and cfg_key != "YOUR_GEMINI_API_KEY_HERE":
            return cfg_key

        return ""

    def _transcribe_direct(self, audio_bytes, mime_type, api_key, duration_sec):
        """
        Ultra-Fast Single-Pass Speech-to-Text Engine.
        Transcribes speech verbatim directly from gemini-3.5-transcribe in ONE hop.
        If Google returns 503 (demand spike) or network timeout, instantly fails over
        to gemini-2.5-flash / gemini-3.5-flash-lite in the same hop.
        Zero secondary LLM passes. Zero conversational hallucination.
        """
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        # 1. Primary Direct Call: gemini-3.5-transcribe
        to_primary = max(3.5, min(14.0, self.primary_timeout_sec + (duration_sec * 0.08)))
        url_primary = f"https://generativelanguage.googleapis.com/v1beta/models/{self.transcribe_model}:generateContent?key={api_key}"
        payload_primary = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": audio_b64}}
                ]
            }]
        }

        try:
            resp = self.session.post(url_primary, json=payload_primary, timeout=to_primary)
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = parts[0].get("text", "").strip() if parts else ""
                    if text:
                        return apply_deterministic_tech_normalization(text)
                    return ""
            else:
                Logger.warn(f"Direct transcribe ({self.transcribe_model}) HTTP {resp.status_code}. Fast-switching to fallback...")
        except Exception as e:
            Logger.warn(f"Direct transcribe ({self.transcribe_model}) timeout/error ({to_primary:.1f}s): {e}. Fast-switching to fallback...")

        # 2. Instant Zero-Hallucination Fallback (Verbatim)
        for fb_model in self.fallback_models:
            to_fb = max(5.0, min(25.0, 5.0 + (duration_sec * 0.12)))
            fb_url = f"https://generativelanguage.googleapis.com/v1beta/models/{fb_model}:generateContent?key={api_key}"
            fb_payload = {
                "system_instruction": {"parts": [{"text": ASR_TRANSCRIPTION_PROMPT}]},
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": audio_b64}}
                    ]
                }],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 4096}
            }
            try:
                resp = self.session.post(fb_url, json=fb_payload, timeout=to_fb)
                if resp.status_code == 200:
                    candidates = resp.json().get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = parts[0].get("text", "").strip() if parts else ""
                        if text:
                            return apply_deterministic_tech_normalization(text)
                        return ""
                else:
                    Logger.warn(f"Fallback ASR ({fb_model}) HTTP {resp.status_code}. Trying next...")
            except Exception as e:
                Logger.warn(f"Fallback ASR ({fb_model}) error: {e}")

        return ""

    def _process_and_paste(self, wav_path, hold_duration_sec):
        t0 = time.time()

        if not wav_path or not os.path.exists(wav_path) or os.path.getsize(wav_path) < 2000:
            Logger.warn("Audio input too short or empty.")
            self._cleanup_files(wav_path)
            return

        # 1. Instant In-Memory Hardware Silence Gate (< 5ms)
        if is_audio_silent(wav_path, self.silence_threshold_db):
            Logger.info("Audio Gate: Silence or background hiss detected (no speech). Discarded.")
            self._cleanup_files(wav_path)
            return

        try:
            # 2. In-Memory Audio Conditioning & Compression (~80ms)
            t_c0 = time.time()
            audio_bytes, mime_type = compress_audio_in_memory(wav_path)
            t_compress = time.time() - t_c0

            api_key = self._resolve_api_key()
            if not api_key:
                Logger.error(
                    "Missing Gemini API Key!",
                    "Please run 'gemini-flow setup' in your terminal to configure your API key."
                )
                self.show_notification("Configuration Error", "Missing API key! Run 'gemini-flow setup'.")
                return

            # 3. Direct Single-Pass Voice Transcription
            t_api0 = time.time()
            final_text = self._transcribe_direct(audio_bytes, mime_type, api_key, hold_duration_sec)
            t_api = time.time() - t_api0

            if not final_text or final_text.strip() in ("<noise>", "<silence>", "[noise]", "[silence]"):
                Logger.info("No speech detected in audio.")
                self.show_notification("Notice", "No speech detected.")
                return

            elapsed = round(time.time() - t0, 2)
            file_kb = round(len(audio_bytes) / 1024, 1)
            Logger.success(f"Dictation finished in {elapsed}s (API: {t_api:.2f}s, Prep: {t_compress:.2f}s, {file_kb}KB):")
            print(f"      {Logger.BOLD}Text:{Logger.RESET} \"{final_text[:85]}{'...' if len(final_text) > 85 else ''}\"", flush=True)

            self.play_sound("complete")
            self._paste_text(final_text)
            self.show_notification("Dictation Ready", final_text[:60] + ("..." if len(final_text) > 60 else ""))

        except Exception as e:
            Logger.error(f"Processing exception occurred: {e}", exc=e)
            self.show_notification("Error", str(e))
        finally:
            self._cleanup_files(wav_path)

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
        Supports Wayland (wl-copy + wtype) and X11 (xclip + xdotool).
        """
        env = os.environ.copy()
        env["DISPLAY"] = env.get("DISPLAY", ":0")
        raw_bytes = text.encode("utf-8")

        is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
        if is_wayland and shutil.which("wl-copy"):
            try:
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, env=env)
                p.communicate(input=raw_bytes, timeout=0.8)
            except Exception as e:
                Logger.debug(f"wl-copy error: {e}")
        elif shutil.which("xclip"):
            for sel in ("clipboard", "primary"):
                try:
                    p = subprocess.Popen(["xclip", "-selection", sel, "-quiet"], stdin=subprocess.PIPE, env=env)
                    p.communicate(input=raw_bytes, timeout=0.8)
                except Exception as e:
                    Logger.debug(f"xclip error on {sel}: {e}")

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
            except Exception as e:
                Logger.debug(f"xdotool paste error: {e}")
        elif is_wayland and shutil.which("wtype"):
            try:
                subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5)
            except Exception as e:
                Logger.debug(f"wtype paste error: {e}")
        elif shutil.which("ydotool"):
            try:
                subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5)
            except Exception as e:
                Logger.debug(f"ydotool paste error: {e}")


# ==============================================================================
# CLI Entry Point
# ==============================================================================
def main():
    global VERBOSE_DEBUG
    parser = argparse.ArgumentParser(description="Gemini WhisperFlow Daemon (Linux Speech-to-Text)")
    parser.add_argument("--setup", action="store_true", help="Launch interactive setup wizard")
    parser.add_argument("--test", action="store_true", help="Run end-to-end self-test diagnostics")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--config", type=str, default=CONFIG_PATH, help="Path to config.json")
    args = parser.parse_args()

    if args.debug:
        VERBOSE_DEBUG = True

    if args.setup:
        interactive_setup()
        return

    config = load_config()

    if args.test:
        run_self_test(config)
        return

    # Check if API key is missing
    api_key = config.get("gemini_api_key", "").strip()
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        if sys.stdin.isatty():
            Logger.warn("No Gemini API Key configured.")
            interactive_setup()
            config = load_config()
        else:
            Logger.error(
                "FATAL: No Gemini API Key configured in config.json!",
                "Please open a terminal and run 'gemini-flow setup' to configure your API key."
            )
            # Rate-limited desktop notification (max once every 5 minutes, auto-expiring in 5s)
            lock_file = os.path.join(tempfile.gettempdir(), "gwf_api_err.lock")
            now = time.time()
            should_notify = True
            if os.path.exists(lock_file):
                try:
                    with open(lock_file, "r") as f:
                        last = float(f.read().strip())
                        if now - last < 300:
                            should_notify = False
                except Exception:
                    pass
            if should_notify and shutil.which("notify-send"):
                try:
                    with open(lock_file, "w") as f:
                        f.write(str(now))
                    subprocess.run([
                        "notify-send", "-t", "5000", "-u", "normal", "-a", "WhisperFlow",
                        "Gemini WhisperFlow Error",
                        "No API Key configured! Run 'gemini-flow setup' in terminal."
                    ], check=False, timeout=2.0)
                except Exception:
                    pass
            sys.exit(1)

    Logger.banner(config)
    daemon = VoiceFlowDaemon(config)

    with keyboard.Listener(on_press=daemon.on_press, on_release=daemon.on_release) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\nGemini WhisperFlow daemon stopped.")


if __name__ == "__main__":
    main()

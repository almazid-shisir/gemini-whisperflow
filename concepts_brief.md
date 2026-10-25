# Gemini WhisperFlow Latency & Hallucination Overhaul

* **Author:** almazid-shisir
* **Date:** 2026-10-26
* **Domain:** Bilingual Bengali-English Voice Dictation on Linux (X11 & Wayland)

---

## Overview

Gemini WhisperFlow is a privacy-first, zero-bloat voice dictation engine for Linux desktop environments (**X11 & Wayland**), explicitly engineered for **bilingual Bengali-English dictation with code-switching and technical vocabulary**.

Users currently experience two critical operational regressions:
1. **Severe Latency:** Voice typing takes 4–6+ seconds between releasing the key and seeing text pasted at the cursor.
2. **Hallucination & Semantic Distortion:** Output frequently paraphrases spoken words, alters natural conversational tone, or hallucinates phrases on audio pauses.

This brief establishes the architecture to achieve **near-instant execution (P95 < 1.2s for typical utterances)** while guaranteeing **100% fidelity to spoken speech without generative hallucinations**.

---

## Analysis & Problem Decomposition

### 1. Root Causes of High Latency (4s–6s Total)
* **Sequential Double-Hop API Overhead:** The current two-stage engine issues two independent HTTPS roundtrips:
  - *Hop 1 (ASR):* Audio payload upload to `models/gemini-3.5-transcribe` (~1.5s–2.0s).
  - *Hop 2 (NLP):* Raw transcript upload to `models/gemini-3.5-flash-lite` for thought restructuring (~1.5s–2.0s).
  - Network handshakes, serialization, and server queuing happen twice.
* **Subprocess & Disk I/O Bottleneck:** Spawning sequential FFmpeg subprocesses (`volumedetect` followed by audio encoding) writes temporary files to disk, consuming 300–500ms of local CPU time before packet transmission begins.

### 2. Root Causes of Hallucination & Semantic Drift
* **Over-Generative LLM Prompting:** Stage 2 instructs the model to *"Transform the messy transcript into a structured message"* and *"eliminate repetitions"*. When an LLM is given creative license to clarify thoughts, it treats voice input as a creative writing prompt—rewriting casual Bengali into unnatural formal phrasing, inventing connector words, and paraphrasing colloquial speech.
* **Limitations of Existing Verbatim Bypass:** While the codebase currently includes a verbatim bypass (`"clean_transcript": false` in `gemini_flow.py`), raw speech-to-text alone is insufficient for daily programming/work: it transcribes English tech terms phonetically into Bengali script (*"ভার্সেল"* instead of `Vercel`, *"সিও"* instead of `CEO`) and lacks sentence punctuation.
* **Acoustic Pre-filter Distortion:** Overly aggressive audio suppression filters (e.g. FFT denoisers) attenuate soft speech by 15–20 dB. When the ASR model receives degraded audio, it is forced to guess phonemes, creating hallucinations.

---

## Goals vs. Non-Goals

### In-Scope Goals:
* **Duration-Bracketed Latency SLAs:**
  - *Short utterances (≤ 5 seconds):* P95 end-to-end latency < 1.2 seconds.
  - *Medium utterances (5–30 seconds):* P95 end-to-end latency < 2.0 seconds.
* **Zero Generative Hallucination:** Dictate exactly what was spoken with zero fabricated sentences, zero unsolicited paraphrasing, and zero tone alteration.
* **In-Memory Audio Processing:** Eliminate intermediate disk writes by piping audio in-memory to reduce local pre-upload latency to < 30ms.
* **Deterministic Tech Term & Punctuation Mapping:** Standardize common developer and business terms (`Vercel`, `GitHub`, `CEO`, `API`, `Linux`) via fast client-side dictionary/regex or a strictly constrained single-pass prompt.
* **Authoritative Silence Gate:** Standardize the default volume threshold to `-45.0 dB` to capture natural quiet speech while rejecting pure room silence.

### Out-of-Scope Non-Goals:
* Conversational chatbot functionality (answering queries, executing tasks).
* Heavy multi-gigabyte local neural network models requiring dedicated GPU VRAM.

---

## Alternatives Considered & Trade-Off Evaluation

| Architecture Option | Latency (P95) | Hallucination Risk | Tech Term Normalization | Maintenance Complexity | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Option 1: Constrained Single-Pass Cloud LLM** (`gemini-3.5-flash-lite`) | **~1.2s** | Low (with strict verbatim system prompt) | High (built-in multilingual understanding) | **Low (single API call, unified code)** | **ADOPTED (Primary)** |
| **Option 2: Pure Cloud ASR (`gemini-3.5-transcribe`) + Client-Side Regex** | ~1.4s | Zero | Medium (requires maintaining local dictionary) | Low | **ADOPTED (Fallback / Verbatim Mode)** |
| **Option 3: Duration-Bifurcated Hybrid Pipeline** (Hypothesis C) | 1.4s – 4.5s | High on long audio | Inconsistent | High (two branching code paths) | **REJECTED (Violates YAGNI & UX Determinism)** |
| **Option 4: Local Speech Engine** (`whisper.cpp` / `sherpa-onnx`) | ~0.8s (GPU) / ~3.0s (CPU) | Low | Low (requires custom fine-tuning for Bengali tech) | High (C++ toolchains, model weights distribution) | **REJECTED (Heavy dependencies for lightweight daemon)** |
| **Option 5: Streaming WebSocket ASR** | ~0.6s | Medium | Medium | Very High (requires persistent bi-directional streaming server) | **REJECTED (Excessive architectural overhead)** |

---

## Risks, Failure Modes & Mitigations

| Risk / Failure Mode | Severity | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Audio Hallucination on Ambient Silence** | High | Generates random text from background noise | Combine `-45.0 dB` local hardware volume gate with an explicit system prompt: *"If audio contains only silence or non-speech background noise, output empty string."* |
| **Loss of Technical Proper Nouns in Bengali** | Medium | English tech words typed in Bengali script (`গিটহাব` instead of `GitHub`) | Maintain a deterministic, client-side regex lookup table for common tech keywords (`Vercel`, `CEO`, `Linux`, `GitHub`) applied instantly after transcription. |
| **Network Timeout or Drop during Dictation** | High | Unresponsive UI or hung daemon | Implement strict 10s request timeout with automatic session recycling and desktop notification alerting user of network drop. |
| **Over-Aggressive Audio Filtering** | Medium | Human voice attenuated, causing ASR failure | Restrict audio conditioning to gentle bandpass (`highpass=80Hz, lowpass=8000Hz`) with a `1.5x` volume boost; strictly eliminate destructive FFT denoisers (`afftdn`). |

---

## Key Decisions & Implementation Staging

1. **Shift to Single-Pass Architecture:**
   - Deprecate the two-hop sequential pipeline (ASR + NLP restructuring).
   - Use a single optimized request directly to `gemini-3.5-flash-lite` with an explicit anti-hallucination, verbatim-preserving system instruction.
2. **In-Memory Pipe Encoding:**
   - Stream audio directly into memory buffer or single-pass FFmpeg pipe without redundant disk roundtrips.
3. **Telemetry Instrumentation:**
   - Retain granular millisecond logging (`t_capture`, `t_preprocess`, `t_api`, `t_paste`) to ensure P95 < 1.2s target is continuously verified.

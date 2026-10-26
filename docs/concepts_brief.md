# Feature Concept: Noise-Resilient Speech Recognition & Anti-Hallucination for Low-SNR Microphones

* **Author:** almazid-shisir & Antigravity
* **Date:** 2026-10-26
* **Status:** Brainstorming (Step 1: Clarification & Problem Drilling)

## Overview

Gemini WhisperFlow currently relies on single-pass multimodal inference with `gemini-3.5-flash-lite`. When audio is captured through low-sensitivity microphones with ambient background noise, muffled frequency response, or low Signal-to-Noise Ratio (SNR), the engine exhibits two failure modes:
1. **Acoustic Mishearing & Phonetic Drift:** Phonetically ambiguous English/Bengali words degrade into semantic hallucinations (for example, "Hugging Face" transcribed as "এখানে যে হাতির ফেস আছে সেটাতে").
2. **False Silence Rejection:** Quiet voice segments fall below the silence detection threshold (-45 dB), causing "No speech detected in audio" drops during short or soft utterances.

The objective of this feature is to introduce an audio conditioning pipeline and acoustic-grounded inference strategy that maintains high transcription accuracy on degraded microphone hardware without reintroducing 4-6 second latency or generative hallucination.

## Problem Analysis

### 1. Root Cause: LLM Phonetic Guessing Under Low SNR
Unlike dedicated acoustic models that output CTC/transducer alignments based strictly on phoneme probabilities, general multimodal LLMs (`gemini-3.5-flash-lite`) use autoregressive token generation. When audio quality degrades:
* Low-amplitude consonants (fricatives, stops like `f`, `s`, `k`, `p`) are masked by microphone hiss.
* The model fills phonetically ambiguous gaps with high-probability linguistic tokens (e.g. "হাতির ফেস").
* Prompting the model to "clean" or "smooth" compounds the issue by giving it license to synthesize missing syllables.

### 2. Audio Pipeline Shortcomings
* **Raw Audio Capture:** `pw-record` captures uncompressed 48kHz mono PCM without software gain or noise profiling.
* **Lack of Pre-Emphasis / Dynamic Range Control:** Distant or low-gain mic input has an uneven dynamic range. Normal speech peaks may barely hit -40 dB while ambient noise hovers around -48 dB.
* **No Domain Vocabulary Biasing:** The model lacks explicit acoustic hints for common technical terms used by the user.

## Hypothesized Solution Vectors

| Vector | Description | Trade-offs |
|---|---|---|
| **A. In-Memory Software Audio Conditioning** | Apply lightweight pre-emphasis (`highpass=80, lowpass=7500, acompressor/speechnorm`) during MP3 compression in RAM to boost vocal clarity before sending to Gemini. | Low latency overhead (~30ms), but may amplify background hiss if gain is too aggressive. |
| **B. Two-Tier Verification / Dedicated ASR Fallback** | Use `gemini-3.5-transcribe` (which tested at 260ms latency on the host) as the primary acoustic anchor, with Flash-Lite reserved strictly for formatting. | Adds a second roundtrip (~260ms), but provides strictly non-hallucinating phoneme grounding. |
| **C. Acoustic Context Biasing in Prompt** | Inject an expanded, prioritized vocabulary and common phonetic mishearing list into the system instruction. | Minimal runtime cost, but relies on model prompt compliance. |
| **D. Automatic Gain Control (AGC) & Adaptive Gating** | Dynamically calibrate the silence floor against ambient room noise rather than a static -45.0 dB cutoff. | Prevents dropped utterances, requires 100ms noise profile measurement. |

## Goals vs. Non-Goals

### In-Scope Goals
* Eliminate phonetic hallucinations on low-cost/noisy microphones (e.g., prevent "Hugging Face" -> "হাতির ফেস").
* Prevent dropped speech on quiet or brief utterances without triggering on room noise.
* Maintain sub-2.0s end-to-end latency.
* Keep 100% of audio processing local or via authorized Gemini API endpoints.

### Out-of-Scope Non-Goals
* Hardware microphone replacement or external physical sound card calibration.
* Heavy offline local AI models (e.g. Whisper-large local weights) that require dedicated GPU hardware.

## Open Clarifying Questions
*(To be addressed in chat drilling)*
1. What specific types of ambient noise are present (e.g., ceiling fan, PC fan hiss, keyboard clicks, street traffic)?
2. Does the issue occur mainly on English technical terms (like "Hugging Face", "GitHub", "API") or also on everyday Bengali words?
3. Between a slight latency increase (+300ms for dedicated acoustic grounding) vs pure single-pass speed, which has higher priority for this environment?

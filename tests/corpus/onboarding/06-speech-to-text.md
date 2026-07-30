# Speech to text

**High level:** speech-to-text (STT) turns the captured audio of the user's question into
text for the brain. Jarvis uses OpenAI's Whisper model, running on the Mac's GPU via
Apple's MLX framework, which makes it fast enough for a responsive conversation.

## The adapter

`MlxWhisperTranscriber` in `voice/mlx_whisper_stt.py` implements the `Transcriber` protocol
(`transcribe(audio) -> str`). It calls `mlx_whisper.transcribe(...)` with the configured
model and language, and returns the stripped text. The real model call is
`# pragma: no cover`; the transcribe function is injectable so the adapter's logic is
tested with a fake.

Configuration comes from the `speech_to_text` block in `config.yaml`
(`SpeechToTextConfig`): the model repo and the language (English).

## Why MLX and "turbo"

This choice was driven by a measured latency problem, and it is worth understanding because
it shaped a core decision.

The first implementation used `faster-whisper`. On Apple Silicon that library runs on the
**CPU** — its backend (CTranslate2) has no Metal/GPU support — so transcribing a ~4 second
question took around **6.5 seconds**, slower than real time. That dominated the delay before
Jarvis could even start thinking.

Switching to **`mlx-whisper`** with the **`large-v3-turbo`** model moved transcription onto
the Apple GPU. The "turbo" model has a much smaller decoder, so it decodes several times
faster with negligible accuracy loss. The same clip now transcribes in well under a second.
Live transcripts confirmed the accuracy held up on real speech.

The lesson baked into the codebase: for local voice, *where* the model runs (GPU vs. CPU)
matters as much as which model it is.

## Its place in the turn

STT is step two of a turn (see [The turn lifecycle](03-turn-lifecycle.md)). The recorder
returns `float32` audio in [-1, 1]; the transcriber returns text; if that text is empty
(the [silence guard](05-listening-and-endpointing.md) returned empty audio), the turn ends
right there without troubling the brain. The measured `transcribe_s` timing is reported in
the per-turn [diagnostics](13-transcript-and-diagnostics.md).

## Where this lives in the code

- Adapter: `MlxWhisperTranscriber` in `voice/mlx_whisper_stt.py`.
- Contract: `Transcriber` in `interfaces.py`.
- Configuration: `SpeechToTextConfig` in `config.py`; `speech_to_text` in `config.yaml`.

---

[← Previous: Listening & endpointing](05-listening-and-endpointing.md) · [Contents](index.md) · [Next: The brain →](07-the-brain.md)

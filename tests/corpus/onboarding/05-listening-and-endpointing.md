# Listening & endpointing

**High level:** once a turn starts, Jarvis records from the microphone until it decides the
user has finished speaking. That decision — called *endpointing* — is what lets a blind
user talk naturally without pressing a key to stop, and it is tuned to be **patient** so he
is never cut off mid-thought.

## The two pieces

**Voice-activity detection (VAD)** answers "is this 80 ms frame speech or silence?"
`SileroVad` in `voice/vad.py` wraps the Silero VAD model that openWakeWord bundles (an ONNX
model, so no PyTorch dependency) and reduces each frame to a `True`/`False` via a
threshold. Its `silero_vad.onnx` is fetched with every other model on first launch by the
startup call to `download_models()` — see
[First run downloads the models](04-wake-word.md).

**The endpointer** answers "given the stream of speech/silence decisions so far, is the
utterance finished?" `Endpointer` in `voice/endpointing.py` is a pure state machine — no
audio, no I/O — which makes it fully unit-testable. `VadRecorder` (also in `voice/vad.py`)
glues them together: it reads mic frames, asks the VAD about each, and feeds the answer to
the endpointer until it says stop.

## What makes the endpointer patient

`Endpointer.update(is_speech)` returns `True` (finish) in exactly three situations:

1. **Trailing silence after speech.** Once he has started talking, it ends only after a
   configurable run of continuous silence (`trailing_silence_seconds`, currently 3.0s).
   That is comfortably longer than a normal mid-sentence pause, so a hesitation ("uh...
   well...") does not end his turn.
2. **Onset timeout (follow-ups only).** If a follow-up window opens and *no* speech ever
   begins within the timeout, it gives up quietly and the window closes. Normal turns pass
   no timeout and wait indefinitely. This timeout is measured in **wall-clock time** (an
   injected `now` clock, defaulting to `time.monotonic`), *not* in frames. Right after a
   long answer the microphone path can deliver a burst of buffered frames all at once; a
   frame counter would race to its limit and slam the window shut the instant Jarvis
   stopped speaking, so the follow-up window is timed by the clock instead — a genuine
   `follow_up_seconds` measured from when listening actually begins.
3. **Hard maximum.** An utterance can never exceed `max_utterance_seconds`, so a stuck
   stream or a false trigger cannot record forever.

`from_seconds` converts the silence and maximum durations into frame counts given the
frame length (80 ms); the onset timeout stays in seconds and is compared against the clock.

## The silence guard — the other half of the runaway fix

A subtle failure mode: if a follow-up window records only silence and that silence is sent
to Whisper, Whisper *hallucinates* — it was trained on subtitles, so near-silence produces
phantom phrases like "Good night." or "Thank you." The brain would then answer the phantom,
which once caused an endless self-conversation.

The fix lives in two places:

- `Endpointer` counts speech frames and exposes `heard_speech`, which is `True` only once
  enough real speech (past `min_speech_seconds`, so a cough does not count) has been
  captured.
- `VadRecorder.record` returns an **empty array** when `heard_speech` is `False`. Empty
  audio transcribes to an empty string, so the turn cleanly reports "nothing heard" and the
  follow-up window closes. Combined with the `max_follow_ups` cap from
  [The turn lifecycle](03-turn-lifecycle.md), a runaway is impossible.

## Format details

The recorder captures `int16` frames (what the VAD wants) and, when it does return audio,
converts to `float32` in the range [-1, 1], which is what Whisper expects. The mic runs at
16 kHz mono.

## Tuning

`trailing_silence_seconds` is the main comfort dial and is explicitly meant to be tuned to
the individual user — the father is long-winded, so it may go higher for him. All of these
live in the `listening` block of `config.yaml` (`ListeningConfig` in `config.py`). See
[Configuration](14-configuration.md).

## Where this lives in the code

- VAD + recorder: `SileroVad`, `VadRecorder` in `voice/vad.py`.
- Endpointing state machine: `Endpointer`, `Endpointer.from_seconds`, `heard_speech`,
  `update` in `voice/endpointing.py`.
- Tunables: `ListeningConfig` in `config.py`; `listening` in `config.yaml`.

---

[← Previous: The wake word](04-wake-word.md) · [Contents](index.md) · [Next: Speech to text →](06-speech-to-text.md)

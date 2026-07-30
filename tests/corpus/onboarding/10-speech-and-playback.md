# Text to speech & playback

**High level:** text-to-speech (TTS) turns each answer sentence into audio and plays it
through the speakers. Jarvis uses [Piper](https://github.com/rhasspy/piper), a fast, natural
local voice, and plays everything through a single persistent audio stream — a detail that
turned out to matter a lot for sound quality.

## Synthesis

`load_piper_synthesize` in `voice/piper_voice.py` loads a Piper voice model (an `.onnx` file
under `models/piper/`) and returns a `synthesize(text) -> AudioClip` function. It reads the
live speaking rate on every call — via an injected `get_rate` — so "slower"/"faster"
controls take effect immediately by adjusting Piper's length scale. An `AudioClip` is just
raw samples plus their sample rate (Piper's is 22050 Hz).

The voice model is chosen by name in the `text_to_speech` block of `config.yaml`
(`en_US-ryan-high`, a natural US male voice). Swapping voices is just a one-line config
change — see [Configuration](14-configuration.md).

### Auto-downloading the voice

The `.onnx`/`.onnx.json` files live under a gitignored `models/piper/`, so a fresh clone
wouldn't have them. Rather than a manual placement step, `ensure_piper_voice` in
`voice/piper_download.py` **downloads the configured voice on first use** — mirroring how
Whisper and openWakeWord fetch their models. `piper_voice_paths` derives the voice's location
in the official [`rhasspy/piper-voices`](https://huggingface.co/rhasspy/piper-voices) repo
from its key (`en_US-ryan-high` → `en/en_US/ryan/high/en_US-ryan-high.onnx`), and both files
are fetched via `huggingface_hub` and copied into `models/piper/`. It is a **no-op once the
voice is present**, so only a missing (or newly-configured) voice triggers a download. The
path derivation and copy logic are unit-tested with an injected fetch; only the real network
call is untested. `main()` in `voice/voice_cli.py` calls it to resolve the voice path before
building the speaker.

## The speaker

`PiperSpeaker` in `voice/piper_tts.py` implements the `Speaker` protocol (`speak(text)`). It
composes two injected steps — `synthesize` and `play` — so its logic is fully testable with
fakes. On each call it synthesizes the text, applies the live **volume** from
`RuntimeSettings` (via `apply_gain`), and plays it. Blank text is never spoken.

## Playback, and the popping story

`StreamingPlayer` in `voice/audio.py` plays clips through **one persistent output stream**.
Two things about it were established by A/B listening tests, not theory, and both fixed
audible popping:

- **One stream, kept open.** Opening a fresh stream per sentence makes the audio device
  start and stop between sentences, and each transition is an audible click. The stream is
  opened once and reused across the whole reply.
- **The device's native sample rate.** Piper outputs 22050 Hz, but the output device runs
  at its own rate (44100 Hz on the MacBook). Handing the device a mismatched rate makes
  CoreAudio convert continuously, which glitches badly once the microphone is also open (as
  it is during barge-in). The fix: convert the audio **once**, up front, with `resample`,
  and open the stream at the device's native rate.

To keep one stream open across the gaps while the next sentence is still being synthesized,
`PlaybackBuffer` feeds the stream's callback. Its key trick: `take` always returns a *full*
block, padding with silence if the queue is momentarily empty — because an output stream
that runs dry underruns, and an underrun is itself a click.

## The pure audio helpers

`audio.py` also holds small, fully-tested numpy functions:

- `resample` — linear interpolation between sample rates (22050 → 44100 is an exact 2x).
- `apply_gain` — scale samples by a volume factor, clipping to avoid overflow (used for the
  "louder"/"quieter" controls).
- `apply_fade` — a short linear fade-in/out at clip edges to remove edge clicks.

## Interrupting playback

`StreamingPlayer` is constructed with a `should_stop` callback (wired to barge-in). While a
clip plays, it checks that callback; when it fires, `PlaybackBuffer.stop` drops the queued
audio but keeps a short faded tail so the cut-off itself does not click. See
[Barge-in](11-barge-in.md).

## Where this lives in the code

- Synthesis: `load_piper_synthesize` in `voice/piper_voice.py`.
- Voice auto-download: `ensure_piper_voice`, `piper_voice_paths` in `voice/piper_download.py`.
- Speaker: `PiperSpeaker` in `voice/piper_tts.py`.
- Playback + audio math: `StreamingPlayer`, `PlaybackBuffer`, `resample`, `apply_gain`,
  `apply_fade` in `voice/audio.py`.
- Voice choice: `TextToSpeechConfig` in `config.py`; `text_to_speech` in `config.yaml`.

---

[← Previous: The filler](09-the-filler.md) · [Contents](index.md) · [Next: Barge-in →](11-barge-in.md)

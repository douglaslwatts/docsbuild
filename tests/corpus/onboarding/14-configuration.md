# Configuration

**High level:** every tunable value lives in one place — `config.yaml` at the project root —
loaded into frozen dataclasses in `config.py`. This is where you change the voice, the model,
how patient the listening is, and the control bounds, without touching code.

> Looking for step-by-step recipes ("how do I change the voice / the speed / the wait
> time")? See the dedicated **[Configuration guide](../../CONFIGURATION.md)**. This page
> explains how configuration works *under the hood*.

## How it loads

`load_config(path)` in `config.py` reads the YAML and builds a `Config` via
`Config.from_dict`, which fills each section, falling back to the dataclass defaults for
anything omitted. Every section is a frozen dataclass, so configuration cannot be mutated at
runtime — the live, changeable state is `RuntimeSettings` instead (see
[Architecture overview](02-architecture.md)).

Because defaults live in the dataclasses *and* in `config.yaml`, the two are kept in step; a
missing key in the YAML simply uses the code default.

## The sections

- **`wake_word`** (`WakeWordConfig`) — the spoken `phrase`, the openWakeWord `model`
  (`hey_jarvis`), an optional custom `model_path`, the detection `threshold`, and whether
  wake-listening is on at start. The `phrase` must match the `model`. See
  [The wake word](04-wake-word.md).
- **`listening`** (`ListeningConfig`) — `trailing_silence_seconds` (patience, currently 3.0),
  `max_utterance_seconds`, `follow_up_seconds` (the no-wake-word window), `min_speech_seconds`
  (the silence guard), and `max_follow_ups` (the runaway cap). See
  [Listening & endpointing](05-listening-and-endpointing.md).
- **`speech_to_text`** (`SpeechToTextConfig`) — the Whisper `model` and `language`. See
  [Speech to text](06-speech-to-text.md).
- **`text_to_speech`** (`TextToSpeechConfig`) — the Piper `voice` name and `speaking_rate`.
- **`brain`** (`BrainConfig`) — the answer `model`, `temperature`, the `think` flag, and the
  small `research_model` used for routing/filler. See [The brain](07-the-brain.md).
- **`answers`** (`AnswersConfig`) — `relevant_filler` on/off and the `acknowledgments`
  fallback phrases. See [The filler](09-the-filler.md).
- **`controls`** (`ControlsConfig`) — the step size and min/max bounds for the
  louder/quieter and slower/faster commands. See [Voice controls](12-voice-controls.md).
- **`search`** (`SearchConfig`) — the search `backend` and `max_results`.

## Changing the voice (a worked example)

The Piper voice is just a model file under `models/piper/` named by the config value.
To switch voices:

```
uv run python -m piper.download_voices en_US-ryan-high --download-dir models/piper
```

Then set `text_to_speech.voice: "en_US-ryan-high"` in `config.yaml` and restart. The name in
the config must match the `.onnx` filename. Male US options include `en_US-ryan-high` (the
default) and `en_US-joe-medium`; `en_GB-alan-medium` is a British voice fitting the "Jarvis"
theme.

## Where this lives in the code

- Loader and every section dataclass: `load_config`, `Config`, and the `*Config` classes in
  `config.py`.
- The values themselves: `config.yaml` at the project root.
- Live (non-config) session state: `RuntimeSettings` in `voice/runtime.py`.

---

[← Previous: Transcript & diagnostics](13-transcript-and-diagnostics.md) · [Contents](index.md) · [Next: Testing & TDD →](15-testing-and-tdd.md)

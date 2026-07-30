# Architecture overview

**High level:** Jarvis is a small Python state machine that drives a chain of local
components — wake word, voice detection, speech-to-text, a language-model brain, and
speech synthesis — with web search as the only thing that ever reaches the network.

This page gives you the map. Every later page zooms into one box on it.

## The pipeline

```
mic --> wake word --+
Enter --------------+--> VAD / endpointing --> speech-to-text --> brain --> text-to-speech --> speaker
 "sleep / wake" <---+        (patient)          (mlx-whisper)      |  |         (Piper)
                                                                   |  +--> web search / weather  (only egress)
                                          barge-in (wake word) <---+       + conversation memory
```

A turn flows left to right: something triggers it, the mic captures one utterance, Whisper
transcribes it, the brain researches and answers, and Piper speaks the reply sentence by
sentence. While the reply plays, a background listener watches for the wake word so the
user can [barge in](11-barge-in.md). The [turn lifecycle](03-turn-lifecycle.md) page walks
this end to end.

## The design rule that shapes every module

**Deterministic logic sits behind small `Protocol` interfaces; the messy outside world is
wrapped in thin adapters that are faked in tests.** This is the single most important thing
to understand about the codebase.

- The **interfaces** are defined in `interfaces.py` — `WakeWord`, `AudioRecorder`,
  `Transcriber`, `Responder`, `Researcher`, `Filler`, `Speaker`, `BargeIn`, `Controls`,
  and the data types they exchange (`ChatMessage`, `TurnResult`, `AudioClip`, ...).
- The **adapters** are the classes that talk to hardware or the network: `OpenWakeWordListener`,
  `VadRecorder`, `MlxWhisperTranscriber`, `OllamaClient`, `DuckDuckGoBackend`,
  `PiperSpeaker` / `StreamingPlayer`. Their hardware/network calls are marked
  `# pragma: no cover` and verified by ear; everything else is unit-tested.
- The **deterministic core** — the orchestration and rules — is tested to 100% against
  fakes: `VoiceSession`, `run_hands_free_loop`, `Brain`, `WebResearcher`, `Endpointer`,
  `Controller`, `parse_command`, and the audio math in `audio.py`.

Because the core only ever sees interfaces, a test can hand it a fake recorder, fake
transcriber, and fake brain and assert on exactly what happens — no microphone, no model,
no network. See [Testing & TDD](15-testing-and-tdd.md).

## Repository layout

```
src/voice_companion/
  interfaces.py      # Protocols + shared data types (the contracts)
  config.py          # frozen config dataclasses, loaded from config.yaml
  cli.py             # text REPL + build_brain() wiring helper
  agent/
    brain.py         # Brain: the remembered, grounded conversation loop
    memory.py        # ConversationMemory: bounded turn history
    research.py      # WebResearcher: deterministic retrieval routing
    response_shaping.py  # strip markdown, split into spoken sentences
    controls.py      # parse spoken commands; strip the wake phrase
    tools/
      web_search.py  # WebSearchTool: format search results for the model
      weather.py     # WeatherTool: wttr.in current + 3-day forecast
  llm/ollama_client.py   # OllamaClient: the LLMClient adapter
  search/duckduckgo.py   # DuckDuckGoBackend: the SearchBackend adapter
  voice/
    voice_cli.py     # run_hands_free_loop + main() wiring the whole pipeline
    session.py       # VoiceSession: one spoken turn end to end
    wake_word.py     # OpenWakeWordListener
    vad.py           # SileroVad + VadRecorder
    endpointing.py   # Endpointer: when an utterance is finished
    mlx_whisper_stt.py   # MlxWhisperTranscriber
    piper_voice.py / piper_tts.py   # synthesis + the Speaker
    audio.py         # StreamingPlayer, PlaybackBuffer, resample, gain, fade
    barge_in.py      # WakeWordBargeIn
    controller.py    # Controller: apply a parsed command
    runtime.py       # RuntimeSettings: live, voice-adjustable state
    echo.py          # EchoingSpeaker: print everything spoken
```

Tests mirror this under `tests/unit/`.

## Two kinds of state

- **`Config`** (`config.py`) is frozen startup configuration read from `config.yaml` — the
  wake phrase, model names, timeouts, bounds. It never changes during a session.
- **`RuntimeSettings`** (`runtime.py`) is the live, mutable state the user steers by voice:
  speaking rate, volume, whether wake-listening is on, and the last exchange (so "repeat"
  and "tell me more" have something to act on). It is shared by reference across the
  speaker, controller, and session. See [Configuration](14-configuration.md) and
  [Voice controls](12-voice-controls.md).

## Where this lives in the code

- Contracts: `interfaces.py`.
- The full wiring of every real component: `main` in `voice/voice_cli.py`.
- The brain's wiring (models + tools): `build_brain` in `cli.py`.

---

[← Previous: Introduction](01-introduction.md) · [Contents](index.md) · [Next: The turn lifecycle →](03-turn-lifecycle.md)

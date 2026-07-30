# The wake word

**High level:** the wake word is how Jarvis is summoned hands-free. Saying "Hey Jarvis"
into the room makes it start a turn. It is detected fully on-device by
[openWakeWord](https://github.com/dscripka/openWakeWord), a small, local, open-source model.

## How it works

`OpenWakeWordListener` in `voice/wake_word.py` is the adapter. Its `wait_for_wake` method
opens a 16 kHz microphone stream and feeds 80 ms frames into the model, returning as soon
as the model's confidence for the phrase crosses a threshold. It also takes a `should_stop`
callback so the caller can cancel the wait (used when a keypress wins the race, or when
barge-in tears down).

The model, threshold, and an optional custom-model path all come from configuration
(`wake_word` in `config.yaml`, mapped to `WakeWordConfig` in `config.py`). The real model
load and the microphone loop are `# pragma: no cover`; the class accepts an injected model
so its construction is still testable.

## First run downloads the models

The adapter only *loads* the ONNX models; it does not fetch them. On startup, before any
model-backed component is built, `main` in `voice/voice_cli.py` calls
`openwakeword.utils.download_models()` once. That single call downloads **all** of
openWakeWord's ONNX models — the pretrained wake words, the shared feature models, and the
Silero VAD (see [Listening & endpointing](05-listening-and-endpointing.md)) — so a fresh
clone works on first launch. It is idempotent: models already on disk are skipped, so there
is no cost on later runs.

## Why "Hey Jarvis" specifically

openWakeWord ships a handful of pretrained, speaker-independent phrase models — including
`hey_jarvis`. The companion is named **Jarvis** precisely so that its name *is* a built-in
wake word: no custom model needs to be trained, and the name it calls itself matches the
words you say to wake it. The alternative — a custom "Hey <name>" model — is a real training
task (synthetic speech generation plus training) and was deliberately avoided by this
naming choice.

## Two important properties

- **It is phrase-based, not speaker-based.** "Hey Jarvis" wakes it for *anyone*, by design.
  Recognizing *who* spoke is a separate concern (speaker identification), not built yet, and
  reserved for personalization only — never for authorizing anything. See
  [Roadmap & what's next](17-roadmap.md).
- **The same listener does double duty.** The one `OpenWakeWordListener` instance is used
  both to trigger a turn when idle *and*, wrapped in `WakeWordBargeIn`, to detect an
  interruption while Jarvis is speaking. Using the wake word (rather than any speech) for
  interruption is what makes barge-in robust to Jarvis hearing its own voice through the
  speakers — see [Barge-in](11-barge-in.md).

## The wake phrase can leak — and is stripped

When the user barge-ins by saying "Hey Jarvis, actually what about Mars?", the wake phrase
lands at the front of the next transcript. Answering that literally would make Jarvis reply
to its own name. So `strip_wake_phrase` (in `agent/controls.py`) removes a leading wake
phrase before the text reaches the brain, preserving the casing and punctuation of the real
question that follows. If only the wake phrase was said, Jarvis answers "Yes?" and listens
again. This is covered more in [Voice controls](12-voice-controls.md).

## Toggling it off

The user can say "go to sleep" to stop wake-word listening (so ambient talk never triggers
it) and "wake up" or press Enter to resume. That flag lives in `RuntimeSettings.wake_listening`
and is honored at the top of `run_hands_free_loop`.

## Where this lives in the code

- Adapter: `OpenWakeWordListener` in `voice/wake_word.py`.
- Configuration: `WakeWordConfig` in `config.py`; the `wake_word` block in `config.yaml`.
- Phrase stripping: `strip_wake_phrase` in `agent/controls.py`.
- Wiring: the `listener` built in `main` (`voice/voice_cli.py`).

---

[← Previous: The turn lifecycle](03-turn-lifecycle.md) · [Contents](index.md) · [Next: Listening & endpointing →](05-listening-and-endpointing.md)

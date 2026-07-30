# Barge-in

**High level:** barge-in lets the user interrupt Jarvis while it is speaking, simply by
saying the wake word. A long answer is never a trap — he can cut in at any moment and take
over. This directly serves the "patient, never a dead end" constraint from
[Introduction](01-introduction.md).

## How it works

`WakeWordBargeIn` in `voice/barge_in.py` implements the `BargeIn` protocol (`start`,
`triggered`, `stop`). When an answer begins, `start` launches a background thread that
listens for the wake phrase using the same `OpenWakeWordListener` described in
[The wake word](04-wake-word.md). If it fires, an internal event is set; `triggered()`
reports that, and `stop` tears the thread down and resets the event so the next reply is not
pre-interrupted.

Two collaborators act on that signal:

- `VoiceSession._speak_answer` checks `barge_in.triggered()` after each spoken sentence and
  stops streaming the rest of the reply if it fired.
- `StreamingPlayer` (see [Text to speech & playback](10-speech-and-playback.md)) is wired
  with `barge_in.triggered` as its `should_stop` callback, so playback of the current
  sentence is cut off mid-clip — with a short faded tail so the interruption does not click.

After playback stops, the follow-up window opens and captures what the user says next.

## Why the wake word, not "any speech"

The obvious design — interrupt on *any* detected speech — has a hard problem: Jarvis hears
its own voice through the speakers, so raw voice-activity detection would constantly
false-trigger on itself. Solving that properly needs **acoustic echo cancellation** (AEC),
subtracting the known output signal from the microphone input.

Using the *wake word* sidesteps this entirely: the openWakeWord model does not fire on
Jarvis's own speech, so no echo cancellation is required. The cost is that the user says
"Hey Jarvis" to interrupt rather than just talking over it. Making "any speech interrupts"
work is a deliberate later refinement that depends on adding AEC — noted in
[Roadmap & what's next](17-roadmap.md).

## Testability

The thread and microphone are hardware (`# pragma: no cover`), but the trigger is a plain
`threading.Event`, so the barge-in *policy* — stop after the current sentence, reset between
replies — is unit-tested with a fake interruptible speaker and a fake monitor, no audio
involved.

## Where this lives in the code

- The monitor: `WakeWordBargeIn` in `voice/barge_in.py`.
- Stopping the stream of sentences: `_speak_answer` in `voice/session.py`.
- Cutting off the current clip: `StreamingPlayer.play` / `PlaybackBuffer.stop` in
  `voice/audio.py`.
- Shared listener wiring: `main` in `voice/voice_cli.py`.

---

[← Previous: Text to speech & playback](10-speech-and-playback.md) · [Contents](index.md) · [Next: Voice controls →](12-voice-controls.md)

# Voice controls

**High level:** voice controls are spoken commands that let the user run the machine without
a screen — "louder", "slower", "say that again", "tell me more", "stop", and "go to
sleep" / "wake up". They are recognized *before* the brain is consulted, so a command
adjusts the system instead of being answered as a question.

## Two halves: parsing and applying

**Parsing** is pure and lives in `agent/controls.py`. `parse_command(text)` normalizes the
transcript and looks it up against per-command synonym tables, returning a `Command` enum
value or `None`. The `Command` enum covers `LOUDER`, `QUIETER`, `SLOWER`, `FASTER`,
`REPEAT`, `MORE_DETAIL`, `STOP`, `STOP_LISTENING`, `START_LISTENING`, `END_CONVERSATION`.

The crucial rule: matching is on the **whole normalized utterance**, never a substring. So
"what should I do to stop a leak?" is a question (returns `None`), while a bare "stop" is
the command. This keeps real questions from being swallowed. `normalize` lowercases,
collapses punctuation, and strips edge politeness/address words ("jarvis, repeat that
please" → "repeat that").

**Applying** lives in `Controller` (`voice/controller.py`), which implements the `Controls`
protocol. `try_handle(text)` parses the command and, if there is one, runs it via a handler
table and returns a short spoken confirmation — so a blind user always *hears* that the
command was understood.

## What each command does

- **Louder / quieter / faster / slower** adjust `volume` or `speaking_rate` in
  `RuntimeSettings` by a configured step, clamped to safe bounds, and confirm ("Okay, a
  little louder." / "That's as loud as I can go."). The speaker reads these live values on
  the next utterance, so the change is immediate.
- **Repeat** re-speaks `last_answer`.
- **More detail** re-asks the brain with the last question plus a "go deeper" instruction,
  and speaks the fuller reply.
- **Stop** halts current playback (via the injected `stop_playback`).
- **Go to sleep / wake up** flip `RuntimeSettings.wake_listening`, which the main loop
  honors; the sleep confirmation tells the user the exact phrase to wake it.
- **"That's all" / "that will be all" / "goodbye"** (`END_CONVERSATION`) ends the open
  follow-up window and returns to waiting for the wake word — but **stays awake** (it sets a
  one-shot `RuntimeSettings.end_requested` the loop consumes, and leaves `wake_listening`
  on). This is the difference from *go to sleep*: after "that's all", Jarvis still answers to
  "Hey Jarvis"; it just stops the open listening instead of waiting out the follow-up window.

`last_question` and `last_answer` are recorded by `Controller.remember`, which the session
calls after every answered turn — that is what gives "repeat" and "more detail" something to
act on.

## Wake-phrase stripping

Also in `agent/controls.py` is `strip_wake_phrase`, used by the session (not the
controller). It removes a leading "Hey Jarvis" that barge-in left on the transcript,
preserving the real question's casing and punctuation because that text goes to the model.
Unlike `normalize` — which lowercases for matching — this keeps the remainder intact. If
only the wake phrase was said, it returns empty and the session answers "Yes?".

## Where this lives in the code

- Parsing: `Command`, `parse_command`, `normalize`, `strip_wake_phrase` in
  `agent/controls.py`.
- Applying: `Controller`, its `_HANDLERS` table, and `try_handle` / `remember` in
  `voice/controller.py`.
- Live state it mutates: `RuntimeSettings` in `voice/runtime.py`.
- Bounds and steps: `ControlsConfig` in `config.py`; `controls` in `config.yaml`.

---

[← Previous: Barge-in](11-barge-in.md) · [Contents](index.md) · [Next: Transcript & diagnostics →](13-transcript-and-diagnostics.md)

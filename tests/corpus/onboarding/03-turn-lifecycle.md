# The turn lifecycle

**High level:** one "turn" is a single round of *trigger → listen → transcribe → answer →
speak*. This page traces exactly what happens, in order, and where each step is
implemented — it is the spine that ties every other page together.

## The outer loop

The hands-free loop is `run_hands_free_loop` in `voice/voice_cli.py`. Stripped to its
shape:

```
print the greeting
loop forever:
    if wake-listening is on: wait for "Hey Jarvis" OR Enter
    else:                    wait for Enter only
    turn = session.handle_turn()
    report diagnostics
    if nothing was heard: continue
    for up to max_follow_ups:      # the follow-up window
        if the last turn had no answer: stop
        turn = session.handle_turn(follow_up=True)
        if nothing was heard: stop
```

Two things to notice:

- **The follow-up window.** After Jarvis answers, the loop keeps listening *without*
  requiring the wake word again, so a natural back-and-forth ("...and how far is Mars?")
  just works. The window closes the moment a turn comes back empty (nobody spoke).
- **The hard cap.** `max_follow_ups` bounds that window. This exists because a misheard or
  hallucinated transcript once kept Jarvis answering itself indefinitely; the cap makes a
  runaway structurally impossible. See [Listening & endpointing](05-listening-and-endpointing.md)
  for the other half of that fix (never handing silence to Whisper).

The trigger itself is `wait_for_trigger` inside `main` — it races the wake word against a
keypress so both always work, and when Jarvis is "asleep" only the key wakes it.

## One turn, step by step

A single turn is `VoiceSession.handle_turn` in `voice/session.py`:

1. **Record.** Call `recorder.record(onset_timeout_s=...)`. On a normal turn the timeout is
   `None` (wait patiently and indefinitely for speech to begin). On a follow-up turn it is
   `follow_up_seconds`, so an empty window closes instead of hanging.
2. **Transcribe.** `transcriber.transcribe(audio)` returns the text. If it is empty
   (silence), the turn ends immediately and reports nothing heard.
3. **Strip the wake phrase.** `strip_wake_phrase` removes a leading "Hey Jarvis" that
   barge-in may have left on the front of the transcript. If nothing remains, Jarvis says
   "Yes?" and waits — an audible acknowledgment for a user who cannot see a prompt.
4. **Report what was heard.** The `on_heard` callback prints `You: ...` *now*, before
   anything is spoken, so the printed transcript reads in the true order.
5. **Try controls first.** `controller.try_handle(text)` checks whether the utterance is a
   system command (louder, repeat, sleep, ...). If so it runs it and the brain is never
   consulted. See [Voice controls](12-voice-controls.md).
6. **Otherwise, answer.** `_speak_answer` first asks the brain to `plan` the turn (decide
   what to look up — a fast routing call, no network), starts the
   [filler](09-the-filler.md) — driven by that decision — in a background thread, then
   streams the brain's reply, which runs the lookup and then generates. Each sentence is
   spoken as it is ready, stopping early if [barge-in](11-barge-in.md) fires.
7. **Remember.** The exchange is recorded so "repeat" and "tell me more" can act on it.

## What a turn returns

`handle_turn` returns a `TurnResult` (defined in `interfaces.py`), which carries both what
happened and how long each stage took: `heard`, `answer`, `command`, `route` (what was
looked up, for the diagnostics line), and the timings `record_s`, `transcribe_s`,
`first_word_s`, `answer_s`. The loop uses `heard` vs. `answer`
to distinguish silence (nothing heard) from a quiet command like "stop" (heard, but no
spoken answer) — a distinction that matters for whether to open a follow-up window. The
timings feed the diagnostics line described in
[Transcript & diagnostics](13-transcript-and-diagnostics.md).

## Why the filler runs concurrently

Looking something up and generating an answer takes a few seconds. Rather than leave dead
air, the filler ("Let me check the weather in Athens for you") is spoken on a background
thread while the brain works. This is why `plan` only *decides* and leaves the lookup to
`answer_stream`: the decision is available in one fast routing call, so the filler starts
speaking **before** the web request rather than after it.

It never delays the answer either. If the first real sentence is ready while the filler is
still being written, the filler is dropped unspoken; only a filler that has already started
speaking is waited out, so the two never talk over each other.

## Where this lives in the code

- Outer loop and real wiring: `run_hands_free_loop` and `main` in `voice/voice_cli.py`.
- One turn: `VoiceSession.handle_turn` and `_speak_answer` in `voice/session.py`.
- The turn's return type: `TurnResult` in `interfaces.py`.

---

[← Previous: Architecture overview](02-architecture.md) · [Contents](index.md) · [Next: The wake word →](04-wake-word.md)

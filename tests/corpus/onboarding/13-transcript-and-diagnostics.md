# Transcript & diagnostics

**High level:** while Jarvis runs, the terminal prints the entire conversation as it happens
— what the user said and every line Jarvis spoke — plus a per-turn diagnostics line with
timings. This exists so whole conversations can be captured and shared to debug behavior,
which is otherwise invisible in a voice-only system.

## Printing what the user said

`VoiceSession` takes an `on_heard` callback and calls it the *moment* the transcript exists
— after stripping the wake phrase, before anything is spoken. In `main` (`voice/voice_cli.py`)
that callback prints `You: <text>`. Printing it here, rather than after the turn, is
deliberate: an answer is spoken *while* it streams, so printing the user's line at the end
made every exchange read backwards.

## Printing what Jarvis said

`EchoingSpeaker` in `voice/echo.py` wraps the single shared `Speaker` and prints each
utterance (`Jarvis: <text>`) right before speaking it. Because *every* spoken line funnels
through `Speaker.speak` — answer sentences, the filler, control confirmations, the
bare-wake "Yes?" — wrapping that one object captures the whole conversation, and **no code
path can escape it**. A future feature that speaks is logged automatically instead of being
silently missing.

Sentences are printed individually rather than as one block on purpose: that shows the
streaming order, where [barge-in](11-barge-in.md) truncated a reply, and how the filler
interleaved with the answer.

## The diagnostics line

After each turn, `_report` in `voice/voice_cli.py` prints a compact timing line from the
`TurnResult`, for example:

```
  · rec 3.1s · stt 0.5s · thinking 2.4s · speaking 12.0s · control no · research WEATHER Athens
```

- **rec** — how long recording took (includes the patient trailing silence).
- **stt** — speech-to-text time.
- **thinking** — the wait before the *first* spoken word: the latency the user actually
  feels.
- **speaking** — total time to speak the whole reply (much longer, since it includes reading
  it aloud).
- **control** — whether the turn was a system command.
- **research** — what the researcher looked up (`WEATHER <place>`, `SEARCH "<query>"`, or
  `NONE`), so a shared transcript shows *why* an answer was fresh or stale. Commands look
  nothing up, so they omit it.

Splitting "thinking" from "speaking" matters because a single combined number was
misleading — most of it was just the time to read a long answer aloud, not latency.

If nothing was heard, `_report` prints "(I didn't catch anything — try again.)". A quiet
command like "stop" is *not* mistaken for silence, because `TurnResult` distinguishes
`heard` (something was said) from `answer` (something was spoken back).

## Where this lives in the code

- User transcript: the `on_heard` callback in `VoiceSession` (`voice/session.py`), wired in
  `main` (`voice/voice_cli.py`).
- Jarvis transcript: `EchoingSpeaker` in `voice/echo.py`.
- Diagnostics + timings: `_report` in `voice/voice_cli.py`; `TurnResult` in `interfaces.py`.

---

[← Previous: Voice controls](12-voice-controls.md) · [Contents](index.md) · [Next: Configuration →](14-configuration.md)

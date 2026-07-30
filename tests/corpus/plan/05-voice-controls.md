# Voice controls & flow

**High level:** whole-utterance, deterministic command parsing (`agent/controls.py` →
`parse_command`), never handed to the model. A real question that merely *contains* a command
word ("what should I do to be quiet in a library?") is never mistaken for a control.

## The commands

- [DONE] **louder / quieter, slower / faster, repeat, more detail, stop, be quiet, start /
  stop listening**, and the leave-taking **"that's all."**

## Conversation flow

- [DONE] **Follow-ups need no wake word** — after an answer, an ~8s window listens for "yes" /
  "tell me more" / a fresh question. The window is timed by the **wall clock** from when
  listening truly begins, so a long answer's buffered audio can't collapse it the instant
  Jarvis stops speaking (`a5f432c`). Silence closes it; a hard cap stops a misheard phantom
  from sustaining a self-conversation.
- [DONE] **Spoken state transitions** — when the window closes, Jarvis *says* "I'm here whenever
  you need me. Just say Hey Jarvis," so a blind user hears that it is waiting again and how to
  resume (`1547295`).
- [DONE] **Voice-resumable sleep** — the wake word stays live even while "asleep," so "Say Hey
  Jarvis whenever you want me back" is literally true and a keyboard-free user is never
  stranded.
- [DONE] **"That's all" / "stop" / "no"** (`END_CONVERSATION`) end the open window immediately
  and return to the wake word **while staying armed** — distinct from "go to sleep"
  (`STOP_LISTENING`), which quiets Jarvis but (now) still wakes to the wake word (`a258ccf`).
  Implemented as a one-shot `RuntimeSettings.end_requested` consumed by the loop.

## The mid-sentence interrupt

- [DROPPED] **"Stop talking" / "be quiet"** are *recognized* as commands (`6d371fb`), but making
  them actually halt playback didn't work: while Jarvis speaks, the only listener is the
  wake-word barge-in monitor (deliberately wake-word-only, so it doesn't fire on Jarvis's own
  voice — there is no echo cancellation). So on the current branch the way to cut Jarvis off is
  **"Hey Jarvis."** The activation attempt is parked on the unmerged
  `make_stop_phrases_active` branch. True phrase-based interrupt needs a dedicated "stop" model
  or acoustic echo cancellation — deferred. See [Constraints & caveats](07-constraints.md).

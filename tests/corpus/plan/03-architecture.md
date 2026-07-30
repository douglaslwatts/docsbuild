# Architecture

**High level:** a local voice pipeline orchestrated by a small Python state machine.
Everything runs on-device except the search tool's outbound queries.

```
mic ─► wake word ─┐
Enter ────────────┼─► VAD/endpointing ─► STT ─► LLM agent ─► TTS ─► speaker
                  │      (patient)     (Whisper)  │  │        (Piper)
"start/stop       │                               │  └─► web search (only egress)
 listening" ◄─────┘                    barge-in ◄─┘      + memory + notes/lists
```

## The components

- **Wake word** — `openWakeWord` (local), built-in `hey_jarvis`. Toggle-able by voice + Enter.
- **Endpointing / VAD** — Silero VAD with a generous, configurable trailing-silence timeout.
- **STT** — `mlx-whisper` (`large-v3-turbo`) on Metal; replaced CPU-only faster-whisper, cutting
  ~6.5s/turn to under ~1s.
- **Brain** — Ollama running a capable answer model (`think=false`); a small `llama3.2` handles
  routing, filler, and summarization.
- **Web search** — a simple API now → self-hosted **SearXNG** on the appliance later (M4).
- **TTS** — `Piper` (`en_US-ryan-high`), markdown stripped before speaking, rate/volume
  live-adjustable.

Deterministic logic sits behind `Protocol` interfaces (unit-tested directly); thin adapters
wrap the external services (Ollama, Whisper, Piper, network, Keychain) and are faked in tests.
See [Approach & verification](13-approach.md).

## Freshness is deterministic, not model-judged

Leaving accuracy to the model's own judgment (know-it's-stale, then decide-to-search) was
unreliable. The fix makes freshness **deterministic**, so a *fast* (`think=false`) model can
still be *accurate*:

1. **Ground in the present** — inject the current date/time into the system prompt each turn.
2. **Deterministic retrieval (RAG), not model tool-calling** — `WebResearcher` routes every
   turn in code to **WEATHER / SEARCH / NONE**; the model only forms a query or summarizes
   results. Weather is **force-routed** to the `wttr.in` tool (with a real hour-by-hour
   summary), never a web-search snippet.

**Route-driven filler:** the researcher's decision is the single source of truth; the filler
merely narrates it — silent on `NONE`, a fixed template on `WEATHER`, a grounded line on
`SEARCH`. It can no longer invent an off-topic subject or fire on a decline.

## The dispatch seam

A turn's transcript is offered to deterministic handlers **before** the brain, each exposing
the same `try_handle(text) -> (handled, reply)` shape:

1. **Voice controls** (`agent/controls.py`) — louder/quieter, repeat, stop, sleep, "that's all."
2. **Notes / lists** (`notes/manager.py`) — when it's a notes command or a reply to an open
   confirmation (`awaiting_reply`).
3. **The brain** — everything else: a normal, grounded conversational answer.

This ordering is what lets a spoken "yes" mean "yes, create the list" mid-confirmation instead
of being read as a generic control. `VoiceSession` (`voice/session.py`) owns the ordering.

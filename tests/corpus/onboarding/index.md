# Jarvis — Onboarding Guide

*How the system works · page by page · for a new contributor*

> An in-depth tour of Jarvis, from the highest level down to the specific modules and
> functions that implement each piece. Read it in order, or jump straight to the part you
> need — every page opens with a high-level summary and points at the code.

If you are looking for what is **built** and what is **planned** rather than how it works,
read the [development plan](../../development-plans/markdown/index.md) instead.

A note on code references: these pages name **files, classes, and functions** rather than
line numbers, so they stay correct as the code moves. When in doubt the code is the source
of truth — and per `CLAUDE.md`, these docs must be updated in the same change that alters
the behavior they describe.

## Where to start

- **New to the project?** [Introduction](01-introduction.md) →
  [Architecture overview](02-architecture.md) → [The turn lifecycle](03-turn-lifecycle.md).
  Those three give you the whole shape.
- **Changing a setting?** [Configuration](14-configuration.md), plus the standalone
  [configuration guide](../../CONFIGURATION.md).
- **Writing code?** [Testing & TDD](15-testing-and-tdd.md) covers the red/green workflow
  and the coverage gate every change has to clear.
- **Editing these docs?** [How the docs are built](18-how-the-docs-are-built.md).

## Contents

Read straight through with the Previous / Next buttons, or jump in:

1. [Introduction: what Jarvis is](01-introduction.md) — the goal, the user, the constraints.
2. [Architecture overview](02-architecture.md) — the whole local voice pipeline in one view.
3. [The turn lifecycle](03-turn-lifecycle.md) — what happens between "Hey Jarvis" and the answer.
4. [The wake word](04-wake-word.md) — openWakeWord, thresholds, and always-on listening.
5. [Listening & endpointing](05-listening-and-endpointing.md) — knowing when he has finished speaking.
6. [Speech to text](06-speech-to-text.md) — Whisper on the Apple GPU.
7. [The brain](07-the-brain.md) — routing, answering, and the spoken-style contract.
8. [Research & tools](08-research-and-tools.md) — web search and deterministic freshness.
9. [The filler](09-the-filler.md) — covering the wait without ever adding to it.
10. [Text to speech & playback](10-speech-and-playback.md) — Piper, streaming, and the audio device.
11. [Barge-in](11-barge-in.md) — interrupting Jarvis mid-sentence.
12. [Voice controls](12-voice-controls.md) — louder, slower, say that again, go to sleep.
13. [Transcript & diagnostics](13-transcript-and-diagnostics.md) — seeing what happened, and why.
14. [Configuration](14-configuration.md) — every setting and where it takes effect.
15. [Testing & TDD](15-testing-and-tdd.md) — the red/green workflow and the coverage gate.
16. [Notes & lists](16-notes-and-lists.md) — the voice-managed notes subsystem.
17. [Roadmap & what's next](17-roadmap.md) — what is built and what comes after.
18. [How the docs are built](18-how-the-docs-are-built.md) — this site, and how to change it.

---

[Start reading: Introduction →](01-introduction.md)

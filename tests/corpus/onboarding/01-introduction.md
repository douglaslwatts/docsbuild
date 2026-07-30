# Introduction: what Jarvis is

**In one sentence:** Jarvis is a private, local, voice-first companion that lets a blind,
first-time computer user ask questions aloud and hear concise, warm, spoken answers.

This page sets the context — who it is for, what it must do, and the principles that shape
every technical decision that follows. Read it first; the rest of the guide keeps
referring back to these constraints.

## Who it is for

Jarvis is built for the maintainer's father, who was blinded in an early-1980s accident and
has never used a computer independently. He cannot use a keyboard or a screen reader. He is
curious and loves to learn. The dream is simple: he speaks a question into the room, and a
knowledgeable, patient voice answers — able to search the web, and (later) help him shop
safely and learn his interests over time.

That single user reframes the whole project. This is not an experimental AI platform; it is
a **reliable appliance** someone depends on daily. Polish and predictability beat cleverness.

## The non-negotiable constraints

Every design choice serves these, in roughly this priority order:

1. **Voice is the entire interface.** No keyboard, no screen. He summons Jarvis by saying
   "Hey Jarvis," speaks his question, and hears the answer. (A keyboard Enter exists as a
   tactile fallback for the maintainer during development.)
2. **Concise but complete.** Answers lead with the direct answer and the one or two facts
   that matter, in two or three spoken sentences, then offer to go deeper. Spoken answers
   must be even tighter than written ones — no padding, no lists read aloud.
3. **Patient listening.** It must wait through his pauses and never cut him off
   mid-sentence.
4. **Barge-in.** He can interrupt a reply by speaking, so a long answer is never a trap.
5. **Privacy-first and local.** The language model, speech recognition, speech synthesis,
   and all personal data run **on the device**. Only web-search queries ever leave it.
6. **Safe voice shopping (much later).** He can assemble a cart by voice, but spending
   money requires a physical fingerprint plus a trusted person's remote approval — never a
   spoken password.

## What is built today

The conversational core is complete and works well: wake word, patient listening, fast
local speech-to-text, a local brain that grounds answers in fresh web results, natural
speech output, barge-in, and voice controls (louder, slower, repeat, go deeper, sleep). The
later milestones — porting to an always-on Mac Mini, and the secure shopping subsystem —
are covered in [Roadmap & what's next](17-roadmap.md).

## How to run it

From the project root:

```
uv sync                 # install dependencies, register the console scripts
uv run jarvis-voice     # start the hands-free voice loop
```

It also needs a local [Ollama](https://ollama.com) server running the configured models.
Then say **"Hey Jarvis"** and ask something. The terminal prints the whole conversation as
it happens (see [Transcript & diagnostics](13-transcript-and-diagnostics.md)).

## Where this lives in the code

- The spoken-answer contract is the system prompt in `prompts/spoken_style.txt`.
- The project-wide rules (privacy invariants, TDD, the shopping gates) are in `CLAUDE.md`.
- The full product plan and milestone history live in the plan file referenced by
  `CLAUDE.md`.

---

[Contents](index.md) · [Next: Architecture overview →](02-architecture.md)

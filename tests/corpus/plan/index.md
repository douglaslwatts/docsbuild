# Jarvis — Development Plan

*Project plan · current state · updated 2026-07-28*

> A private, local machine a blind, first-time computer user (the maintainer's father)
> operates entirely by voice: "Hey Jarvis," a question, and a concise, warm, spoken
> answer. It can search the web, keep notes and lists, remember his interests locally,
> and — later — help him shop with the maintainer's approval on every order.

**This is the source-of-truth development plan for the app.** It is kept up to date as the
plan evolves; completed work is *marked done and moved to the archive, never deleted*, so the
history of decisions stays legible. A new contributor (or a new Claude session) should read
this page and [Where it stands](02-status.md) before making changes. These pages are generated
from the markdown in `markdown/` by `docsbuild.py` — see
[How the docs are built](../../onboarding/markdown/18-how-the-docs-are-built.md).

- [DONE] **Conversational core** — text brain, voice loop, hands-free wake word, barge-in, and voice controls (M0–M2).
- [DONE] **Memory, notes & lists** — encrypted cross-session recall, plus voice-managed notes/lists/to-dos.
- [NEXT] **M3 — the father tests it live** — the whole point is that it works for one specific person; every audio path is still unconfirmed by ear.
- [PLANNED] **M4 — the appliance** — signed `.app`, `launchd` auto-start, and the Mini's hardware, all designed and un-started.
- [LATER] **Robustness and secure shopping** — M5–M6.

## Where it stands right now

- **492 tests · 100% coverage · ruff + pyright clean.**
- All work **committed on branch `various_improvements` with a clean tree.**
- The itemised build history, with commits, is in [Completed work (archive)](14-archive.md).

## Contents

Read straight through with the Previous / Next buttons, or jump in:

1. [The goal & constraints](01-goal.md) — who this is for and the non-negotiables.
2. [Where it stands](02-status.md) — what's built, test/commit state, the live-verify debt.
3. [Architecture](03-architecture.md) — the local voice pipeline and deterministic freshness.
4. [Memory & context](04-memory.md) — compaction and encrypted cross-session recall.
5. [Voice controls & flow](05-voice-controls.md) — commands, follow-ups, spoken state cues.
6. [Notes, lists & to-dos](06-notes-lists.md) — the voice-managed notes subsystem (built).
7. [Constraints & caveats](07-constraints.md) — deliberate calls and known limits.
8. [Roadmap & milestones](08-roadmap.md) — M0 through M6 and speaker profiles.
9. [Packaging & the appliance (M4)](09-packaging.md) — the signed `.app`, `launchd`, hardware sizing.
10. [Proposed: updates & locked screen](10-updates-and-lock.md) — **still being thought out.**
11. [Secure shopping (M6)](11-shopping.md) — the highest-stakes subsystem, design locked.
12. [Security invariants](12-security.md) — the rules the code may never violate.
13. [Approach & verification](13-approach.md) — TDD, coverage, docs, live acceptance.
14. [Completed work (archive)](14-archive.md) — the build history, kept out of the way.

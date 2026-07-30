# Where it stands

**High level:** the conversational core, the memory system, and the voice-managed
notes/lists subsystem are all **built, green, and committed**. What remains is the one thing
code can't do for us — a real person using it — plus the deferred appliance and shopping work.

- **492 tests · 100% coverage · ruff + `ruff format` + pyright clean.**
- All work is **committed on branch `various_improvements` with a clean working tree.**

## What is built

Everything through **M2**, plus the memory system and the notes/lists subsystem:

- The **voice loop** end to end — wake word, patient endpointing, speech-to-text, the brain,
  streaming speech, barge-in, and the spoken voice controls.
- **Memory** — in-session compaction plus encrypted cross-session recall, maintained on a
  background thread so it never costs per-turn latency.
- **Notes, lists & to-dos** — the whole voice-managed subsystem, encrypted at rest. See
  [Notes, lists & to-dos](06-notes-lists.md).
- **Conversation-flow polish** — leave-taking, spoken state cues, voice-resumable sleep, and a
  filler that covers the wait and speaks to what was actually asked.

The itemised record, with commits, is in [Completed work (archive)](14-archive.md).

## Designed, not built

Two milestones are designed in detail with no code yet. A session picking up appliance work
should start with these rather than re-deriving them:

- [PLANNED] **M4 — packaging & the appliance.** A signed, notarized `Jarvis.app` that owns its
  microphone permission, starts at boot via `launchd`, and the hardware the Mac Mini needs
  (48 GB, 1 TB — measured, not estimated). Includes a go/no-go spike that must pass before any
  real work. See [Packaging & the appliance](09-packaging.md).
- [PLANNED] **Proposed and still being thought out** — spoken macOS update reports, a
  voice-controlled restart, and an always-locked screen with a fully functional Jarvis behind
  it. Recorded with its dead ends and open questions, and **not committed to**. See
  [Proposed: updates & locked screen](10-updates-and-lock.md).

**M6 shopping** is designed and locked but deliberately ships last — see
[Secure shopping](11-shopping.md).

## The single biggest outstanding item: live verification

- [NEXT] Every audio path is `# pragma: no cover`, so wake-word sensitivity, endpointing
  patience, barge-in feel, the filler in real conversation, whether the pop is truly gone, and
  the **spoken confirmations for every notes/lists action** are all **unconfirmed by ear**.

The next milestone is **M3 — the father tests it** — but the maintainer should run
`uv run jarvis-voice` first and confirm the paths live. Nothing here is blocked on more code;
it is blocked on listening.

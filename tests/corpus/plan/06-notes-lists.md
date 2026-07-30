# Notes, lists & to-dos

**High level:** Jarvis can take notes and keep lists entirely by voice — "start a shopping
list," "add milk," "check off milk," "read me my chores," "write me a note explaining git
worktrees." Everything is stored as markdown, **encrypted at rest**, in files Jarvis is
**hard-confined** to write only under `~/.jarvis/`. The model never touches the filesystem and
never sees a path; deterministic, tested code does all the disk work.

- [BUILT] The whole subsystem is built, green, and committed across `780549c` → `ca9c233` →
  `f4bc211`. The deep how-it-works lives in the onboarding guide
  ([Notes & lists](../../onboarding/markdown/16-notes-and-lists.md)); this page is the plan-level
  summary and the record of the decisions behind it.

## Four categories

Each kind of note/list lives in its own subdirectory under `~/.jarvis/` and renders in the
markdown style that suits it:

- `~/.jarvis/notes/` — freeform **prose** notes.
- `~/.jarvis/todos/` — **checklists** (`- [ ] item`).
- `~/.jarvis/shopping-lists/` — **checklists**.
- `~/.jarvis/lists/` — plain **bullet** lists.

Todos and shopping lists support check / uncheck; general lists are simple bullets; notes are
paragraphs. Any list can nest **one level of sub-items** under a heading.

## How a command flows

Three pieces in the `notes/` package mirror the researcher/controls patterns:

1. **`NotesRouter`** (`notes/router.py`) turns a transcript into a validated `NoteCommand`. A
   **cheap deterministic gate** (does the utterance even mention notes/lists?) keeps ordinary
   questions from paying for a model call; then one **LLM extraction** into text fields
   (`action`, `category`, `title`, `item(s)`, `parent`, `new`, `body`); then **deterministic
   validation**. The model only ever returns text — never a filename or path — and anything
   that doesn't validate **fails closed**, so the turn falls through to a normal answer.
2. **`NotesManager`** (`notes/manager.py`) executes the command, runs the multi-turn
   confirmations, and speaks a short confirmation. It exposes the same `try_handle` seam as the
   controls.
3. **`NoteStore`** (`notes/store.py`) does the file work — the single filesystem choke point.

## What it can do (all built)

- [DONE] **Create** a list/note, naming and confirming first (nothing is written until the heard
  name is read back and confirmed; "no" re-asks).
- [DONE] **Add items — confirmed one at a time.** Every item is read back for a yes/no before
  it's written; "no" asks *"What should it be instead?"* and re-confirms the correction, so one
  bad "bred" doesn't block "milk" and "eggs." Applies to a single "add milk" and to items given
  on a create.
- [DONE] **Check / uncheck** an item; **read back** a whole list (headings with their children).
- [DONE] **Two-level sub-items** — add *under* a heading, move between headings (atomic), delete
  a subtree. Depth is capped at two by a single constant (`_MAX_DEPTH`), because past two,
  placing an item by voice needs a spoken path a blind listener can't follow.
- [DONE] **Rename** an item in place (keeps its checkbox and sub-items); the new value runs
  through the same confirm-and-correct flow as an add.
- [DONE] **Clear** a list (empties items, keeps the list) and **delete** a whole list — both
  spoken-confirmed.
- [DONE] **One list, one file (identity).** `NoteStore` resolves by a **canonical slug**, so
  "August," "August to-do's," and "August to-do list" all map to one file; `create` won't
  fragment a re-worded name, and `delete` removes every canonical variant (this fixed the
  "delete reported success but the file was still there" report — a stale orphan).
- [DONE] **Follow-ups on the active list** — after you work with a list it's remembered, so a
  bare "add eggs" continues it; the gate stays closed to ordinary talk.
- [DONE] **Export** — one spoken-confirmed, **unencrypted** `.md` snapshot to `~/Desktop` for a
  sighted household member. The *only* plaintext write and the *only* write outside
  `~/.jarvis/`, to a hardcoded, containment-checked path.

## Two failure modes we deliberately guarded

A confusing early live session drove two fixes:

- **A command silently reaching the brain.** If extraction yields nothing valid the turn falls
  through to the brain, which has no notes tools. To keep that rare, extraction runs on the
  **capable answer model** (`brain.model`) by default, not the small routing model — reliable
  JSON matters more than the extra second — and it stays overridable via `notes.router_model`.
- **The brain then pretending it did the action.** Because a fall-through still produces a
  spoken answer, the brain used to fabricate results ("I reorganized your list," even "I saved
  it to your Documents folder"). The system prompt (`prompts/spoken_style.txt`) now **forbids
  the brain from ever claiming** to create, change, read back, save, export, or delete a
  note/list/to-do/file, or to invent contents or a save location. It says plainly it couldn't
  and asks the user to rephrase — never a false confirmation.

`jarvis-voice --debug` (or `JARVIS_DEBUG=1`) narrates each routing decision — gate hit/miss,
raw reply, parsed/rejected — so a command that fell through is visible, not invisible.

## Filesystem safety (the security core)

The title comes from speech and a note body may be model-authored, so neither may influence a
path. `NoteStore` is the only place a path is built, and it is confined:

- The **category is an enum**, so the subdirectory is never attacker-influenced text.
- The **title is slugified** to `[a-z0-9-]` (bounded length) and stamped with the **creation
  date** — filenames look like `grocery-list-2026-07-26.enc`, **never contain spaces**, and a
  spoken title resolves by newest-date-wins.
- Every resolved path is checked with `is_relative_to` against its allowed base before any read,
  write, append, delete, or export.
- Files are **encrypted at rest** through the injected Keychain-backed `Cipher`
  (`privacy.encrypt_at_rest`) — the same guarantee the conversation store gives
  ([security invariant #6](12-security.md)).

## Decisions logged

- **Delete policy.** Voice delete ships with a spoken confirmation now; an optional Touch ID
  gate is layered on later (config-flagged, reusing the shopping `BiometricAuthorizer`),
  decoupled from M6 so notes never had to wait.
- **Depth cap of two** — chosen for voice reliability; arbitrary depth is storable but can't be
  addressed or read back reliably by ear. A full restructure is done as separate commands (add a
  heading, add items under it, move an item), one operation per utterance.
- **Rename is items only**, not whole lists (out of scope, below).

## Out of scope (unchanged)

Renaming whole lists; compound multi-op restructures in one utterance; nesting deeper than two
levels.

## Where this lives in the code

- Package: `notes/markdown.py` (pure rendering), `notes/store.py` (`NoteStore`),
  `notes/router.py` (`NotesRouter`), `notes/manager.py` (`NotesManager`).
- Config: `NotesConfig` in `config.py`; the `notes` block in `config.yaml`.
- Wiring: the `notes` handler built in `main` (`voice/voice_cli.py`), dispatched by
  `VoiceSession` (`voice/session.py`).

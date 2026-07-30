# Notes & lists

**High level:** Jarvis can take notes and keep lists entirely by voice — "start a shopping
list", "add milk", "check off milk", "read me my chores", "write me a note explaining git
worktrees". Everything is stored as markdown, **encrypted at rest**, in files Jarvis is
**hard-confined** to write only under `~/.jarvis/`. The model never touches the filesystem
and never sees a path; deterministic, tested code does all the disk work.

## Four categories

Each kind of note/list lives in its own subdirectory under `~/.jarvis/` and renders in the
markdown style that suits it:

- `~/.jarvis/notes/` — freeform **prose** notes.
- `~/.jarvis/todos/` — **checklists** (`- [ ] item`).
- `~/.jarvis/shopping-lists/` — **checklists** (`- [ ] item`).
- `~/.jarvis/lists/` — plain **bullet** lists (`- item`).

Todos and shopping lists support **check / uncheck**; general lists are simple bullets;
notes are paragraphs. Any list can also nest **one level of sub-items** under a heading (see
[Sub-items](#sub-items-two-levels)). `~/.jarvis/` is the same private data root the
conversation memory already uses (`~/.jarvis/conversations`).

## How a spoken command flows

The pieces live in the `notes/` package and mirror the researcher/controls patterns:

1. **`NotesRouter`** (`notes/router.py`) turns a transcript into a validated `NoteCommand`.
   Like `WebResearcher`, it first runs a **cheap deterministic gate** (does the utterance
   even mention notes/lists?) so ordinary questions never pay for a model call, then one
   **LLM extraction** into fields — `action`, `category`, `title`, `item`, `body` — then
   **deterministic validation**. The model only ever returns text; anything that doesn't
   validate fails closed and the turn falls through to a normal answer. Extraction runs on
   the **capable answer model** by default (see [Reliable routing](#reliable-routing-and-an-honest-fallback)),
   and the prompt pins a few rules that were easy to get wrong by voice: a **to-do list is
   always the `todo` category** even when the user says the word "list" ("my August list"),
   and a create may carry its **first item** ("start a to-do list, first item install the
   toilets") which is stored in the list's style rather than dropped.
2. **`NotesManager`** (`notes/manager.py`) executes the command and speaks a short
   confirmation. It exposes `try_handle(text) -> (handled, reply)`, the same seam as
   `Controller`, and `VoiceSession` offers it a turn **before** the brain (see
   [The turn lifecycle](03-turn-lifecycle.md)). Authored notes ("write me a note about X")
   are composed by the brain and then stored. Several items can be given at once — the
   `items` array on a command, so "add mow the lawn and install the toilets" stores both.
3. **`NoteStore`** (`notes/store.py`) does the file work — the single filesystem choke
   point (below).

## Creating a list: naming and confirming

People say "create a to-do list", not "…called Groceries", so a create needn't carry a name —
and even when it does, speech-to-text mangles proper nouns ("Clog" for "Claude"). Since a
blind user can't glance at the result and there's no rename yet, **a create never writes until
the name is confirmed**. `NotesManager` holds a `_PendingCreate` (mirroring the delete/export
confirmation): if no name was given it asks *"What would you like to call your to-do list?"*,
then reads the heard name back — *"I heard August. Shall I create your to-do list? Say yes or
no."* On **yes** it creates the list (and adds any items carried along); **"no" re-opens the
name prompt** so a mis-hear is fixed on the spot; a cancel word ("never mind") aborts. Only
then does anything reach disk, through the same `slugify` + dated filename as every other file
(`august-2026-07-27.enc` — never a space). A titleless *add* with no active list is treated
the same way (it must create a list first).

## Adding items: confirm each one

Speech-to-text mangles proper nouns ("NASA" for "Nassau"), and a blind user can't glance at
the result to catch it — so **every item is read back for a yes/no before it's written**, the
same idea as the list-name confirmation. `NotesManager` holds a `_PendingItems` queue (like
`_PendingCreate`): for each item it asks *"Add milk to Groceries? Say yes or no."*

- **yes** writes that one item; **a skip word** ("never mind") drops just it; **anything else
  ("no")** asks *"What should it be instead?"*, and the correction is **re-confirmed** before
  moving on. So if one item in a batch is wrong, the rest still commit — one bad "bred" doesn't
  block "milk" and "eggs".
- When the queue empties, Jarvis summarizes what actually went in — *"Added milk and eggs to
  Groceries."* — or *"Okay, I didn't add anything."* A single "add milk" therefore reads: "Add
  milk? Yes or no." → "yes" → "Added milk to Groceries."
- **Items given on a create** ("create a to-do list called August and add mow the lawn and
  install the toilets") run through the same queue **after the name is confirmed**. Adding under
  a heading checks the heading exists *first*, so items are never confirmed for a place they
  can't go. (Moving an item is a single relocation, not an add, so it stays immediate.)

The queue is one more multi-turn state behind `awaiting_reply` (alongside the delete/export and
name confirmations), so `VoiceSession` routes each yes/no/correction turn to notes first.

## Follow-ups on the active list

After you work with a list, `NotesManager` remembers it as the **active list** and offers
it to the router, so a bare follow-up continues it without naming it again: "start a
shopping list", "add milk", then just **"add eggs"** or **"check off milk"**. The router's
gate stays closed to ordinary talk — it only opens for a bare command when there is an
active list *and* the utterance starts with a follow-up verb (add / remove / put / cross
off / check off / uncheck / take off), so "what's the capital of France?" still goes to the
brain. Deleting the active list clears the memory; a `list` query ("what lists do I have?")
doesn't set one.

## Sub-items (two levels)

A list can be an **outline**: top-level items ("headings") each with sub-items under them —
"Nassau to-dos" with "install the toilets" and "mow the lawn" beneath it. The depth is
**capped at two levels**, on purpose: past two, placing an item by voice would need a spoken
path and a blind listener can't follow the read-back. The cap is a single constant,
`_MAX_DEPTH` in `notes/markdown.py`, so it could be raised later — but the voice grammar and
read-back are tuned for two.

- **Add under a heading** — "add install the toilets **under** Nassau to-dos". The router fills
  a `parent` field; `NoteStore.add_item(..., parent=...)` nests the item via
  `md.add_subitem`, which only matches a **top-level** heading (so a sub-item can never become
  a parent — that's what enforces the cap). If the heading isn't found, Jarvis says so rather
  than nesting it somewhere wrong or inventing the heading.
- **Move between headings** — "move mow the lawn to Moss Side to-dos" (a `move` action).
  `NoteStore.move_item` removes the item and re-adds it under the destination, and is
  **atomic**: if the destination heading is missing it changes nothing.
- **Delete is subtree-aware** — deleting a heading drops its children too; deleting a sub-item
  drops just that line (`md.remove_item`).
- **Read-back names each heading with its children** — `md.outline` yields `(depth, item,
  checked)` per line, and `NotesManager._render_read` speaks a heading followed by its
  children ("Nassau to-dos: install the toilets, unchecked; mow the lawn, unchecked"); a
  childless top-level item reads as before.

A full restructure is done as **separate commands** (add a heading, add items under it, move an
item, read it back) — the router still does one operation per utterance.

## Renaming an item, and clearing a list

- **Rename** ("rename NASA to-dos to Nassau to-dos") edits an item's text in place, keeping its
  checkbox and any sub-items (`md.rename_item` preserves the line's prefix). Because the *new*
  value is just as prone to a mis-hear, it runs through the **same confirm-and-correct flow** as
  adding an item: Jarvis reads it back — "Rename NASA to-dos to Nassau to-dos? Yes or no." — and
  "no" asks "What should it be instead?" and re-confirms the correction. The old item is
  checked to exist first (`store.has_item`), so a rename of nothing is reported, not confirmed.
  This is a `_PendingRename` state, sibling to `_PendingItems`.
- **Clear** ("clear my August list") empties a list of all its items but keeps the list itself,
  confirmed like delete (`store.clear` keeps the `# Title` header, drops the rest). It's
  distinct from **remove** (one item) and **delete** (the whole list) — the router prompt spells
  out the three.

## One list, one file (identity)

A list's filename is its slugified title, but speech gives the title slightly differently each
time — "August", "August to-do's", "August to-do list" — which once scattered one list across
several files (and left orphans a later "delete August" couldn't reach). `NoteStore` now
resolves by a **canonical slug**: `_canonical_slug` drops trailing category words
(`august-to-do-s` → `august`), so every variant maps to one file. `create` short-circuits on
that match (no new fragment for a re-worded name), and **`delete` removes every canonical
variant**, so it fully clears a list — including a pre-existing orphan. Filenames and spoken
titles are unchanged; only *matching* is canonicalized.

## Reliable routing, and an honest fallback

Two failure modes made an early voice session confusing, and both are guarded now:

- **A command silently reaching the brain.** If the router extracts nothing valid, the turn
  falls through to the brain — which has no notes tools. To keep that rare, extraction runs
  on the **capable answer model** (`brain.model`) by default, not the small routing model;
  reliable JSON here matters more than the extra second, and it stays overridable via
  `notes.router_model`.
- **The brain then pretending it did the action.** Because a fall-through still produces a
  spoken answer, the brain used to fabricate results — "I reorganized your list", or even "I
  saved it to your Documents folder" when nothing was written. The system prompt
  (`prompts/spoken_style.txt`) now **forbids the brain from ever claiming** to create,
  change, read back, save, export, or delete a note/list/to-do/file, or to invent its
  contents or a save location. If such a request reaches the brain, it says plainly it
  couldn't do that and asks the user to rephrase — never a false confirmation.

### Diagnosing with `--debug`

Run `jarvis-voice --debug` (or set `JARVIS_DEBUG=1`) to have `NotesRouter` narrate each
routing decision to the terminal: gate **hit/miss**, the **raw model reply**, and whether the
command was **parsed** (with the action/category) or **rejected**. That makes visible exactly
why a spoken command did or didn't reach the notes system — the signal the earlier session
lacked. The sink is injected (`NotesRouter(..., debug=...)`), so it adds nothing when off.

## Filesystem safety (the security core)

The title comes from speech and a note's body may be model-authored, so neither may
influence a path. `NoteStore` is the only place a path is built, and it is confined:

- The **category is an enum**, so the subdirectory is never attacker-influenced text.
- The **title is slugified** to `[a-z0-9-]` (bounded length) and the **creation date** is
  stamped from a clock — so filenames look like `grocery-list-2026-07-26.enc`, never
  contain spaces, and a spoken title (no date) resolves to its file by newest-date-wins.
- Every resolved path is checked with `is_relative_to` against its allowed base before any
  read, write, append, delete, or export.
- Canonical files are the markdown **encrypted at rest** through the injected `Cipher`
  (the Keychain-backed Fernet key from `crypto.py`, gated by `privacy.encrypt_at_rest`) —
  the same at-rest guarantee the conversation store gives (security invariant #6).

## Confirmations, and the one plaintext export

Three destructive operations take a spoken **"yes"** across a second turn, because voice can't
confirm within one utterance:

- **Delete** a whole note/list — Jarvis reads the title back and waits for "yes".
- **Clear** a list — empties every item but keeps the list; confirmed the same way.
- **Export a plaintext copy** — on confirmation, `NoteStore.export` writes an
  **unencrypted** `.md` snapshot to a hardcoded `~/Desktop` so a sighted household member
  can open it. This is the *only* plaintext write and the *only* write outside `~/.jarvis/`;
  its directory is code-controlled (never from speech) and still containment-checked.

While any multi-turn prompt is open — a delete/clear/export "yes/no", a create's name/readback,
a per-item add, or a rename readback — the manager's `awaiting_reply` is true, and
`VoiceSession` routes the next turn to the manager **first**, so a bare "no" (or a spoken name /
item) is intercepted here instead of being read by the controls as leave-taking.

## Configuration

The `notes` block in `config.yaml` (mapped to `NotesConfig` in `config.py`):

```yaml
notes:
  enabled: true
  base_dir: ""        # "" = ~/.jarvis
  router_model: ""    # "" = use brain.model (the capable answer model)
```

Encryption reuses the existing `privacy.encrypt_at_rest` flag; there is no separate toggle.

## Where this lives in the code

- Package: `notes/markdown.py` (pure rendering), `notes/store.py` (`NoteStore`),
  `notes/router.py` (`NotesRouter`), `notes/manager.py` (`NotesManager`).
- Configuration: `NotesConfig` in `config.py`; the `notes` block in `config.yaml`.
- Wiring: the `notes` handler built in `main` (`voice/voice_cli.py`) and dispatched by
  `VoiceSession` (`voice/session.py`).

---

[← Previous: Testing & TDD](15-testing-and-tdd.md) · [Contents](index.md) · [Next: Roadmap & what's next →](17-roadmap.md)

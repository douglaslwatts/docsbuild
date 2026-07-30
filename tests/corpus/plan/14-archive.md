# Completed work (archive)

**High level:** the full record of what has been built and when. Nothing here is pending — it
is kept so the history of decisions stays legible, and moved off
[Where it stands](02-status.md) so the pages read at the start of every session stay small.

> **Why this page exists.** The plan rule is that completed items are *marked done, never
> deleted*. But `02-status.md` and `index.md` are the two pages read at the start of every
> session, and a permanently-growing "what we built" list makes that read more expensive every
> milestone. Completed history moves here once it stops being news; the current state stays
> there.

Capability lists elsewhere in the plan — the notes/lists feature list, the voice controls, the
memory behaviors — are **not** archived even though they are marked `[DONE]`. Those describe
what the system *does* today, not what happened; they belong with their subsystem.

## Built

- [DONE] **Step 0 · M0 · M1 · M2** — scaffold, text brain, push-to-talk voice loop, and full
  hands-free operation (wake word, barge-in, voice controls).
- [DONE] **Spock → Jarvis rename** and the male voice (`en_US-ryan-high`); identity and wake
  word now match.
- [DONE] **Onboarding docs** (`docs/onboarding/`) and the standalone **configuration guide**
  (`docs/CONFIGURATION.md`), both generated from markdown.
- [DONE] **Popping fix** — playback at the device-native sample rate.
- [DONE] **Deterministic weather routing** with an hour-by-hour forecast, plus a route-driven
  filler that only ever narrates the researcher's decision.
- [DONE] **Filler relevance & coverage** — research is split into `route` (decide) and
  `fetch` (look up), so the filler now speaks *during* the web request instead of after it;
  it is given what the user actually said alongside the distilled query, so it answers the
  person rather than reading the search string back; and it is cancelled unspoken if the
  answer beats it, so it can never add to the wait it exists to cover. See
  [The filler](../../onboarding/markdown/09-the-filler.md).
- [DONE] **Full memory system** — in-session compaction and cross-session encrypted recall,
  with background-thread maintenance so it never grows per-turn latency.
- [DONE] **Conversation-flow polish** — the "that's all" leave-taking command, spoken state
  transitions, voice-resumable sleep, and a wall-clock follow-up window.
- [DONE] **Model auto-provisioning** — a fresh clone downloads its models at startup instead
  of failing with "model not found" (`13a43f3`).
- [DONE] **Voice notes, lists & to-dos** — the whole subsystem: create, add, check/uncheck,
  rename, clear, read-back, delete, and a single confirmed plaintext export; two-level
  sub-items; per-item add confirmation; canonical-slug list identity. See
  [Notes, lists & to-dos](06-notes-lists.md).
- [DONE] **Docs build hardening** — the markdown converter now handles bullets that wrap across
  lines (every wrapped bullet used to be truncated, with its remainder rendered as a stray
  paragraph), and the build deletes generated pages whose markdown source is gone, so a
  rename can't leave a stale page behind. See
  [How the docs are built](../../onboarding/markdown/18-how-the-docs-are-built.md).

## Commit state

Branch `various_improvements`. The notes/lists feature line:

| Work | State |
|---|---|
| Voice notes & lists (base), backend resilience, model auto-provisioning | committed `780549c` |
| Two-level sub-items + per-item add confirmation | committed `ca9c233` |
| Rename & clear commands + list-identity (canonical-slug) fix | committed `f4bc211` |
| Filler covers the wait and speaks to what was asked | committed `a4ee3a1` |

Earlier feature line still in history: memory compaction (`c79aace`), cross-session memory
(`ca82995`), background maintenance (`d8fde83`), weather follow-up fix (`adfd9dd`), STOP-phrase
parsing (`6d371fb`), "stop"/"no" leave-taking (`a258ccf`), spoken state cues (`1547295`),
wall-clock follow-up window (`a5f432c`).

## Dropped

- [DROPPED] **STOP playback-halt activation.** Making the "stop talking" / "be quiet" phrases
  actually cut off speech didn't work in practice (they can't be *heard* mid-sentence without
  echo cancellation) and is parked on the unmerged `make_stop_phrases_active` branch. The
  phrases are still *recognized*; the mid-sentence interrupt is the wake word. See
  [Constraints & caveats](07-constraints.md).
- [DROPPED] **Custom wake-word training.** `hey_jarvis` is openWakeWord's built-in model and is
  now the permanent wake word; the companion was renamed so identity and wake word match.
- [DROPPED] **Shipping `ffmpeg` in the app bundle.** Nothing in the code path calls it. See
  [Packaging & the appliance](09-packaging.md).

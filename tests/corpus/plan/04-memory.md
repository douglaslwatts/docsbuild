# Memory & context

**High level:** long conversations stay coherent without letting the prompt grow without
bound, and Jarvis can recall a *previous* conversation across restarts — all stored locally
and encrypted at rest.

## Step 1 — in-session compaction

- [DONE] Recent messages stay verbatim; older ones fold into a running summary carried in the
  prompt, so context stays roughly constant on long chats. `ConversationMemory.compact()`,
  `LLMSummarizer`, thresholds `recent_turns: 8` / `summarize_after: 20`. Committed `c79aace`.

## Step 2 — cross-session persistence + recall

- [DONE] Each conversation's running summary is persisted **encrypted** (Fernet key in the
  macOS Keychain), **size-capped** (prune oldest-first once the store passes **25 GiB**, down
  to **20 GiB**, so it can never fill the disk), and the relevant summaries are **retrieved on
  demand** (keyword + recency scoring first; embeddings are a documented upgrade). Every record
  is keyed by an optional `user_id` (defaulting to one shared user) so voice profiles slot in
  later with no rewrite. Files: `crypto.py`, `conversation_store.py`, `memory_retrieval.py`,
  `agent/summarizer.py`. Committed `ca82995`.

## Background maintenance

- [DONE] Compaction, persistence, and pruning run on a **joined daemon thread**, off the turn's
  critical path, so the follow-up-listening window opens immediately even on a turn where
  compaction fires. `ask()` stays synchronous for the text CLI and tests; the voice path gets
  the latency win (`plan()` joins the previous turn's thread before mutating memory). Committed
  `d8fde83`.

## Notes on the design

- **Summarizer model.** Compaction defaults to the small `llama3.2`. Now that it's off the
  critical path, bumping `memory.summary_model` costs almost no latency if summaries feel lossy
  — a config knob, no code change.
- **Trade-off (accepted).** A daemon thread means if the process is killed mid-write, the last
  turn's persist may not complete. Each turn upserts the whole conversation, so at most the
  final update is lost — the same pattern as the existing filler/barge-in daemons.

`~/.jarvis/conversations` is the same private data root the [notes/lists](06-notes-lists.md)
subsystem writes under, and it uses the same Keychain-backed cipher.

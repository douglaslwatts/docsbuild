# The brain

**High level:** the brain is what turns a transcribed question into a spoken answer. It
remembers the conversation, grounds each answer in fresh web information and the current
date, asks a local language model once, and streams the reply back sentence by sentence so
speech can start before the model finishes.

## The class

`Brain` in `agent/brain.py` implements the `Responder` protocol (`plan`, `answer_stream`,
`ask_stream`, `history`). Its collaborators are all injected: an `LLMClient` (the model), an
optional `Researcher` (fresh context), and a `clock` (so "what's today's date" is testable).
It owns a `ConversationMemory`.

## What one answer does

A turn is split into two steps so the [filler](09-the-filler.md) can be driven by the
*researched decision* rather than a separate guess:

**`plan(text)` — decide what to look up (no lookup yet):**

1. **Remember the question.** Add the user's message to `ConversationMemory`.
2. **Route.** Hand the *whole* conversation to the researcher's `route`, which decides
   whether anything needs looking up and returns a `ResearchResult` (route + topic, no
   context). This is deterministic retrieval — see
   [Research & tools](08-research-and-tools.md). The decision is **stashed** for the answer.

**`answer_stream()` — run that lookup, then speak the reply grounded in it:**

3. **Fetch.** Hand the stashed decision to the researcher's `fetch`, which runs the weather
   or search call and fills in the context. Deliberately *not* done in `plan`: keeping the
   network round trip on this side means the [filler](09-the-filler.md) is already speaking
   while it happens.
4. **Compose the system message.** `_system_message` starts from the base prompt
   (`prompts/spoken_style.txt`), appends the **current date and time**, and, if the plan
   fetched anything, appends it under a header that explicitly labels it as *data, not
   instructions* (prompt-injection defense).
5. **Ask once and stream.** Call `llm.chat_stream(messages)` and pass the chunks through
   `stream_sentences`, yielding each complete, speech-cleaned sentence as it arrives.
6. **Remember the answer.** Join the sentences and store them, so follow-ups and "repeat"
   have context.

`ask_stream(text)` simply calls `plan` then `answer_stream` — the form used by the text REPL
and "tell me more", which don't need the decision. `ask` joins `ask_stream` into one string.
Research runs **once** per turn regardless of which entry point is used.

## Why grounding matters

A local model's training is frozen in the past, so on its own it will confidently give
stale answers — an old software version, last year's news, a made-up temperature. Two
mechanisms fix this without relying on the model's judgment:

- **The current date/time** is injected every turn, so time-sensitive reasoning has an
  anchor.
- **Fresh web context** is retrieved *deterministically* by the researcher and handed to
  the model, rather than hoping the model decides to call a search tool. This decouples
  accuracy from flaky tool-calling and is why a fast model can still be accurate.

The system prompt also instructs the model never to claim it "can't browse the web" — it
can, because the system searches for it — and to say so plainly and offer to look further
when the results lack an exact fact. It likewise **forbids the brain from claiming to have
performed notes/list/file actions** it can't do (creating, saving, reorganizing, or reading
back a note/list/to-do, or saving a file): those belong to the separate
[notes system](16-notes-and-lists.md), so if such a request reaches the brain it says it
couldn't do that rather than fabricating a result.

## Memory

`ConversationMemory` in `agent/memory.py` holds the running list of user/assistant turns
(`add_user`, `add_assistant`, `messages`, `clear`). It deliberately does *not* hold the
system prompt — the brain composes that fresh each turn so the date and context are always
current. `Brain.history()` exposes these turns — the same conversation the researcher is
given, which is what lets a short follow-up like "yes" resolve against the previous topic.

### In-session compaction (keeping context bounded)

Left alone, the conversation would be resent *in full* to the model every turn, so a long
chat means more tokens each turn — creeping latency, and eventually context-window pressure
and "lost-in-the-middle" quality loss. Compaction keeps the live context roughly constant:

- `ConversationMemory` also holds a **running summary** (`summary()`) and a pure
  `compact(keep_recent, summary)` that keeps only the last `keep_recent` messages and stores
  the summary in place of the rest.
- After each answer, `Brain._maybe_compact()` checks whether history has grown past
  `memory.summarize_after`. If so, it hands the *older* turns to a **`Summarizer`**
  (`LLMSummarizer` in `agent/summarizer.py`, one cheap call on the small routing model,
  faked in tests), folds them into the running summary, and keeps the last
  `memory.recent_turns` verbatim.
- `_system_message` then injects that summary each turn under "Summary of the earlier
  conversation", so the model still knows what came before without carrying every word.

Compaction runs *after* the reply is spoken and only fires occasionally, when the threshold
is crossed. It (and the cross-session save below) happen on a **background thread**
(`Brain._start_maintenance`), joined before the next turn touches memory — so end-of-turn
work adds nothing to the reply or to the follow-up-listening window. The thresholds live in
the `memory` block of `config.yaml` (`MemoryConfig`); see the
[configuration guide](../../CONFIGURATION.md).

### Cross-session memory (remembering past conversations)

Compaction only bounds the *current* session; on its own, restarting Jarvis forgets
everything. Cross-session memory persists conversations and recalls the relevant ones later,
without dragging the whole history into the live context:

- **Persist.** After each answer (on the same background maintenance thread as compaction),
  `Brain._persist` writes the current conversation (its running summary plus recent turns,
  as text) to a **`ConversationStore`**
  (`conversation_store.py`), keyed by a per-session `conversation_id`. It is **encrypted at
  rest** via a `Cipher` (`crypto.py`, Fernet with a key held in the macOS Keychain), because
  FileVault is off on the appliance. A hard **size cap** prunes the oldest conversations once
  the store passes `memory.store_max_gib`, back down to `memory.store_prune_to_gib`, so it can
  never fill the disk.
- **Recall.** At startup the Brain loads the past conversations once. On each new question,
  `Brain._recall` asks a **`MemoryRetriever`** (`memory_retrieval.py`, keyword + recency
  scoring) for the few most relevant past conversations and injects *only those* into the
  system prompt under a "Notes from earlier conversations" header (labeled data, not
  instructions). So the model can "look back" when a question relates to something from before,
  while the live context stays small.

Everything deterministic here is unit-tested with fakes; only the Keychain access is
hardware (`# pragma: no cover`). The `user_id` on each record defaults to a single shared
user — the seam for per-voice profiles later. A semantic-embedding retriever is the planned
upgrade if keyword recall proves too blunt.

## Streaming into sentences

`stream_sentences` in `agent/response_shaping.py` buffers incoming text and emits a sentence
as soon as its terminating punctuation arrives, so Piper can start speaking the first
sentence while the rest is still generating. Each sentence is passed through
`to_spoken_text`, which strips Markdown (headings, bullets, links, emphasis, inline code) —
because a text-to-speech voice would otherwise read the markup symbols aloud.

## The model adapter

`OllamaClient` in `llm/ollama_client.py` implements `LLMClient` over a local
[Ollama](https://ollama.com) server, exposing `chat` and `chat_stream`. The answer model,
temperature, and a "think" flag come from the `brain` block of `config.yaml`
(`BrainConfig`). The default answer model is a capable local model with `think: false` for
fast replies; a smaller, faster model handles the routing step (next page).

## Required models & the startup preflight

Jarvis uses more than one model: the **answer** model (`brain.model`), a small **routing**
model (`brain.research_model`) reused by the [filler](09-the-filler.md), the
[notes router](16-notes-and-lists.md), and optionally a dedicated summary model. Each needs
to be present in Ollama; a model named in `config.yaml` but not installed would otherwise
fail only mid-conversation, as a 404.

To prevent that, `main()` in `voice/voice_cli.py` runs a **preflight** at startup: it gathers
every configured model name and asks the adapter (`OllamaClient.available_models`, backed by
Ollama's model list) which are installed. The comparison lives in `llm/preflight.py`
(`missing_models`) — pure and unit-tested, it normalizes Ollama's implicit `:latest` tag so a
bare `llama3.2` matches an installed `llama3.2:latest`.

For anything missing, the default behavior (**`brain.auto_pull: true`**) is to **pull it
automatically**, streaming throttled progress via `OllamaClient.pull` +
`format_pull_progress` — the same first-run, download-if-absent experience Whisper,
openWakeWord, and the [Piper voice](10-speech-and-playback.md) already provide. Set
`brain.auto_pull: false` and the preflight instead just **warns**, naming the exact
`ollama pull …` command (useful for a controlled or offline setup). Either way it never
blocks startup, a single model's pull failure doesn't abort the others, and if Ollama itself
is unreachable it says so and carries on. Everything present is a no-op — only truly missing
models are fetched.

## Graceful degradation on backend errors

Jarvis is an always-on companion for a blind user, so a backend hiccup — a missing model, a
restarted Ollama, a dropped stream — must **never** crash it to a traceback. The adapter is
the single boundary that translates any such failure into one domain exception,
`LLMError` (`interfaces.py`): both `chat` and `chat_stream` re-raise backend errors as
`LLMError`. Each place that calls a model then degrades instead of propagating:

- the **notes router** ([notes](16-notes-and-lists.md)) *fails closed* — a backend error
  returns "not a notes command", so the turn simply falls through to the brain;
- **`VoiceSession.handle_turn`** catches `LLMError` around the answer, speaks a short,
  warm apology (`BACKEND_ERROR_APOLOGY`), and ends the turn so the loop keeps listening;
- the **filler** thread swallows `LLMError` silently — a filler-model failure never prints a
  stray traceback and never blocks the (separately guarded) answer.

## Where this lives in the code

- The brain: `Brain`, `plan`, `answer_stream`, `ask_stream`, `_system_message`, `history`
  in `agent/brain.py`.
- Memory + compaction: `ConversationMemory`, `compact`, `summary` in `agent/memory.py`;
  `Brain._maybe_compact` in `agent/brain.py`; `LLMSummarizer` in `agent/summarizer.py`.
- Cross-session memory: `Brain._persist` / `_recall` in `agent/brain.py`;
  `ConversationStore` in `conversation_store.py`; `KeywordMemoryRetriever` in
  `memory_retrieval.py`; encryption in `crypto.py`.
- Background maintenance: `Brain._start_maintenance` / `_await_maintenance` in
  `agent/brain.py`.
- Sentence streaming + markdown stripping: `stream_sentences`, `to_spoken_text` in
  `agent/response_shaping.py`.
- Model adapter: `OllamaClient` (incl. `available_models`, `pull`) in `llm/ollama_client.py`.
- Startup preflight & auto-pull: `missing_models` / `format_pull_progress` in
  `llm/preflight.py`, wired (with `_pull_model`) in `voice/voice_cli.py`.
- Backend-error resilience: `LLMError` in `interfaces.py`; `BACKEND_ERROR_APOLOGY` and the
  `handle_turn` guard and `_FillerPlayback._run` in `voice/session.py`; the fail-closed
  `route` in `notes/router.py`.
- Wiring: `build_brain` in `cli.py`.

---

[← Previous: Speech to text](06-speech-to-text.md) · [Contents](index.md) · [Next: Research & tools →](08-research-and-tools.md)

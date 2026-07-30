# The filler

**High level:** the filler is the short spoken line — "Let me check the weather in Athens
for you" — that Jarvis says *while* it researches and generates the real answer. It fills
the few seconds of dead air so the conversation feels responsive, without delaying the
answer at all.

## How it fits the turn

In `VoiceSession._speak_answer` (`voice/session.py`), the researcher **decides** first
(`responder.plan(text)`) and hands that decision — a `ResearchResult` — to the filler,
along with the transcript of what was actually said. The filler is then generated and
spoken on a **background thread**. If nothing is being looked up, the thread stays silent.

Deciding is only a fast routing call; the lookup itself happens inside `answer_stream` (see
[Research & tools](08-research-and-tools.md)). That split is deliberate: it means the filler
covers the web request *and* the answer generation — the whole slow part of the turn —
rather than starting after the network round trip has already finished.

### It can never delay the answer

The filler exists to cover dead air, so it must never create any. `_FillerPlayback` wraps
the worker thread with a small lock-guarded handover:

- when the first answer sentence is ready, `settle()` runs. If the filler has **not** begun
  speaking yet, it is cancelled and never spoken — a filler that arrives after the answer
  would only push the real reply later;
- if it **has** begun speaking, `settle()` waits for it, so the filler and the answer never
  overlap on the shared audio buffer;
- if the answer stream produces nothing at all, `finish()` lets the filler run to
  completion — there is nothing for it to make way for.

## Driven by the researcher's decision, not its own guess

This is the key idea, and the fix for a whole class of bug. The filler used to decide
**independently** of the researcher and at the same time, so the two could disagree: the
researcher would correctly decide "look nothing up" for "No, that's okay," while the filler
— a small model handed only the raw words — blurted out an invented topic ("looking up the
latest news about Elon Musk"). It also fired on declines and closings, and could latch onto
a stale topic from earlier in the conversation.

Now the filler only **narrates the researcher's `ResearchResult`**:

- **`NONE`** (nothing to look up) → the filler is *silent*. It is structurally impossible
  for it to speak when nothing is being looked up, so it can never fire on "no, that's
  okay" or invent a topic.
- **`WEATHER`** → a deterministic template, "Let me check the weather in {location} for
  you." No model call, so it cannot drift.
- **`SEARCH`** → one fast model call, bounded to the researcher's own resolved topic, so the
  subject is always the real thing.

## Speaking about the question, not the query

The route decides *whether* the filler speaks; what it says comes from both halves of the
turn. `generate(plan, text)` is given the transcript of what the user said **and** the
researcher's distilled query, formatted as two labelled lines:

```
They asked: what's going on with the Braves lately
Looking up: Atlanta Braves recent results standings
```

Both are needed. The query alone is keyword-shaped, so a filler built from it reads the
search string back at the person ("Let me look up Atlanta Braves recent results standings")
instead of answering them. The transcript alone is not enough either: after "yes, tell me
more" it names no subject at all, and only the researcher's topic knows what "that" is. The
system prompt tells the model to use *their* words for the subject and never to read the
query back, and carries three worked examples in that same two-line format.

## The generator

`FillerGenerator` in `voice/filler.py` implements the `Filler` protocol
(`generate(plan, text) -> str`). For the `SEARCH` case, a small model asked to speak freely
can still say odd things, and the user is blind and cannot see that something went wrong —
so two guards wrap it:

1. **It must look like a filler.** `_looks_like_filler` rejects a reply that is too long or
   contains a question mark (a filler must never answer or ask).
2. **It must be grounded in something that was really said.** `_grounded` requires the reply
   to share a meaningful word with the researcher's query **or** with the question itself,
   so an unrelated invented topic is still rejected. Either anchor will do: requiring the
   query alone was too strict — a good line phrased in the user's own words often echoed
   none of the keyword-shaped query and was thrown away for a disconnected "One moment."

Any error, blank, `NONE`, or rejected reply falls back to a random phrase from the
configured list, so something reasonable is always the result.

## Configuration

Whether relevant fillers are generated at all (`relevant_filler`) and the fallback phrase
list (`acknowledgments`) live in the `answers` block of `config.yaml` (`AnswersConfig`). The
filler uses the small research model at a low temperature — variety comes from the topic and
the random fallback list, not from sampling.

## Where this lives in the code

- Generator + guards: `FillerGenerator.generate`, `_search_line`, `_FILLER_SYSTEM`,
  `_FILLER_PROMPT`, `_looks_like_filler`, `_grounded` in `voice/filler.py`.
- The decision it narrates: `ResearchResult` in `interfaces.py`, produced by
  `WebResearcher.route` (`agent/research.py`).
- Concurrency + wiring: `_speak_answer`, `_start_filler`, `_FillerPlayback` in
  `voice/session.py`.
- Configuration: `AnswersConfig` in `config.py`; `answers` in `config.yaml`.

---

[← Previous: Research & tools](08-research-and-tools.md) · [Contents](index.md) · [Next: Text to speech & playback →](10-speech-and-playback.md)

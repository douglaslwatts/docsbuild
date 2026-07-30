# Configuring Jarvis

This is the practical guide to changing how Jarvis behaves — its voice, how fast it talks,
how patiently it listens, and every other easily-tuned setting. It is organized by *task*:
find what you want to change, and follow the recipe.

For how the configuration system works internally, and how it fits the rest of the system,
see the onboarding [Configuration](onboarding/markdown/14-configuration.md) page.

## How settings work

Every setting lives in one file: **`config.yaml`** at the project root. Edit a value, save,
and **restart** Jarvis (`uv run jarvis-voice`) for it to take effect.

A few things to know:

- Settings are read once at startup and frozen for the session. Anything you can also change
  *while talking* (volume, speed, sleep/wake) is covered under
  [Adjusting things by voice](#adjusting-things-by-voice-mid-session) — those changes last
  only for the session; `config.yaml` sets the starting point.
- If you delete a key, Jarvis falls back to a built-in default (defined in `config.py`), so
  you can not break it by omitting something.
- Values are grouped into sections (`wake_word`, `listening`, `text_to_speech`, ...). Keep a
  value under its correct section.

## Change the voice

The voice is a [Piper](https://github.com/rhasspy/piper) model file kept in
`models/piper/`, chosen by name in `config.yaml`.

To switch voices, just point the config at a new name — Jarvis **downloads it automatically**
on the next start if it isn't already in `models/piper/`:

```
text_to_speech:
  voice: "en_US-ryan-high"
```

Restart to hear it. (The download is a no-op once the voice is present, and only pulls a voice
that's actually missing. If you'd rather fetch it by hand, the equivalent command is
`uv run python -m piper.download_voices <voice> --download-dir models/piper`.)

**Some voices to try** (change the name and restart — each downloads on first use):

- `en_US-ryan-high` — natural US male (the current default).
- `en_US-joe-medium` — warmer, lighter US male.
- `en_US-hfc_male-medium` — neutral, steady US male.
- `en_GB-alan-medium` — British male, fitting the "Jarvis" theme.
- `en_US-amy-medium` — a US female voice, if you want to compare.

Tip: `-high` voices sound best but synthesize a little slower; `-medium` is the usual sweet
spot. Audition a few and keep the one you like. More detail:
[Text to speech & playback](onboarding/markdown/10-speech-and-playback.md).

## Change how fast it speaks

The `speaking_rate` under `text_to_speech` controls playback speed:

```
text_to_speech:
  speaking_rate: 1.15
```

- `1.0` is the voice's natural pace.
- Above `1.0` is faster (the current `1.15` is slightly brisk).
- Below `1.0` is slower and more deliberate.

Change it in steps of about `0.1` and listen. You can also speed up or slow down **by voice**
mid-session by saying "faster" or "slower" — see
[Adjusting things by voice](#adjusting-things-by-voice-mid-session).

## Change how long it waits before deciding you're finished

This is the patience dial — how long Jarvis waits, after you stop making sound, before it
decides your sentence is done and starts working. It is `trailing_silence_seconds` under
`listening`:

```
listening:
  trailing_silence_seconds: 3.0
```

- **Higher** (e.g. `4.0`) = more patient. Good if you pause to think mid-sentence ("uh...
  well...") and get cut off. The cost: this much silence is waited out on *every* turn, so it
  adds directly to how long before Jarvis responds.
- **Lower** (e.g. `2.0`) = snappier replies, but it may end your turn during a natural pause.

`3.0` is a comfortable default. This is the single most personal setting — tune it to the
speaker. Two related knobs:

- `max_utterance_seconds` (default `120`) — a hard ceiling so a stuck microphone can never
  record forever. Raise it only if someone routinely speaks for over two minutes at a stretch.
- `min_speech_seconds` (default `0.3`) — sound shorter than this is treated as noise (a cough,
  a door) and ignored, so Jarvis does not answer a phantom. Rarely needs changing.

Background: [Listening & endpointing](onboarding/markdown/05-listening-and-endpointing.md).

## Change the follow-up window

After Jarvis answers, it keeps listening for a short while so you can ask a follow-up
*without* saying "Hey Jarvis" again. Two settings under `listening` control this:

```
listening:
  follow_up_seconds: 8.0
  max_follow_ups: 6
```

- `follow_up_seconds` — how long that open window stays listening for you to start speaking
  (default `8.0`). Set it to `0` to turn the feature off entirely, so every turn needs the
  wake word.
- `max_follow_ups` — how many follow-ups in a row are allowed before Jarvis returns to
  waiting for the wake word (default `6`). This is a safety cap; there is rarely a reason to
  change it.

## Change how sensitive the wake word is

The wake word is handled under `wake_word`:

```
wake_word:
  phrase: "Hey Jarvis"
  model: "hey_jarvis"
  threshold: 0.5
  enabled_on_start: true
```

- `threshold` (0 to 1) is the sensitivity. **Lower** it (e.g. `0.4`) if "Hey Jarvis" often
  is not detected; **raise** it (e.g. `0.6`) if it triggers on background talk or the TV.
- `enabled_on_start` — whether Jarvis is listening for the wake word the moment it launches.
- `phrase` and `model` must match, and both describe the built-in `hey_jarvis` word. Changing
  the actual wake word means switching to a different built-in model (`hey_mycroft`, `alexa`,
  `hey_rhasspy`) — change `model` *and* `phrase` together — or training a custom model. See
  [The wake word](onboarding/markdown/04-wake-word.md).

## Change the language models

Jarvis uses two local [Ollama](https://ollama.com) models, set under `brain`:

```
brain:
  model: "qwen3.6:27b-mlx"
  research_model: "llama3.2:latest"
  temperature: 0.3
  think: false
  auto_pull: true
```

- `model` — the main model that writes answers. A bigger model is smarter but slower (higher
  latency before Jarvis speaks); a smaller one is faster but less capable.
- `research_model` — a small, fast model used for the behind-the-scenes routing and the
  "working on it" filler. Keep this small; it only makes quick decisions.
- `temperature` — creativity/randomness. Lower is more focused and consistent.
- `think` — leave `false` for fast replies. `true` makes the model reason more deeply but is
  much slower, which does not suit a live conversation.
- `auto_pull` — when `true` (the default), any configured Ollama model that isn't installed is
  **pulled automatically at startup**, with download progress printed. Set it to `false` for a
  controlled or offline setup, and Jarvis instead just warns, naming the `ollama pull …`
  command to run yourself.

With `auto_pull` on, a fresh setup needs no manual `ollama pull` — the startup preflight
fetches whatever is missing (and is a no-op once present). Either way, a model that is still
missing at conversation time degrades gracefully (a spoken apology) rather than crashing.
Background: [The brain](onboarding/markdown/07-the-brain.md) and
[Research & tools](onboarding/markdown/08-research-and-tools.md).

## Change the louder/quieter and faster/slower steps

The `controls` section sets how much each spoken "louder"/"quieter" or "faster"/"slower"
command moves things, and the safe limits it stays within:

```
controls:
  rate_step: 0.1
  rate_min: 0.7
  rate_max: 1.6
  volume_step: 0.1
  volume_min: 0.2
  volume_max: 1.0
```

- `*_step` — how big one "louder"/"faster" command is. Raise for coarser, quicker
  adjustments.
- `rate_min`/`rate_max` and `volume_min`/`volume_max` — the bounds those commands cannot
  exceed, so the voice can never be driven to silence or a comically fast/slow rate.

See [Voice controls](onboarding/markdown/12-voice-controls.md).

## Change the "working on it" filler

While Jarvis researches an answer, it says a short line ("Let me check the weather in Athens
for you") so there is no dead air. Configure it under `answers`:

```
answers:
  relevant_filler: true
  acknowledgments:
    - "One moment."
    - "Let me check that for you."
    - "Hang on a second."
    - "Give me just a moment."
```

- `relevant_filler` — `true` generates a line about what was actually asked; set `false` to
  always use a plain phrase from the list below instead.
- `acknowledgments` — the fallback phrases, chosen at random when a topic-specific line is
  not used. Add or reword these freely.

See [The filler](onboarding/markdown/09-the-filler.md).

## Change web search

Web search settings live under `search`:

```
search:
  backend: "duckduckgo"
  max_results: 3
```

- `max_results` — how many search hits are gathered as context for an answer. More gives the
  model more to work with but can add noise; `3` is a good balance.
- `backend` — the search provider. `duckduckgo` is the current option (a private, self-hosted
  option is planned for the appliance).

## Change how much of a long conversation it keeps in mind

To keep long conversations from slowing down, Jarvis keeps the most recent messages word for
word and folds older ones into a short running summary it still reads each turn. This lives
under `memory`:

```
memory:
  recent_turns: 8
  summarize_after: 20
  summary_model: ""
  persist: true
  store_path: ""
  retrieval_count: 3
  store_max_gib: 25.0
  store_prune_to_gib: 20.0
```

Keeping the current conversation from growing too long:

- `recent_turns` — how many of the most recent messages stay word-for-word. Higher keeps more
  exact detail live (at a bit more length each turn); lower is tighter.
- `summarize_after` — once the conversation passes this many messages, the older ones are
  summarized. Raise it to summarize less often (more detail kept verbatim for longer), lower
  it to keep the context tighter on long chats.
- `summary_model` — which model writes the summary. Leave it `""` to reuse the small, fast
  `brain.research_model`; set a model name only if you want a different one.

Remembering across restarts (so it can look back on previous conversations):

- `persist` — whether conversations are saved to disk and recalled in later sessions. `true`
  by default; set `false` to make Jarvis forget everything when it restarts.
- `store_path` — where those saved conversations live. Leave `""` for the default
  (`~/.jarvis/conversations`). They are **encrypted at rest** (see `privacy` below).
- `retrieval_count` — how many past conversations Jarvis may pull in when a new question
  relates to them. Only the relevant ones are used, so this stays small.
- `store_max_gib` / `store_prune_to_gib` — a hard disk-safety cap. Once saved conversations
  pass `store_max_gib`, the oldest are deleted until back under `store_prune_to_gib`, so the
  store can never fill the disk. (Saved summaries are tiny, so this rarely comes into play.)

Summarizing and saving happen *after* Jarvis finishes speaking, so they never delay an answer.

## Notes and lists

Jarvis can take notes and keep lists by voice — notes, to-do lists, shopping lists, and
general lists — saved as markdown files under `~/.jarvis/`. This lives under `notes`:

```
notes:
  enabled: true
  base_dir: ""
  router_model: ""
```

- `enabled` — whether voice notes/lists are on. `true` by default; set `false` to turn the
  feature off entirely.
- `base_dir` — where the files live. Leave `""` for the default (`~/.jarvis`, with a
  subfolder per kind: `notes/`, `todos/`, `shopping-lists/`, `lists/`).
- `router_model` — which model interprets a notes/lists request. Leave `""` to use the
  capable answer model, `brain.model`. Reliably turning a spoken request into the right
  action/category matters more here than the small routing model's speed, so this defaults
  to the strong model; set a different name only if you have a reason to.

**Creating a list.** You don't have to name a list up front — "create a to-do list" is
enough; Jarvis asks "what would you like to call it?". Either way it **reads the name back and
waits for a yes** before creating anything, so a misheard name is caught before it becomes the
filename; say "no" to try the name again, or "never mind" to cancel. You can also add several
items in one breath ("add mow the lawn and install the toilets").

**Adding items.** Jarvis reads **each item back for a yes/no** before adding it, so a misheard
item is caught before it lands. Say "yes" to add it, "no" to give the correct wording (which is
then confirmed), or "never mind" to skip just that one — the other items in a batch still get
added. When it's done it tells you what went in.

**Sub-items.** A list can hold one level of sub-items under a heading: "add install the
toilets **under** Nassau to-dos", and "move mow the lawn to Moss Side to-dos" to reorganize.
Reading the list back names each heading with its items. (Two levels is the limit — it keeps
things reliable to say and to hear.)

**Fixing and clearing.** "Rename NASA to-dos to Nassau to-dos" fixes a misheard item — Jarvis
reads the new name back for a yes/no (say "no" to correct it) before changing it. "Clear my
August list" empties a list but keeps it (confirmed, like delete); to remove the list entirely,
say "delete my August list". If you refer to the same list by slightly different words
("August", "my August to-dos"), Jarvis treats them as one list rather than making duplicates.

The files are **encrypted at rest** (see `privacy` below), so they aren't human-readable on
disk. When you want a readable copy, ask Jarvis to "save a plaintext copy" — it confirms,
then writes an unencrypted `.md` to your **Desktop**. That is the only unencrypted copy and
the only file Jarvis ever writes outside `~/.jarvis/`.

**Diagnosing notes commands.** If a spoken notes/list command doesn't seem to take effect,
run `jarvis-voice --debug` (or set `JARVIS_DEBUG=1`). Jarvis then prints how it routed each
command — whether it recognized it as a notes request at all, the model's raw reply, and
whether it accepted or rejected it — so you can see why a command did or didn't land.

## Adjusting things by voice, mid-session

Some settings can be changed just by speaking, without editing anything — the change lasts
until Jarvis restarts, when it returns to the `config.yaml` values:

- "louder" / "quieter" — volume, within the `controls` bounds.
- "faster" / "slower" — speaking rate, within the `controls` bounds.
- "go to sleep" / "wake up" — stop or resume wake-word listening entirely.
- "that's all" / "that will be all" / "goodbye" — end the current conversation and go back
  to waiting for the wake word, **without** going to sleep (it still answers to "Hey
  Jarvis"). Use this to close the open follow-up window immediately instead of waiting it out.
- "say that again" — repeat the last answer.
- "tell me more" / "go deeper" — a longer version of the last answer.
- "stop" — stop talking.

These are the accessibility controls; the full list and how they work is in
[Voice controls](onboarding/markdown/12-voice-controls.md).

## Full settings reference

Every section of `config.yaml`, with its keys and defaults:

- **wake_word** — `phrase` ("Hey Jarvis"), `model` ("hey_jarvis"), `model_path` (""),
  `threshold` (0.5), `enabled_on_start` (true).
- **listening** — `trailing_silence_seconds` (3.0), `max_utterance_seconds` (120),
  `follow_up_seconds` (8.0), `min_speech_seconds` (0.3), `max_follow_ups` (6).
- **speech_to_text** — `model` ("mlx-community/whisper-large-v3-turbo"), `language` ("en").
- **text_to_speech** — `voice` ("en_US-ryan-high"), `speaking_rate` (1.15).
- **brain** — `provider` ("ollama"), `model` ("qwen3.6:27b-mlx"), `research_model`
  ("llama3.2:latest"), `temperature` (0.3), `think` (false), `auto_pull` (true).
- **answers** — `default_max_sentences` (3), `offer_more` (true), `relevant_filler` (true),
  `acknowledgments` (a list of fallback phrases).
- **controls** — `rate_step` (0.1), `rate_min` (0.7), `rate_max` (1.6), `volume_step` (0.1),
  `volume_min` (0.2), `volume_max` (1.0).
- **memory** — `recent_turns` (8), `summarize_after` (20), `summary_model` (""),
  `persist` (true), `store_path` (""), `retrieval_count` (3), `store_max_gib` (25.0),
  `store_prune_to_gib` (20.0).
- **search** — `backend` ("duckduckgo"), `max_results` (3).
- **notes** — `enabled` (true), `base_dir` ("" = ~/.jarvis), `router_model` ("" =
  `brain.model`).
- **privacy** — `encrypt_at_rest` (true): encrypt saved conversations **and** notes/lists
  with a key kept in the macOS Keychain.

The `shopping` section in `config.yaml` is a placeholder for a future milestone and does not
affect anything yet.

## Tips and gotchas

- **Restart after editing.** `config.yaml` is read only at startup.
- **Change one thing at a time** and listen — especially voice and patience settings, which
  are about feel, not correctness.
- **Voice model names must match a downloaded file** in `models/piper/`, and **Ollama model
  names must be pulled** first, or startup will fail to find them.
- **Patience vs. speed is a real trade-off.** A more patient `trailing_silence_seconds` means
  a longer wait before every reply. Tune it to the person, not to a number.

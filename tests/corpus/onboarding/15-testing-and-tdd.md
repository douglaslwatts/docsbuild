# Testing & TDD

**High level:** the whole codebase is built with strict red/green test-driven development and
kept at (near) 100% test coverage. This is not ceremony — it is what makes a voice appliance
someone depends on daily trustworthy, and it is enforced mechanically. If you change the
code, you write the test first.

## The rules (from `CLAUDE.md`)

1. **Red → Green → Refactor.** Write a failing test that specifies the next behavior; write
   the minimum code to pass it; clean up with tests green. Never write implementation before
   there is a failing test for it.
2. **Coverage ≥ 95%, kept near 100%.** The suite runs with `--cov-fail-under=95`, so it
   *fails* below the bar. New code lands with its tests.
3. **PEP 8 and types.** `ruff` (lint + format) and `pyright` must pass; enforced by
   pre-commit.

Run everything with:

```
uv run pytest                     # tests + coverage gate
uv run ruff check . && uv run ruff format --check .
uv run pyright
```

## How the design makes this possible

The architecture exists *for* testability. Deterministic logic sits behind `Protocol`
interfaces (`interfaces.py`) and is tested directly against **fakes**; thin adapters wrap
the real hardware and network and are the only things allowed to be uncovered.

- **Fakes, not mocks.** A test builds a `VoiceSession` from a fake recorder, fake
  transcriber, fake responder, fake speaker, and asserts on exactly what was spoken and
  returned — no microphone, no model, no network. The same pattern covers the brain (fake
  `LLMClient`), the researcher (fake search), the controller (fake speaker/brain), and so
  on.
- **`# pragma: no cover` marks the edges.** The genuine hardware/network calls — the mic
  loop, the Piper model load, the Ollama call, the openWakeWord inference — are marked no
  cover and verified *by ear*. Everything around them (the logic that decides what to do
  with their results) is covered.
- **Pure cores.** The trickiest logic is deliberately pure so it can be tested exhaustively:
  `Endpointer` (a state machine fed frame decisions), `parse_command`, the `audio.py` math
  (`resample`, `apply_gain`, `apply_fade`), `stream_sentences`, and `_format_weather`.

## Adding a feature — the workflow

Say you want a new voice control, "mute":

1. **Red:** add a case to the `parse_command` test asserting `"mute"` maps to a new
   `Command.MUTE`; add a `Controller` test asserting it sets volume to zero and confirms.
   Run — watch them fail.
2. **Green:** add `MUTE` to the `Command` enum and its phrases, and a handler in
   `Controller._HANDLERS`. Run — watch them pass.
3. **Refactor:** tidy up; keep tests green.
4. **Docs:** update the relevant onboarding page ([Voice controls](12-voice-controls.md))
   in the same change — this is required, see below.

## Live verification is still owed

Because the audio edges are `# pragma: no cover`, unit tests prove the *wiring*, not the
*feel*. Anything touching real audio — wake-word sensitivity, endpointing patience, the
sound of a voice, whether a pop is gone — must be confirmed by actually running
`uv run jarvis-voice` and listening. Several past bugs (popping, a runaway self-conversation)
were only found and fixed this way.

## Keeping these docs honest

`CLAUDE.md` requires that this onboarding documentation is updated **in the same change**
that alters the behavior it describes, and that the HTML is regenerated
(`uv run python docs/docsbuild.py --all`). Docs that drift from the code are worse than no
docs.

## Where this lives in the code

- The rules: `CLAUDE.md`.
- The contracts that enable fakes: `interfaces.py`.
- The coverage gate and tool config: `pyproject.toml`.
- The tests themselves: `tests/unit/`, mirroring `src/voice_companion/`.

---

[← Previous: Configuration](14-configuration.md) · [Contents](index.md) · [Next: Notes & lists →](16-notes-and-lists.md)

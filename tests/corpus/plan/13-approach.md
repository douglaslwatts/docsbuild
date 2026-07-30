# Approach & verification

**High level:** how we build this, and what still has to be confirmed by a human ear.

## Development approach

- **Strict red/green TDD** (mandatory, in `CLAUDE.md`): a failing test that specifies the next
  behavior → the minimum code to pass → refactor with tests green. Never write implementation
  before there is a failing test for it.
- **≥95% coverage, kept near 100%** — enforced mechanically by `pytest --cov-fail-under=95`, so
  the suite *fails* below the threshold. It currently sits at **100% across 474 tests.**
- **Testable architecture** — deterministic logic behind `Protocol` interfaces (TDD'd directly);
  thin adapters wrap external services (Ollama, Whisper, Piper, Playwright, Keychain, network)
  and are **faked** in unit tests; real hardware paths are `# pragma: no cover` and live-verified.
- **DRY, PEP 8 (ruff), type hints (pyright standard).** `pre-commit` runs ruff + `ruff format` +
  pyright + the coverage-gated suite before every commit.
- **Docs are kept in sync in the same change.** A behavior/architecture change updates the
  relevant `docs/onboarding/markdown/*.md`; a config change updates `docs/CONFIGURATION.md`; a
  plan change updates these `docs/development-plans/markdown/*.md` pages — then the HTML is
  regenerated.

```
uv sync                                   # install deps
uv run pytest                             # full suite + coverage gate
uv run pytest -m "not integration"        # fast unit-only run
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run python docs/docsbuild.py --all     # regenerate both doc sets' HTML
uv run jarvis-voice                       # live: the real audio loop
```

## Live acceptance (owed by the maintainer)

Run `uv run jarvis-voice` and confirm by ear:

- A natural back-and-forth **without re-saying the wake word**; a weather question gives real
  highs/lows and, on "yes," the hour-by-hour breakdown; a decline ("no, that's okay") draws no
  filler and no invented topic.
- **"That's all for now"** ends the open window while **"Hey Jarvis"** still wakes it; "go to
  sleep" quiets Jarvis but still resumes on the wake word.
- A **20+ message conversation** stays coherent with roughly flat per-turn latency; across a
  restart, Jarvis can **recall the previous conversation** while the live context stays small.
- The **notes/lists confirmations** feel right spoken aloud: creating a list confirms the name;
  each added item is read back for yes/no with a working correction; rename, clear, delete, and
  the plaintext export each take a spoken "yes"; and a mis-routed request is honestly declined,
  never falsely confirmed.

Then, and only then: **M3 — the father tests it.** Nothing here is blocked on more code; it is
blocked on listening.

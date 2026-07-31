# CLAUDE.md — docsbuild

docsbuild turns a directory of markdown into a browsable HTML site with a contents sidebar and
Previous / Next links. Every page it emits is **self-contained** — the stylesheet is written
into the file — so it opens straight from disk over `file://` with no server and no missing
assets. It is deliberately small in *scope*, not in correctness: no plugins, themes, templates,
shortcodes, or search index.

The whole program is one file, `src/docsbuild/__init__.py` (~1,200 lines including docstrings),
plus a bundled `style.css`. Keeping it in one file is a deliberate choice — see the onboarding
guide.

## The onboarding guide is a source of truth (MANDATORY — keep it updated)

**`docs/onboarding/` is in-depth documentation of how this tool works and why, and it MUST be
kept up to date with the current state of the system.** It is not a nice-to-have written once:
it is where the *reasoning* lives, including the decisions that were wrong first. The code says
what it does; the guide says why.

**Any change that alters behavior, moves or renames something the guide references, adds or
changes a `site.toml`/`sites.toml` key, or changes the release workflow MUST update the
relevant page in the same change.** Docs that drift from the code are worse than no docs.

Rules:

- **The markdown under `docs/onboarding/markdown/` is the single source of truth.** The `html/`
  directories are generated and **not tracked by git** (`.gitignore` ignores every `html/`), so
  **never hand-edit generated HTML** — rebuild it.
- Regenerate after editing:

  ```bash
  uv run docsbuild --set onboarding
  ```

- **Reference files and class/function names, not line numbers**, so the text survives the code
  moving.
- **Each page opens with a high-level summary** before going deep.
- **Every page stands on its own.** Assume the reader has not read the others: explain
  project- and domain-specific terms on first use *on each page* (doc set, chrome, token
  stream, core rule, CommonMark, semver, editable install), and expand an acronym before using
  it. Prefer plain phrasing over jargon and short sentences over dense ones.
- **Write for a competent developer new to this codebase and its domain** — readable end to end
  by anyone from a junior to a principal engineer without external lookups. **Depth is not the
  same as difficulty:** go as deep as the subject needs, in language that stays easy.
- **Adding a page** means creating `docs/onboarding/markdown/<NN>-<slug>.md`, adding it to the
  Contents list in that directory's `index.md`, and wiring the Previous / Next footer links on
  it and its neighbour. The sidebar and reading order come from the directory automatically.
- **Figures in the guide are measurements, not estimates.** Page counts, byte sizes and test
  counts appear in the prose; if a change moves one, re-measure it rather than guessing.

Keep `README.md` in sync too — it is the front door and repeats the install, configuration and
release story.

**The guide is built by the tool it documents**, and `tests/test_example.py` enforces that:
`test_the_onboarding_guide_builds` asserts the built pages match the markdown sources exactly,
and `test_every_link_in_the_guide_resolves` catches a cross-reference or a mis-wired footer
pointing at a page that does not exist. So a change that breaks the build, or a page added
without its links, **fails the test suite** rather than being discovered by hand later.

## Development workflow — Red/Green TDD (MANDATORY)

1. **Red** — write a failing test that specifies the next behavior. Run it; watch it fail.
2. **Green** — write the *minimum* code to make it pass. Run it; watch it pass.
3. **Refactor** — clean up with the tests green.

Never write implementation code before there is a failing test for it.

## Test coverage (MANDATORY)

- **≥95% is a hard requirement, kept as close to 100% as reasonably possible.** It currently
  sits at **100% across 423 tests.**
- Enforced mechanically: `pytest` runs with `--cov-fail-under=95`, so the suite *fails* below
  the threshold.
- New code lands together with its tests.

## Two test strategies, both deliberate

- **Unit tests** (`tests/test_docsbuild.py`, `test_init.py`, `test_build.py`, `test_cli.py`) —
  small hand-written inputs asserting specific behavior. They assert **semantics, not exact
  HTML**: "a `<ul>` with two `<li>`", not a byte string. Exact-HTML assertions all had to be
  rewritten when the renderer was swapped; property assertions survived.
- **The corpus harness** (`tests/test_corpus.py`) — 40 real documents, ~200 KB, asserting
  **invariants**: no leaked `**`, no unrendered `](`, every `.md` link became `.html`, output
  parses as well-formed markup. This is what makes a renderer swap verifiable, and it must stay
  implementation-agnostic.

## Code quality

- **PEP 8** — https://peps.python.org/pep-0008/ — enforced by `ruff` (a pycodestyle superset).
- Type hints everywhere; `pyright` in standard mode must pass.
- **DRY** — a rule that exists in two places must be fixed in both. This has bitten here: the
  greedy-loose-markdown bug was fixed in `detect_sets` and left wrong in `_as_set` one level up,
  where it caused the same failure a week later.
- Note `ruff` 0.16+ formats Python inside fenced markdown blocks, so hand-laid-out snippets in
  docs come back re-wrapped.

## Releases

A release is a **git tag** — there is no package index. Tags are v-prefixed semver (`v0.1.0`)
and always match `version` in `pyproject.toml`. Cutting one and consuming one are documented in
`docs/onboarding/markdown/14-releasing.md`; that page is the source of truth for the workflow,
including why `uv run --no-sync` is mandatory when testing local changes against a consuming
project.

## Commands

```bash
uv sync                                  # install deps (incl. dev group)
uv run pytest                            # full suite + coverage gate
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run docsbuild --set onboarding        # rebuild this project's own guide
uv run docsbuild --help
```

## Layout

`src/docsbuild/` (the program plus `style.css`), `tests/` (unit tests, the corpus harness and
its `corpus/` documents), `example/` (a tiny two-page project used by tests and by the README),
and `docs/onboarding/` (this project's own guide, built by itself).

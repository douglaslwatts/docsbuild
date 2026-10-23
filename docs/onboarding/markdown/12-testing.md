# How it is tested

**There are two test strategies here, doing genuinely different jobs.** Ordinary unit tests
check specific behaviours against small hand-written inputs. A corpus harness runs 40 real
documents through the renderer and checks properties that must hold for all of them. This
page explains why both exist, what each catches, and — importantly — what neither catches.

```bash
uv run pytest          # 436 tests, 100% coverage, gate at 95%
uv run ruff check . && uv run ruff format --check .
uv run pyright
```

## The two kinds

| | Unit tests | Corpus harness |
|---|---|---|
| Files | `test_docsbuild.py`, `test_init.py`, `test_build.py`, `test_cli.py`, `test_links.py` | `test_corpus.py` |
| Input | small, hand-written | 40 real documents, ~200 KB |
| Asserts | specific behaviour | invariants across every page |
| Catches | "this feature is wrong" | "something is wrong *somewhere*" |

## Unit tests assert semantics, not exact HTML

This is a deliberate change of style, and it earned itself.

The converter tests used to pin exact output strings — `assert out == "<ul><li>one</li>…"`.
When the hand-written converter was [replaced with `markdown-it-py`](05-the-renderer.md),
every one of those strings changed, and every one of those changes was cosmetic:
whitespace between block elements, mostly. Twenty tests failed for no real reason and had
to be rewritten anyway.

They now assert what actually matters:

```python
def test_lists_nest(db):
    out = db.md_to_html("- top\n  - child\n    - grandchild\n- sibling")

    assert _tags(out, "ul") == 3
    assert _tags(out, "li") == 4
    assert "top - child" not in out  # the old flattening bug
```

Three lists, four items. Whether markdown-it puts a newline between them is not something
anyone should be asserting.

## The corpus harness

`test_corpus.py` runs every document in `tests/corpus/` — real documentation written
without any thought for this tool — through the renderer, and asserts invariants:

- no literal `**` outside code spans (leaked bold markers)
- no unrendered `](` (a link form the converter did not understand)
- no stray `!` before an `<a>` (an image rendered as a link)
- every `.md` link rewritten to `.html`, a `#section` after it included
- output is **well-formed** — tags nest and close, checked with the standard library's
  `html.parser`
- one heading element per heading line in the source

### Why it exists

Every rendering bug this tool has shipped was found by eye, in output, weeks later. The
image bug — `![alt](x.png)` producing `!<a href="x.png">alt</a>` — survived a deliberate
audit of the converter's documented limits, because nobody thought to write an image.

Invariants catch that class of bug mechanically. You do not have to think of the case; you
have to think of the *property*.

### It asserts properties, never exact HTML

That is what let it survive the renderer swap unchanged, and therefore **verify** it. When
the entire converter was replaced, the corpus tests carried across untouched and could
confirm that 34 of 35 real pages rendered byte-identical *visible text*.

A test suite that pins exact output cannot validate a change to how output is produced. One
that pins properties can.

### The known-defect pattern

When the four wrong-output bugs were found, each was written into the harness as the
assertion it *should* satisfy, marked `xfail(strict=True)`:

```python
@pytest.mark.xfail(strict=True, reason="known defect")
def test_images_render_as_images():
    assert '<img src="diagram.png"' in docsbuild.md_to_html("![A diagram](diagram.png)")
```

`strict=True` is the point. An expected failure that starts *passing* reports
`XPASS(strict)` and **fails the run** — so fixing the bug announces itself, and the marker
has to be deleted deliberately. It cannot be quietly fixed, and the assertion cannot be
weakened to make it pass. All four eventually flipped that way.

### The synthetic page

`tests/corpus/misc/synthetic-constructs.md` exists because the real corpus turned out to
contain **zero nested lists and zero images** — so the two most recently fixed features had
no corpus coverage at all. Real documents are a good sample of what people write; they are
not a complete sample of what the tool must handle. The synthetic page deliberately
exercises every supported construct.

## What neither strategy caught

Worth being honest about, because it bounds what the harness is for.

The old converter mangled **double-backtick code spans** — `` `` `code` `` `` — producing
stray backticks and, in one case, rendering `**not bold**` as actually bold. On the page
whose own sentence explained that code spans are protected from exactly that.

No invariant caught it. The harness checks for markup **leaking through**; this was markup
being **interpreted when it should not have been**. The output contained no literal `**`,
so `test_no_unrendered_bold_markers` was satisfied — by a `<strong>` element that should
never have existed.

It surfaced only when the output was diffed against a more correct implementation. That is
a real limit: invariants find *malformed* output, not output that is well-formed and wrong.

## Coverage as a bug-finding tool

The suite runs at 100% with the gate at 95%, and the extra 5% is not vanity. **Two bugs in
the badge rule were found by asking what input would reach an unexercised branch** — the
nested-item badge theft and the reference-link collision, both described in
[Status badges](06-badges.md). Neither was likely in practice; both would have been
baffling to debug from a screenshot.

One branch is genuinely unreachable — the badge scan's inner loop always exits by `break`,
because every `list_item_open` has a matching close. It is marked `# pragma: no branch`
with that reason written next to it, rather than contriving a test for it or leaving the
number below 100 with no explanation.

## Tests find bugs in tests, too

Three times while building this, the failure was in the test rather than the code:

- The heading-count invariant treated `# docs/sites.toml` inside a fenced code block as a
  heading. The converter was right to ignore it.
- A visible-text comparison counted whitespace *between* tags as text, reporting 0 of 35
  pages matching when the real answer was 34.
- A verification script uncommented a config's prose along with its examples, producing
  invalid TOML — which turned out to be a genuine usability flaw in the generated file, now
  fixed and pinned by a test.

Worth expecting. A test that fails is evidence about the system *including the test*.

## Where it runs without being asked

Everything above also runs in **continuous integration** — a service that builds and tests a
project automatically, on GitHub's machines, every time work is pushed. The workflow lives in
`.github/workflows/ci.yml` and fires on every pull request to `main` and `dev`, and on every
push to them.

It is two jobs:

- **`test`** runs `uv run pytest` four times over, once each on Python 3.11, 3.12, 3.13 and
  3.14. Running the same suite across several interpreters is called a **matrix**.
- **`quality`** runs `ruff check`, `ruff format --check` and `pyright` once.

The matrix is the point. `pyproject.toml` declares `requires-python = ">=3.11"`, which is a
promise to anyone installing this tool. Locally the suite only ever ran on whichever interpreter
`uv` picked, so nothing tested the oldest version that promise covers. Now something does, and a
change that quietly depends on newer syntax fails before it is merged rather than after someone
installs it.

Two smaller choices worth knowing:

- `uv sync --locked` makes the run **fail** if `uv.lock` is out of date, instead of quietly
  resolving different package versions from the ones you have locally.
- `uv run --no-sync` runs against the environment as it already stands. It is the same habit
  described in [Releasing a version](14-releasing.md), for the same reason: a plain `uv run`
  would reconcile the environment first and could undo what you just set up.

All five checks — the four interpreters and `quality` — are marked **required** by the branch
protection rules, so a pull request whose tests fail cannot be merged. Coverage is included
automatically: the 95 % gate lives in pytest's own `addopts`, so a drop below it fails the run
without CI needing to know about it.

---

[← Previous: Configuration reference](11-configuration.md) · [Contents](index.md) ·
[Next: How it got here →](13-history.md)

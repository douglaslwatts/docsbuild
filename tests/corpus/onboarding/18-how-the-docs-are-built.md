# How the docs are built

Every page you are reading — this guide and the development plan — is **generated**. You write
markdown; a small Python program turns it into styled HTML. This page explains how that works,
what you are allowed to edit, and where it will surprise you.

No prior knowledge assumed. If you can read a `for` loop, you can read the whole thing — it is
about 300 lines and has no dependencies.

## The one rule

There are two directories, and only one of them is yours:

| Directory | Who writes it | Edit it? |
|---|---|---|
| `markdown/` | **You**, by hand | **Yes.** This is the source of truth. |
| `html/` | the build | **Never.** The next build overwrites your changes. |

If you edit a file in `html/`, your work vanishes the next time anyone runs the builder — with
no warning and no error. Everything you want to keep goes in `markdown/`.

The `html/` directories are **not stored in git**. They are rebuilt from the markdown whenever
someone needs them, which is why you may not have any HTML at all after a fresh `git clone`.
That is normal — run the builder.

## Running it

One command builds everything:

```bash
uv run python docs/docsbuild.py --all
```

Or just the set you changed:

```bash
uv run python docs/docsbuild.py --set onboarding
uv run python docs/docsbuild.py --set development-plans
```

It prints what it did. Then open the built page in a browser:

```bash
open docs/onboarding/html/index.html
```

There is no server and no install step. The build uses only Python's standard library, so it
needs **Python 3.11 or newer and nothing else** — no `uv sync`, no packages. (3.11 is the floor
only because the config files are TOML, and `tomllib` arrived in 3.11.)

## One program, two doc sets

Both guides come out of a single program. Nothing is duplicated between them:

| File | What it is |
|---|---|
| `docs/docsbuild.py` | The whole build: converter, page chrome, and command line. |
| `docs/style.css` | The styling — which is why both guides look identical. |
| `docs/sites.toml` | The list of doc sets that `--all` builds. |
| `docs/onboarding/site.toml` | This guide's settings. |
| `docs/development-plans/site.toml` | The plan's settings. |

**This matters when you change the converter.** A fix in `docsbuild.py` fixes both guides at
once — which is the point, since the same bug used to have to be found and fixed twice. It also
means a mistake there breaks every page in the repo, which is why that file is the one piece of
docs tooling with tests: `tests/unit/test_docsbuild.py`.

## What a `site.toml` says

Each doc set describes itself in a small config file beside its markdown:

```toml
brand        = "Jarvis · Onboarding"   # the label at the top of the sidebar
title_suffix = "Jarvis Onboarding"     # appended to each browser-tab title
source       = "markdown"              # where the pages are
output       = "html"                  # where the built site goes
style        = "../style.css"

[titles]
index = "Overview & contents"          # sidebar label, when it differs from the H1
```

Paths are resolved **relative to the config file**, not to wherever you happen to be standing
when you run the build. That is what lets the same program build a doc set in another
directory, or in another repository entirely, via `--root`.

## Pages are discovered, not declared

There is no list of pages anywhere. The build reads the `source` directory and works it out:

- **Which pages exist** — every `*.md` file in the directory is a page.
- **What order they go in** — sorted by filename, except a page named `index`, which is always
  first. (Plain sorting would put it last, since letters sort after digits.) Files are named
  `01-…`, `02-…` precisely so that filename order *is* reading order.
- **What each is called** — the page's own first `# heading`. The `[titles]` table in
  `site.toml` overrides that, which is only needed when the sidebar wants something shorter
  than the page's real title.

That order drives the sidebar, the Previous / Next buttons, and the reading chain.

**To add a page:** create `markdown/<name>.md` starting with a `# Heading`, add it to the
contents list in `markdown/index.md`, wire the footer links on the neighbouring pages, and
rebuild. The build finds it on its own.

## What the build actually does

Four steps, in this order:

1. **Read** every markdown file it discovered. If one vanishes mid-build, it stops immediately
   rather than producing a half-finished site.
2. **Convert** each one to HTML, in memory.
3. **Delete** any `.html` file in the output directory that no longer has a markdown source.
4. **Write** the new pages.

Step 3 is why renaming a page cleans up after itself. Before it existed, renaming
`09-shopping.md` to `11-shopping.md` left the old `09-shopping.html` sitting in the output
directory forever — still opening in a browser, still turning up in searches, quietly showing
content that no longer matched any source file.

**Why deleting happens at step 3 and not step 1** is worth understanding, because it looks
backwards. If the build deleted everything first and *then* started converting, a crash
half-way through would leave you with no documentation at all. By converting everything first
and only deleting once all the new content is safely in memory, a failure leaves the existing
docs completely untouched.

## How the markdown converter works

`md_to_html` walks the file **one line at a time** and asks a simple question: *what kind of
line is this?*

- Starts with ` ``` `? → a code block. Swallow lines until the closing fence.
- Starts with `#`? → a heading.
- Starts with `- ` or `* `? → a bullet list.
- Starts with `1. `? → a numbered list.
- Starts with `|` and the next line is `|---|`? → a table.
- Just `---`? → a horizontal rule.
- Blank? → skip.
- Anything else → a paragraph.

Each branch consumes all the lines belonging to that block, then the loop continues from
wherever it stopped. That is the whole design. It is maybe 60 lines of code, and it lives in
`md_to_html` in `docs/docsbuild.py`.

### Where it will surprise you

This converter handles a **small, deliberately limited subset of markdown — not everything
GitHub renders.** Two traps have actually bitten this project:

**Bullets that wrap onto the next line.** This is fine now, but it used to break badly:

```markdown
- **Some point.** A long sentence that continues
  onto a second, indented line.
```

The list branch originally read only the first line, so the second line fell out of the list
and became a stray paragraph, every bullet became its own one-item list, and any `**bold**`
spanning the line break leaked through as literal asterisks. Now the builder collects indented
continuation lines into the item they belong to.

**Italics inside bold.** This still does not work:

```markdown
- **The brain then *pretending* it did the action.**
```

The pattern that finds bold text is `\*\*([^*]+)\*\*` — "two asterisks, then some characters
that are *not* asterisks, then two asterisks." The inner `*pretending*` breaks that match, and
the raw `**` ends up visible on the page. **Don't nest emphasis inside bold.** Pick one.

That limitation is **asserted by a test**, not just written down here — see
`test_italics_nested_inside_bold_is_a_known_limitation`. So this page and the test suite state
the same thing, and if anyone ever teaches the converter to handle it, the test fails loudly
and this paragraph gets updated with it.

If output ever looks wrong, suspect the markdown before the build — and check whether you used
something outside the supported subset.

### The order inline formatting is applied

Inside a line, `inline` does its work in a specific sequence, and the sequence matters:

1. **Stash `` `code` `` spans** behind placeholders.
2. **Escape** HTML characters (`<` becomes `&lt;`, and so on).
3. Convert **links**, then **bold**, then **italics**.
4. **Restore** the stashed code spans.

Code spans are pulled out first so nothing inside them is escaped or reinterpreted — that is
what lets you write `` `<html>` `` or `` `**not bold**` `` in backticks and have it come out as
literal text. This kind of ordering looks arbitrary right up until you change it and something
breaks.

## Two details worth knowing

**The stylesheet is pasted into every page.** Rather than linking to `docs/style.css`, the
build copies its full contents into a `<style>` tag in each file. That makes every page
completely self-contained: it opens straight from disk, over `file://`, with no server and no
chance of a missing stylesheet. The cost is that all the pages get bigger — a fine trade for
docs. A small script alongside it restores your light/dark choice before the page paints, so
switching themes doesn't flash.

**Links are written as `.md`, not `.html`.** In the markdown you write:

```markdown
See [The wake word](04-wake-word.md).
```

…so the link works when someone reads the source on GitHub. The builder rewrites `.md` to
`.html` on the way out, so it also works in the built site. Write `.md` and let the builder
handle it.

## Two features you will mostly see in the plan

Both live in the shared converter, so either guide can use them. In practice the development
plan uses them and this one rarely does.

**Status badges.** A list item starting with `[DONE]`, `[NEXT]`, `[LATER]`, `[PLANNED]`,
`[BUILT]` or `[DROPPED]` renders as a coloured pill instead of literal text. This is how the
plan marks finished work without deleting it:

```markdown
- [DONE] **Full memory system** — in-session compaction and cross-session recall.
```

A bracketed word that *isn't* in that list is left alone as ordinary text, so `[TODO]` in a
sentence won't accidentally become a badge.

**Tables.** Standard pipe tables work, and get wrapped in a scrolling container so a wide one
never makes the whole page scroll sideways:

```markdown
| Thing | What it does |
|---|---|
| `markdown/` | You write it |
```

## Two outputs that aren't ordinary pages

A doc set can ask for extras in its `site.toml`.

The development plan asks for **`plan.md`** — every plan page concatenated in reading order
into a single file. It exists so the whole plan can be read top-to-bottom, diffed in one place,
or loaded by a tool in one read; links between pages become in-document anchors. It is
generated, so never edit it by hand — but unlike the `html/` directories it **is** tracked in
git, because a fresh clone needs it before anyone has run a build.

This guide asks for a **standalone page**: `docs/CONFIGURATION.html`, built from
`docs/CONFIGURATION.md`. It sits outside the reading chain and gets an in-page section index
instead of Previous / Next buttons. If you edit the configuration guide, this is the build that
regenerates it.

## If something looks wrong

1. **Check the markdown first.** The HTML is only ever a reflection of it.
2. **Check you are not using unsupported markdown** — nested emphasis is the usual culprit.
3. **Rebuild.** Half of all "the docs are wrong" reports are just a build that was never run.
4. **Never fix it by editing `html/`.** That change survives exactly until the next build.

---

[← Previous: Roadmap & what's next](17-roadmap.md) · [Contents](index.md)

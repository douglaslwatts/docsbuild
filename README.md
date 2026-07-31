# docsbuild

Turn a directory of markdown into a browsable HTML site with a contents sidebar and
Previous / Next links. Every page is self-contained — the stylesheet is written into the
file — so it opens straight from disk over `file://` with no server, no build server, and
no missing assets.

**Python 3.11+ and three small pure-Python dependencies** — `markdown-it-py`,
`mdit-py-plugins`, and `mdurl` which the first requires. Installed as a standalone tool it
gets its own isolated environment, so what it needs never reaches the project you are
documenting.

**Markdown is CommonMark**, via `markdown-it-py`, plus tables, strikethrough, footnotes and
task lists. Not a hand-rolled subset — a conformant parser, so what renders on GitHub
renders here.

It is deliberately small in *scope*, not in correctness: no plugins, no themes, no
templates, no shortcodes, no search index. If you want Sphinx or MkDocs, use those. This is
for a project that wants its docs written in plain markdown files, kept next to the code,
and rendered without adopting a toolchain.

> **Working on docsbuild itself?** There is an in-depth guide in
> [`docs/onboarding/`](docs/onboarding/markdown/index.md) — fifteen pages covering how
> every part works and why. Build it with `uv run docsbuild --set onboarding` and open
> `docs/onboarding/html/index.html`. The tool documents itself with itself, so if a change
> breaks the build, that guide stops rendering.

## Quick start

**docsbuild is not on PyPI.** It is installed from its git repository, pinned to a release
tag. The repository is public, so this needs no credentials:

```bash
uv tool install git+https://github.com/douglaslwatts/docsbuild@v0.1.1   # or: pipx install
```

Pin the tag rather than omitting it: without one you track whatever `main` happens to be, which
changes underneath you. See [Releases](#releases).

### Adding it to a project that already has markdown

If your repository already has documentation — say `docs/onboarding/markdown/*.md` and
`docs/development-plans/markdown/*.md` — let `init` write the configuration for you. Run
it **from the repository root**; it finds the docs directory itself:

```bash
cd acme-widgets && docsbuild init
```

```
Using docs/ as the docs root.

Detected 2 doc set(s) in /home/you/acme-widgets/docs:
  development-plans         15 pages   (markdown/)
  onboarding                19 pages   (markdown/)

Note: CONFIGURATION.md at the top level is not a doc set.
      If it should be a page of one of these, add a [[standalone]]
      entry to that set's config.

Wrote development-plans/site.toml
Wrote onboarding/site.toml
Wrote sites.toml

Edit the brand strings, then build:
  docsbuild
```

Config is written **inside `docs/`**, never at the repository root, so `sites.toml` sits
beside the sets it names.

It finds doc sets by looking for markdown, not for names, so it works whether you have
one set or five and whatever they are called. It handles both layouts — pages in a
`markdown/` subdirectory or sitting directly in the set's own directory — and it **never
overwrites an existing config**; pass `--force` if that is what you want.

A loose `.md` at the top level — a README, a changelog, a reference page — is **not** read
as a doc set when real sets are found beneath it, and `init` says which files it passed
over. If such a page belongs in a set, add a [`[[standalone]]`](#optional-a-page-outside-the-reading-chain)
entry to that set's config.

### What `init` cannot work out

`init` writes a **starting** config. The brand strings are guessed from directory names, so
edit them. And `[titles]`, `[concat]` and `[[standalone]]` encode intent that simply is not
in the filesystem — a set that needs them needs them added by hand.

To make that easy, every generated `site.toml` carries a commented, filled-in example of
all four optional blocks — `[titles]`, `[concat]`, `[[standalone]]` and `[badges]` — each
with a note on what it does, so you can uncomment what you want without coming back here.
The paths and commands in those examples are correct for that particular set, and the prose
never opens a line with a bracket, so uncommenting a whole block is safe.

`[badges]` is the exception that gets written **live** rather than commented, whenever the
markdown already uses badge tokens — see [Status badges](#status-badges).

This matters if you are copying a project whose docs already build a particular way.
Scaffolding a fresh config will produce *different* HTML: `brand` and `title_suffix` appear
in the sidebar and `<title>` of every page, so a different guess diffs every file, and a
missing `[concat]` or `[[standalone]]` means those outputs are not produced at all. **To
reproduce another project's docs exactly, copy its `site.toml` files.** They are the source
of truth; `init` is for projects that do not have them yet.

### Starting from scratch

A project needs a `site.toml` and a directory of markdown:

```
docs/
  site.toml
  markdown/
    index.md
    01-getting-started.md
    02-configuration.md
```

```toml
# docs/site.toml
brand        = "Acme · Guide"    # label at the top of the sidebar
title_suffix = "Acme Guide"      # appended to each browser-tab title
```

```bash
cd docs && docsbuild
open html/index.html
```

That is the whole setup. A complete working example is in [`example/`](example/) —
copy it, replace the prose, and you have your own site.

## Pages are discovered, not declared

There is no list of pages anywhere. The build reads the source directory and works out
three things from the files themselves:

- **Which pages exist** — every `*.md` in the directory is a page.
- **What order they go in** — sorted by filename, except a page named `index`, which is
  always first. (Plain sorting would put it last, since letters sort after digits.)
  Naming files `01-…`, `02-…` makes filename order and reading order the same thing.
- **What each is called** — the page's own first `# heading`.

So **adding a page means adding the file**. Nothing to register, nothing to renumber in
a manifest. That order drives the sidebar, the Previous / Next buttons, and the reading
chain.

## Configuration

Every key except the two brand strings is optional.

```toml
brand        = "Acme · Guide"        # required
title_suffix = "Acme Guide"          # required

source = "markdown"                  # where the pages are; "." for a flat layout
output = "html"                      # where the built site goes
style  = "../style.css"              # omit to use the bundled stylesheet
name   = "guide"                     # defaults to the containing directory's name

[titles]
index = "Overview"                   # sidebar label, when it differs from the H1

order = ["index", "01-a", "02-b"]    # replaces filename ordering entirely

[badges]
DONE = "Done"                        # see "Status badges" below; opt-in
```

**Every path resolves relative to the config file**, never to the working directory.
That is what lets one installed copy build documentation living anywhere on disk,
including in a checkout of a different repository.

### Optional: one file with everything in it

```toml
[concat]
output  = "whole-guide.md"
command = "docsbuild --set guide"    # quoted in the generated file's banner
```

Joins every page in reading order into a single markdown file. Links between pages
become in-document anchors; other relative links are rebased for the new location. It is
for reading straight through, diffing in one place, or handing a whole document to a
tool in one read.

### Optional: a page outside the reading chain

```toml
[[standalone]]
source     = "../REFERENCE.md"
output     = "../REFERENCE.html"
title      = "Reference"
brand      = "Acme · Docs"           # defaults to the set's own brand
brand_href = "guide/html/index.html"
```

Gets an in-page list of its own `##` sections instead of Previous / Next buttons. If the
source file is absent the page is skipped rather than failing the build.

Neither extra is tied to a kind of doc set — a guide can have a concatenated build, a
plan can have standalone pages.

## More than one doc set

A **doc set** is the unit of work: a directory of markdown with a `site.toml` beside it.
A project can have as many as it likes — a guide, a development plan, a book of runbooks
— each with its own configuration. List them in a `sites.toml` at the project root:

```toml
# docs/sites.toml
sets = ["guide", "plan"]
```

```
docs/
  sites.toml
  style.css              # shared, if you want one
  guide/site.toml + markdown/
  plan/site.toml  + markdown/
```

```bash
docsbuild --all           # every set
docsbuild --set guide     # one of them
```

The index is what says *where* the sets are, so it is needed whenever they sit in
subdirectories — even if there is only one. A doc set at the project root, with its
`site.toml` right there, needs no index. `docsbuild init` works this out for you.

### Two layouts for a set

```
docs/onboarding/markdown/*.md     # nested — the default, source = "markdown"
docs/onboarding/*.md              # flat   — source = "."
```

Both are supported. A flat set does no cross-set link rewriting, since it has no source
subdirectory for such a link to route through.

## Command line

```
docsbuild                      build every set in the project found from here
docsbuild --set NAME           build one named set
docsbuild --config PATH        build one site.toml directly
docsbuild --root DIR           use DIR as the project root instead of searching

docsbuild init                 write config for every doc set found here
docsbuild init --force         replace existing config instead of keeping it
```

### Where to run it

Anywhere inside the project. With no `--root`, the search walks *upwards* from the working
directory looking for a `sites.toml` or `site.toml`, the way `git` finds a repository — and
at each level it also glances *down* into a conventional documentation directory (`docs/`,
`doc/`, `documentation/`). So all of these work:

```bash
cd acme-widgets            && docsbuild    # repository root
cd acme-widgets/docs       && docsbuild    # the docs root
cd acme-widgets/src        && docsbuild    # a sibling directory
cd acme-widgets/docs/guide && docsbuild    # inside a doc set
```

Config at a level beats a `docs/` inside it, and a nearer level beats a farther one.
`--root` skips the upward walk and uses the directory you name, still stepping into its
`docs/` if that is where the project lives.

Scanning always ignores dot-directories (`.git`, `.venv`, `.pytest_cache`) and the usual
dependency and build trees (`node_modules`, `__pycache__`, `venv`, `dist`, `build`,
`target`, `vendor`, `site-packages`, `htmlcov`), so a vendored `README.md` never becomes a
doc set.

## The markdown it handles

**CommonMark**, in full, via `markdown-it-py` — headings, paragraphs, lists nested to any
depth, emphasis, code spans and fences, blockquotes, images, links (inline and
reference-style), autolinks, hard line breaks, horizontal rules. Plus four extensions:
pipe **tables** with `|:---:|` alignment, **strikethrough**, **footnotes**, and **task
lists**.

Two behaviours are this tool's own:

| You write | You get |
|---|---|
| `[label](page.md)` | A link, rewritten to `page.html` on the way out |
| `[DONE] …` starting a list item | A coloured status badge, if you declared `DONE` |

Write links as `.md` so they also work when someone reads the source on GitHub; the
builder rewrites the extension. A link through a sibling set's source directory —
`../../plan/markdown/x.md` — is repointed at that set's output directory.

### Status badges

A token at the head of a list item becomes a pill, so a document can mark finished work
instead of deleting it. **They are opt-in**, declared per doc set:

```toml
[badges]
DONE  = "Done"                                # pill colour from the lowercased token
NEXT  = "Next"
BUILT = { label = "Built", style = "done" }    # or borrow another token's colour
```

The bundled stylesheet defines `done`, `next`, `later`, `planned` and `dropped`. A token
whose style is not one of those renders as an unstyled pill until you add the CSS.

With no `[badges]` table, nothing is special: `[DONE]` stays literal text. That matters
because otherwise a project would inherit a status vocabulary it never asked for. A token
you have not declared, or one mid-sentence rather than at the head of an item, is likewise
left alone.

**`init` writes this table for you.** It scans the markdown for badge-shaped tokens — using
the same rule the renderer applies, and skipping fenced code — and declares exactly the ones
your documents use, most frequent first. So a repository whose docs already use `[DONE]`
does not quietly lose its badges to an opt-in it never knew about. If a token has no
matching style in the bundled stylesheet, `init` names it and tells you how to point it at
one; guessing a colour would look deliberate and be wrong.

### Known limits

**Raw HTML is escaped, deliberately.** `<kbd>Esc</kbd>` renders as literal text, not as an
element. Passing markup through would mean either trusting every input or shipping a
sanitiser, and a sanitiser is a dependency this tool does not want.

**Assets are not copied.** `![alt](picture.png)` renders an `<img>` with that `src`
untouched, so the file has to already sit where the *built page* will look for it — not
where the markdown is. With the default layout that means `html/picture.png`, not
`markdown/picture.png`.

**Cross-set links assume both sets use the same directory names,** because the converter is
only given the current set's `source`/`output`. If two sets in one project use different
directory names, links between them need writing by hand.

**A `[TOKEN]: url` reference definition wins over a badge.** With such a definition,
`[TOKEN]` is a link and markdown's own meaning takes precedence.

Every one of these is asserted by the test suite, so this list and the behaviour cannot
drift apart. `tests/test_corpus.py` additionally runs 40 real documents through the
renderer on every test run, checking invariants — no leaked `**`, no unrendered `](`, no
stray `!` before a link, well-formed output — because the defects that reached users were
all found by eye in output, weeks late, rather than by a test.

That harness is also what made replacing the renderer safe. This tool used to carry a
hand-written markdown converter, about 225 lines of it. Because the corpus tests assert
invariants rather than exact HTML, they carried across the swap unchanged and could confirm
that 34 of 35 real pages rendered identical visible text — the one difference being a
double-backtick code span the old converter had been mangling for months.

## How a build works

Four steps, in this order:

1. **Read** every discovered markdown file. If one has vanished, stop immediately.
2. **Convert** them all to HTML, in memory.
3. **Delete** any `.html` in the output directory with no markdown source left.
4. **Write** the new pages.

Step 3 is why renaming a page cleans up after itself, instead of leaving the old file
browsable and out of date forever. It happens third rather than first deliberately: if
deleting came before converting, a crash half-way through would leave you with no
documentation at all. Converting everything first means a failure leaves the existing
site untouched.

The stylesheet is copied into every page rather than linked. Pages get bigger; in return
each one is genuinely self-contained and opens from anywhere. For documentation that is
the right trade.

## Development

```bash
uv sync
uv run pytest          # 423 tests, 100% coverage, gate at 95%
uv run ruff check . && uv run ruff format --check .
uv run pyright
```

The converter's documented limits are asserted by tests rather than only written down
here. If someone teaches it to handle nested emphasis, the test fails loudly and this
README gets updated with it.

## Releases

There is no package index here, so **a release is a git tag** and consumers pin it. Tags are
semantic versioning with a `v` prefix — `v0.1.0` — and the tag always matches `version` in
`pyproject.toml`.

| Bump | Means |
|---|---|
| patch — `v0.1.1` | a fix; same inputs, better output |
| minor — `v0.2.0` | something new, nothing broken (a new config key or flag) |
| major — `v1.0.0` | existing `site.toml` files stop working |

To cut one: bump the version, commit, `git tag -a v0.1.0 -m "…"`, then push **both** the branch
and the tag — pushing a branch does not push tags, and until the tag is on the remote no
consumer can resolve it.

A project can consume a release either as a standalone tool (above) or as a development
dependency pinned in `[tool.uv.sources]`. The full workflow — including the reason
`uv run --no-sync` is mandatory when testing local changes against a consuming project — is in
**[Releasing a version](docs/onboarding/markdown/14-releasing.md)**.

## Licence

MIT.

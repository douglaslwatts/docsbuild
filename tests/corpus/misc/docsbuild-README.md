# docsbuild

Turn a directory of markdown into a browsable HTML site with a contents sidebar and
Previous / Next links. Every page is self-contained — the stylesheet is written into the
file — so it opens straight from disk over `file://` with no server, no build server, and
no missing assets.

**No dependencies.** Standard library only, Python 3.11 or newer. The promise is that
someone who has just cloned your repository can rebuild your documentation with nothing
but an interpreter.

It is deliberately small. It handles [a disciplined subset of markdown](#the-markdown-it-handles),
not everything GitHub renders, and it has no plugins, no themes, and no templates. If you
want Sphinx or MkDocs, use those. This is for a project that wants its docs written in
plain markdown files, kept next to the code, and rendered without adopting a toolchain.

## Quick start

```bash
uv tool install git+https://github.com/douglaslwatts/docsbuild   # or: pipx install
```

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
all three, each with a note on what it does, so you can uncomment what you want without
coming back here. The paths and commands in those examples are correct for that particular
set, and the prose never opens a line with a bracket — so uncommenting a whole block is
safe.

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

| You write | You get |
|---|---|
| `# Heading` … `###### Heading` | Headings; `##` and `###` get anchor ids |
| `- item` / `* item` / `1. item` | Bullet and numbered lists |
| `` `code` `` and fenced blocks | Inline code and code blocks, uninterpreted inside |
| `> quoted` | A blockquote |
| `**bold**` and `*italic*` | Bold and italic |
| `[label](page.md)` | A link, rewritten to `page.html` on the way out |
| Pipe tables | A table wrapped so a wide one scrolls on its own |
| `---` alone on a line | A horizontal rule |
| `[DONE]` etc. starting a list item | A coloured status badge |

Status badges — `[DONE]`, `[NEXT]`, `[LATER]`, `[PLANNED]`, `[BUILT]`, `[DROPPED]` —
exist so a document can mark finished work instead of deleting it. A bracketed word
outside that list stays ordinary text.

Write links as `.md` so they also work when someone reads the source on GitHub; the
builder rewrites the extension.

### Known limits

**Italics nested inside bold does not render.** `**a *b* c**` comes out with visible
asterisks. The bold pattern is "two asterisks, non-asterisks, two asterisks", and the
inner emphasis breaks the match. This is pinned by a test
(`test_italics_nested_inside_bold_is_a_known_limitation`), so the documentation and the
behaviour cannot drift apart.

**Cross-set links assume both sets use the same directory names.** A link written
through another set's source directory — `../../plan/markdown/x.md` — is repointed using
*this* set's `source`/`output` names, because that is all the converter is given. If two
sets in one project use different directory names, links between them need writing by
hand.

No nested lists, no footnotes, no reference-style links, no inline HTML.

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
uv run pytest          # 144 tests, 100% coverage, gate at 95%
uv run ruff check . && uv run ruff format --check .
uv run pyright
```

The converter's documented limits are asserted by tests rather than only written down
here. If someone teaches it to handle nested emphasis, the test fails loudly and this
README gets updated with it.

## Licence

MIT.

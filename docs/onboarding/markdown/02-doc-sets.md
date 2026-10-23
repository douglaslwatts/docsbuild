# Doc sets: the central idea

**A doc set is a directory of markdown with a `site.toml` beside it.** That is the only
unit this tool has. Understanding it explains most of the design, including several things
that otherwise look arbitrary.

## The concept

One doc set becomes one browsable site: its own sidebar, its own reading order, its own
Previous / Next chain. A project can have one, or several.

```
docs/
  sites.toml                  names the sets, when there is more than one
  guide/
    site.toml                 this set's configuration
    markdown/*.md             its pages
    html/*.html               its built output
  runbooks/
    site.toml
    markdown/*.md
    html/*.html
```

Here `guide` and `runbooks` are two doc sets. They build independently, link to each other
if they like, and know nothing about each other otherwise.

## The tool has no idea what your sets are *for*

This matters more than it sounds. There is no concept of "a user guide" or "a development
plan" or "an API reference" anywhere in the code. A doc set is a directory with markdown
in it, and every set is treated identically.

You can verify this: search the source for the name of any kind of document and you will
find nothing. `sites.toml` is a list of directory names, and the code does
`root / name / "site.toml"` with whatever you wrote.

The consequence is that the two features that *look* set-specific are not:

| Feature | What it does | Typically used by | Available to |
|---|---|---|---|
| `[concat]` | Also writes every page into one big markdown file | a plan or spec | **any set** |
| `[[standalone]]` | Renders a page outside the reading chain | a reference guide | **any set** |

`build_site` checks `if site.concat:` and loops `for spec in site.standalone:`. Neither
branches on what kind of document it is dealing with, because it cannot — that information
does not exist. See [Concatenation and standalone pages](10-extras.md).

## The minimum viable set

Two lines:

```toml
# docs/guide/site.toml
brand        = "Acme · Guide"
title_suffix = "Acme Guide"
```

`brand` is the label at the top of the sidebar. `title_suffix` is appended to each page's
browser-tab title, so a page called "Getting started" gets
`<title>Getting started · Acme Guide</title>`. Both are required, because guessing them
from a directory name produces something you would immediately want to change.

Everything else has a default:

- `source` defaults to `markdown` — where the pages are read from
- `output` defaults to `html` — where the built pages are written
- `style` defaults to the stylesheet **bundled inside docsbuild itself**

**Both directory defaults are subdirectories of wherever the `site.toml` sits.** The tool
does not scan the config file's own directory for markdown, and it does not write HTML
next to your markdown. Full details in the
[configuration reference](11-configuration.md).

## Two layouts

**Nested** — the default, and what most projects want:

```
docs/guide/site.toml
docs/guide/markdown/index.md
docs/guide/html/index.html
```

**Flat** — pages sitting directly in the set's own directory:

```toml
source = "."
```

```
docs/notes/site.toml
docs/notes/index.md
docs/notes/html/index.html
```

Note that even a flat set writes its output into a subdirectory. `output` still defaults
to `html`, so your markdown and your HTML never end up mixed together unless you
explicitly ask for that.

The flat layout has one behavioural difference, and it is not obvious. Links to pages
are resolved against the project's real page list (see [the renderer](05-the-renderer.md)),
but when that list is incomplete — a `--config` build of one set — a link through another
set's source directory falls back to a naming convention: `/{source}/` is replaced with
`/{output}/`. For a flat set, `source` *is* the set's own directory, so its name is not a
safe marker: a set called `notes` would rewrite any link containing `/notes/`, including
one pointing at something entirely unrelated. So **that fallback is switched off for flat
sets**, which loses nothing, since a flat set has no source subdirectory for such a link
to route through. The function is `_link_dirs`.

## When you need `sites.toml`, and when you don't

`sites.toml` is an index listing the sets:

```toml
# docs/sites.toml
sets = ["guide", "runbooks"]
```

The rule is not about *how many* sets you have — it is about *where they are*:

- Sets in **subdirectories** need an index, even if there is only one. Without it, running
  `docsbuild` in `docs/` finds no configuration, because the `site.toml` is one level down.
- A set at the **project root itself**, with its `site.toml` right there, needs no index.
  There is nothing to point at; the config is already where the build looks.

This falls out of the format rather than being a preference. `sites.toml` names sets by
subdirectory, so a set living at the root cannot be listed in an index sitting in that
same directory — `sets = ["", "guide"]` is meaningless. A project therefore cannot mix a
root-level set with subdirectory sets, and detection has to pick one.
[`docsbuild init`](09-init.md) works all of this out for you.

## Why this is the whole design

Because a doc set is the only unit, and because it is defined by a config file rather than
by a name or a location, the tool works on any repository's layout. Nothing had to be
generalised to make that true — there was never anything specific in the first place.

That also explains the answer to a question people ask early: *can it handle a project
with an onboarding guide and a development plan?* It can handle a project with a guide and
a plan, or five runbooks, or one page of notes, because it does not know which of those
you have. It knows about directories with markdown in them.

---

[← Previous: What it is](01-what-it-is.md) · [Contents](index.md) ·
[Next: How pages are discovered →](03-page-discovery.md)

# Configuration reference

Every key, with its default. There are two config files: a `site.toml` describing one
[doc set](02-doc-sets.md), and an optional `sites.toml` listing several.

## The rule that governs every path

**Every path resolves relative to the config file that named it** — never to your working
directory, and never to where docsbuild is installed.

This is what lets one installed copy build documentation anywhere on disk, including in a
checkout of a completely different repository. `load_site` resolves everything against
`config_path.parent`, stored on the resulting object as `base`.

## `site.toml`

### Required

```toml
brand        = "Acme · Guide"    # label at the top of the sidebar
title_suffix = "Acme Guide"      # appended to each browser-tab title
```

A page called "Getting started" gets `<title>Getting started · Acme Guide</title>`.

Both are required rather than defaulted because anything derived from a directory name is
something you would immediately want to change, and a default you always override is worse
than no default. Omit either and the build stops with a message naming the file, the
missing key, and a two-line minimal config — not a traceback.

### Paths

```toml
source = "markdown"        # where the pages are; "." for a flat layout
output = "html"            # where the built site goes
style  = "../style.css"    # omit to use the stylesheet bundled with docsbuild
```

Both directory defaults are **subdirectories of the config file's own directory**. The tool
does not scan that directory for markdown, and does not write HTML beside your markdown.
Even a flat set (`source = "."`) writes its output into `html/`.

Omitting `style` means [inheriting docsbuild's bundled stylesheet](07-self-contained-pages.md),
which is what makes a two-line config viable. Naming your own pins the look to your project.

### Naming

```toml
name = "guide"    # defaults to the containing directory's name
```

Only affects what `--set` matches. Rarely needed.

### Page order and titles

```toml
[titles]
index = "Overview & contents"        # sidebar label, when it differs from the H1

order = ["index", "01-a", "02-b"]    # replaces filename ordering entirely
```

Both are escape hatches from [discovery](03-page-discovery.md), which normally derives
order from filenames and titles from each page's first `# heading`. Naming a page in
`order` that does not exist is an error, not a silent skip.

### Status badges

```toml
[badges]
DONE  = "Done"                                # colour from the lowercased token
BUILT = { label = "Built", style = "done" }   # or borrow another token's colour
```

**Opt-in.** With no table, `[DONE]` at the head of a list item stays literal text. Styles
the bundled stylesheet defines: `done`, `next`, `later`, `planned`, `dropped`. See
[Status badges](06-badges.md); `docsbuild init` writes this table for you.

### One file with everything in it

```toml
[concat]
output  = "whole-guide.md"           # relative to the config file
command = "docsbuild --set guide"    # quoted in the generated file's banner
```

See [Concatenation and standalone pages](10-extras.md).

### A page outside the reading chain

```toml
[[standalone]]
source     = "../REFERENCE.md"
output     = "../REFERENCE.html"
title      = "Reference"
brand      = "Acme · Docs"             # defaults to the set's own brand
brand_href = "guide/html/index.html"   # defaults to empty
```

An array of tables — repeat the block for more pages. A missing `source` is skipped rather
than fatal.

## `sites.toml`

```toml
sets = ["guide", "runbooks"]
```

A list of subdirectory names, each holding a `site.toml`, in the order `--all` builds them.
Build order has no functional effect; sets are independent.

Needed whenever the sets live in **subdirectories**, even if there is only one — it is what
tells the build where to look. A set at the project root, with its `site.toml` already
there, needs no index.

## A complete two-set project

```
acme-widgets/
  docs/
    sites.toml                     sets = ["guide", "plan"]
    style.css                      shared, if you want one
    CONFIGURATION.md               a loose page; not a doc set
    CONFIGURATION.html             built by [[standalone]]
    guide/
      site.toml
      markdown/*.md
      html/*.html
    plan/
      site.toml
      markdown/*.md
      html/*.html
      plan.md                      built by [concat]
```

## Things worth knowing

**Generated output is not usually committed.** The `html/` directories are rebuilt on
demand; a `.gitignore` entry for `html/` covers every set at once. A `[concat]` file is
often the exception, since a fresh clone benefits from having the whole document before
anyone has run a build.

**Unknown keys are ignored, not rejected.** A typo in a key name fails silently — the
setting simply does not apply. If a config change appears to have no effect, check the
spelling.

**`prune_stale` deletes every `.html` in the output directory** that has no matching page.
With the default `output = "html"` that is safe, because the directory holds nothing but
generated pages. Point `output` at a directory containing hand-written HTML and the build
will remove it.

---

[← Previous: Concatenation and standalone pages](10-extras.md) · [Contents](index.md) ·
[Next: How it is tested →](12-testing.md)

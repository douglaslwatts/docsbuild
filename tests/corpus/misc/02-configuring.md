# Configuring the build

Each doc set describes itself in a `site.toml` sitting beside its markdown. Only two
keys are required.

**If your project already has markdown but no config**, you do not have to write one by
hand. Run `docsbuild init` and it detects every doc set — by looking for markdown, not
for particular directory names — and writes a `site.toml` for each, plus a `sites.toml`
if the sets live in subdirectories. It never overwrites an existing config unless you
pass `--force`. Edit the brand strings it guesses, and you are done.

## The whole file

```toml
brand        = "Example · Guide"     # required — label at the top of the sidebar
title_suffix = "Example Guide"       # required — appended to each browser-tab title

source = "markdown"                  # where the pages are; "." if they sit right here
output = "html"                      # where the built site goes
style  = "../style.css"              # omit to use the bundled stylesheet

[titles]
index = "Overview"                   # sidebar label, when it differs from the H1

order = ["index", "01-a", "02-b"]    # replaces filename ordering entirely
```

**Every path is resolved relative to this file**, never to the directory you happen to
be standing in when you run the build. That is what lets one installed copy of the tool
build documentation living anywhere on disk.

## Two optional extras

**A concatenated single file** — every page joined in reading order, with links between
pages becoming in-document anchors. Useful for reading straight through, diffing in one
place, or handing the whole document to a tool in one read.

```toml
[concat]
output  = "whole-guide.md"
command = "docsbuild --set guide"    # quoted in the generated file's banner
```

**A standalone page** — one sitting outside the reading chain. It gets an in-page list
of its own sections instead of Previous / Next buttons.

```toml
[[standalone]]
source     = "../REFERENCE.md"
output     = "../REFERENCE.html"
title      = "Reference"
brand_href = "guide/html/index.html"
```

Neither is tied to a kind of doc set. A guide can have a concatenated build; a plan can
have standalone pages.

## More than one doc set

A project with several — say a guide and a plan — gives each its own directory and adds
an index naming them:

```toml
# docs/sites.toml
sets = ["guide", "plan"]
```

```bash
docsbuild --all           # both
docsbuild --set guide     # one
```

The index says *where* the sets are, so it is needed whenever they sit in
subdirectories. This example has its markdown at its own root, so its `site.toml` is
already in the right place and no index is needed — which is why there isn't one.

## What a build does, in order

1. **Read** every discovered markdown file. If one has vanished, stop immediately.
2. **Convert** them all to HTML, in memory.
3. **Delete** any `.html` in the output directory with no markdown source left.
4. **Write** the new pages.

Step 3 is why renaming a page cleans up after itself instead of leaving the old one
browsable forever. It happens third rather than first on purpose: if deleting came
before converting, a crash half-way through would leave you with no documentation at
all. Converting everything first means a failure leaves the existing site untouched.

---

[← Previous: Writing pages](01-writing-pages.md) · [Contents](index.md)

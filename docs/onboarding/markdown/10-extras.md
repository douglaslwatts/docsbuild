# Concatenation and standalone pages

Two optional outputs, both off unless a doc set asks for them. Neither is tied to a kind of
document — a guide can have a concatenated build, a plan can have standalone pages, because
[the tool has no idea which you have](02-doc-sets.md).

## `[concat]` — every page in one file

```toml
[concat]
output  = "whole-guide.md"
command = "docsbuild --set guide"
```

This writes an extra file containing every page of the set, joined in reading order,
separated by horizontal rules. It is **markdown, not HTML** — the pages' sources
concatenated, not their rendered output.

### What it is for

Reading a whole document top to bottom without clicking. Diffing an entire guide in one
place. Handing a complete specification to a tool — a language model, a search index, a
`grep` — in a single read rather than nineteen.

### Two things it rewrites

**Links between pages become in-document anchors.** A link to `02-status.md` becomes
`#where-it-stands`, using the target page's own first heading. A link to a section,
`02-status.md#open-questions`, becomes that section's own anchor, `#open-questions`, since
every section is in the one file too. So the concatenated file reads as one document with
working internal navigation, rather than a stack of pages with links pointing at files
that are not there.

The match is against the **real page list**, not a filename pattern. An earlier version
guessed with a regular expression matching `index` or `NN-slug`, which silently missed a
page named `appendix.md`. Checking membership in the discovered set cannot miss anything.

**Every other relative link is rebased.** The concatenated file sits somewhere other than
the source directory — usually a level or two up — so a path that was correct relative to
the sources is wrong relative to the new file, by exactly the distance between them.
`concat_links` computes that distance and re-bases each link accordingly. With the usual
layout, `../../other/x.md` loses a level and `assets/x.png` gains the `markdown/` prefix;
both fall out of the same rule.

Links with a scheme (`https:`), site-absolute paths (`/foo`) and bare anchors (`#section`)
are left alone, since none of them is relative to anything.

### The banner

The generated file opens with a comment naming the command that produced it:

```
<!-- Generated from markdown/*.md by docsbuild — do not edit by hand.
     Edit the sources under markdown/ and run:
     docsbuild --set guide -->
```

That is what `command` is for. Set it to whatever someone should actually run in your
project. The file is generated, so editing it is always a mistake, and the banner is there
to catch someone about to make it.

Unlike the `html/` directory, a concatenated file is often worth committing — a fresh clone
then has the whole document before anyone has run a build.

## `[[standalone]]` — a page outside the reading chain

```toml
[[standalone]]
source     = "../REFERENCE.md"
output     = "../REFERENCE.html"
title      = "Reference"
brand      = "Acme · Docs"           # defaults to the set's own brand
brand_href = "guide/html/index.html"
```

This renders one markdown file that is **not** part of the set's reading order. It does not
appear in the sidebar, has no Previous / Next buttons, and does not shift anything else's
position.

Instead of navigation, it gets an **in-page index of its own `##` headings** — which is
what the [anchor ids on h2 and h3](05-the-renderer.md) are for. `brand_href` is where the
sidebar's brand link points, since such a page usually wants to lead back into the main
guide.

### What it is for

A page that belongs with the documentation but not in the tour. A configuration reference,
an API listing, a changelog, a glossary — something you look things up in rather than read
through.

It also solves a specific layout problem. A loose `.md` at your documentation root — sitting
beside your doc sets rather than inside one — is [deliberately not treated as a doc
set](08-finding-the-project.md). `[[standalone]]` is how such a file gets rendered anyway,
and it is exactly what `init` suggests when it finds one.

Add one block per page; it is an array of tables, so repeating `[[standalone]]` adds more.

### A missing source is skipped, not fatal

If the file named by `source` does not exist, the entry is skipped and the rest of the
build proceeds. That is deliberate: an optional extra should not be able to break the
documentation. The trade-off is that a typo in the path fails quietly — if a standalone
page is not appearing, check the spelling first.

## Both are per-set, and both are optional

`build_site` handles them with `if site.concat:` and `for spec in site.standalone:`. A set
that asks for neither pays nothing. A set can have both.

---

[← Previous: docsbuild init](09-init.md) · [Contents](index.md) ·
[Next: Configuration reference →](11-configuration.md)

# How pages are discovered

**There is no list of pages anywhere.** Not in the config, not in the code, not in a
manifest file. The build reads the source directory and works out three separate things —
which files are pages, what order they go in, and what each one is called — entirely from
what it finds. This page explains each rule and the reasoning behind it.

The function is `discover_pages`, and it is about twenty lines including its docstring.

## Which files are pages

Every `*.md` file in the source directory. There is no exclusion list and no "draft"
convention. If you do not want a file built, do not put it in the source directory.

Note the glob is **not** recursive. Pages are files directly inside `source`; a
subdirectory of markdown is not walked. That keeps the reading order one-dimensional,
which is what makes a single Previous / Next chain possible.

## What order they go in

Sorted by filename, with one exception: **a page named `index` always comes first.**

The exception exists because plain sorting would put it last — in ASCII, letters sort
after digits, so `index.md` lands after `09-whatever.md`. A cover page belongs at the
front. The sort key is `_page_sort_key`:

```python
def _page_sort_key(path: Path) -> tuple[int, str]:
    return (0 if path.stem == "index" else 1, path.stem)
```

Sorting by filename is why documentation written for this tool tends to be numbered:

```
index.md
01-getting-started.md
02-configuration.md
10-appendix.md
```

**Use two digits.** Filename sorting is textual, so `10-appendix.md` sorts *before*
`2-something.md` — "1" is less than "2" as a character. Zero-padding makes textual order
and numeric order agree. This is the one place the convention can bite you, and it will
look like a bug in the tool when it happens.

If filename order genuinely cannot express your reading order, `site.toml` accepts an
explicit list:

```toml
order = ["index", "01-intro", "05-detail", "02-summary"]
```

That replaces the sort entirely. Naming a page that does not exist is an error rather than
a silent skip, because a typo there would otherwise quietly drop a page from the site.

## What each page is called

The page's own **first `# heading`**, found by `first_h1`. A file starting with
`# Getting started` is titled "Getting started" in the sidebar, in the Previous / Next
buttons, and in the browser tab.

This means a page's title lives in exactly one place — inside the page — so renaming a
section cannot leave a stale label in a navigation list somewhere.

When the sidebar should read differently from the heading, override it:

```toml
[titles]
index = "Overview & contents"
```

Use this sparingly. It is for the case where a page's real title is too long for a sidebar,
or where a cover page's `# Project name` heading would be uninformative as a contents
entry. Across the two doc sets this tool was originally built for — 34 pages — exactly
three needed an override.

If a file has no `# heading` at all, the title falls back to the filename stem. That is a
deliberate last resort, not a supported style: the sidebar will show `04-thing`, which
looks broken enough that you will go and add a heading.

## What this buys

**Adding a page means adding a file.** There is nothing to register. Compare with the
common alternative, a navigation tree in a config file, where every new page requires an
edit in two places and the two can disagree.

**Renaming a page cannot leave a dangling reference in a config file,** because there is no
config file mentioning it.

**The reading order and the sidebar cannot disagree,** because both are generated from the
same list, in the same call, in `build_site`.

The cost is that the ordering convention is implicit. Someone new has to be told that
filenames determine order — which is exactly why this page exists.

## What is *not* automatic

Two things still need doing by hand when you add a page, and it is worth being clear about
them because everything else is derived:

1. **The contents list** on the cover page. The sidebar is generated, but a hand-written
   list of links on `index.md` — like the one this guide has — is prose, and the tool does
   not touch it.
2. **The Previous / Next links in the page footer.** The buttons at the top and bottom of
   each rendered page *are* generated from the reading order. But the markdown footer line
   at the bottom of each source file is prose you wrote, and stays whatever you typed.

So a rendered page has generated navigation *and* whatever footer you wrote. This guide
uses both: the buttons come from discovery, the `← Previous · Contents · Next →` line at
the bottom of each source file is written out.

---

[← Previous: Doc sets](02-doc-sets.md) · [Contents](index.md) ·
[Next: What a build actually does →](04-the-build.md)
